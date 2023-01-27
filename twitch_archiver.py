import asyncio, time, os, logging
from streamlink import Streamlink, PluginError

class Stream:
    _url = None
    _session = None
    _stream = None
    _title = None
    _filepath = None
    is_live = False
    def __init__(self, url) -> None:
        self._url = url
        self._session = self.setSession()

    def setSession(self):
        session = Streamlink()
        if config["oauth_token"] != "":
            session.set_plugin_option("twitch", "api-header", {"Authorization":f'OAuth {config["oauth_token"]}'})
        session.set_plugin_option("twitch", "record-reruns", config["record_reruns"])
        session.set_plugin_option("twitch", "disable-hosting", config["disable_hosting"])
        session.set_plugin_option("twitch", "disable-ads", config["disable_ads"])
        return session

    async def setStream(self):
        log.info("waiting for stream to go live")
        streamformats = self._session.streams(self._url)
        while len(streamformats) == 0 and streamformats.get("best", None) == None:
            await asyncio.sleep(1)
            streamformats = self._session.streams(self._url)
        self._stream = streamformats["best"].open()
        self.is_live = True
        log.info("stream is live")
        return
    
    async def setTitle(self):
        log.info("attempting to resolve stream title")
        while (title := self._session.resolve_url(self._url)[1](self._session, self._url).get_title()) == None:
            # .resolve_url() instantiates a new plugin.Twitch class, returns a tuple(str, type(Plugin), str)
            # .get_title() returns the (re?)initialised title metadata from the (new) plugin.Twitch class
            await asyncio.sleep(1)
        self._title = self._sanitiseString(title)
        log.info("resolved stream title")
        self._updateFilepath()
        return

    def updateTitle(self, title):
        self._title = title
        self._updateFilepath()
        # because _updateFilepath() assumes that the filepath being updated ends in 'live.ts'
        # updateTitle() should only be called if setTitle() fails, this means that updateTitle()
        # should only ever be called once per instance of the Stream class
        return

    def setFilepath(self, config):
        directory, streamer, date = config["out_dir"], config["streamer"], self._sanitiseString(time.strftime(config["time_format"])) 
        self._filepath = f'{directory}{streamer}_{date}.live'
        return

    def _updateFilepath(self):
        new_filepath = f'{self._filepath[:-5]}_{self._title}.ts'
        # [:-5] slices '.live' from the end of the temporary filename
        while True:
            try:
                if os.path.exists(new_filepath):
                    raise FileExistsError(f"'{new_filepath}' already exists")
                os.rename(self._filepath, new_filepath)
                break
            except FileExistsError as message:
                log.warning(message)
                log.info("appending current time to filepath")
                new_filepath = f'{self._filepath[:-7]}{self._title}_{time.strftime("%H-%M-%S")}.ts'
        log.info("renamed '%s' to '%s'", self._filepath, new_filepath)
        self._filepath = new_filepath
        return
    
    def _sanitiseString(self, input) -> str:
        forbiddenchars = r'<>:"/\|!?*'
        input = "".join(char for char in input if char not in forbiddenchars)
        input = input.strip()
        return input

    async def checkIsLive(self, timeout):
        while True:
            await asyncio.sleep(timeout)
            if len(self._session.streams(self._url)) != 0:
                self.is_live = True
            else:
                self.is_live = False

    async def writeToFile(self):
        try:
            data = self._stream.read(1024)
            with open(self._filepath, "ab") as vod:
                vod.write(data)
        except OSError as message:
            # self._stream.read() raises `OSError("Read Timeout")` rarely on stream ended
            log.error(message)
            self.is_live = False
        return

def setConfig(config_file):
    with open(config_file, 'r') as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        if line.startswith('#') == False and len(line.strip()) > 0 :
            line = line.split('=')
            config.update({line[0].strip():line[1].strip()})
    return config

config = setConfig(r'./twitch_archiver.config')
logging.basicConfig(level=config["log_level"], format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger()
for option in config:
    if config[option] is config["oauth_token"]: value = f'{config["oauth_token"][:6]}{(max(0, len(config["oauth_token"]))-6)*"*"}'
    else: value = config[option]
    log.info("config.%s=%s", option, value)
if os.path.isdir(config["out_dir"]) == False:
    message = "'out_dir' in twitch_archiver.config is not a directory or does not exist"
    log.critical(message)
    raise Exception(message)
if config["streamer"] == "":
    message = "'streamer' not set in twitch_archiver.config"
    log.critical(message)
    raise Exception(message)
url = f'https://twitch.tv/{config["streamer"]}'

async def mainloop():
    while True:
        stream = Stream(url)
        # delayed initialisation that doesn't fit neatly into Stream.__init__() due to async shenanigans,
        # once the `Stream._stream` file object property has been set, parallel tasks are utilised to set
        # additional properties without 'blocking' the event handler, this allows writeToFile() to start
        # recording as soon as possible in relation to the start of the stream
        try:
            await stream.setStream()
        except PluginError as message:
            # setStream() raises PluginError on reconnect from internet failure, very strange behaviour
            log.warning(message)
            log.info("reinitialising 'Stream' class")
            continue
        stream.setFilepath(config)
        fetch_title = asyncio.create_task(stream.setTitle())
        fetch_is_live = asyncio.create_task(stream.checkIsLive(30))

        log.info("writing stream to '%s'", stream._filepath)
        while stream.is_live:
            await stream.writeToFile()
            await asyncio.sleep(0)
            # asyncio runs on a single thread so without the previous line writeToFile() would always have the
            # highest priority in the event handler, effectively blocking other tasks from executing
        log.info("stream ended")

        # task handling once the stream has concluded to prevent current loop's Stream class properties
        # from interacting with the next loop's as of yet unset properties
        while fetch_is_live.cancel():
            await asyncio.sleep(0)
            stream.is_live = False
        while fetch_title.cancel():
            await asyncio.sleep(0)
            log.error("unable to retrieve stream title")
            stream.updateTitle("title-error")

asyncio.run(mainloop())