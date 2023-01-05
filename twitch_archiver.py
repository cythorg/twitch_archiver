import asyncio, time, os, logging
from streamlink import Streamlink

def setConfig(config_file):
    with open(config_file, 'r') as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        if line.startswith('#') == False and len(line.strip()) > 0 :
            line = line.split('=')
            config.update({line[0].strip():line[1].strip()})
    return config

class Stream:
    _session = None
    _url = None
    _stream = None
    _title = None
    _filepath = None
    def __init__(self, session, url) -> None:
        self._session = session
        self._url = url

    async def setStream(self):
        log.info("waiting for stream to go live")
        streamformats = self._session.streams(self._url)
        while len(streamformats) == 0 and streamformats.get("best", None) == None:
            await asyncio.sleep(1)
            streamformats = self._session.streams(url)
        self._stream = streamformats["best"].open()
        log.info("stream is live")
        return
    
    async def setTitle(self):
        log.info("attempting to resolve stream title")
        while (title := self._session.resolve_url(self._url)[1](self._session, self._url).get_title()) == None:
            # .resolve_url() instantiates a new plugin.Twitch class, returns a tuple(str, type(Plugin), str)
            # .get_title() returns the (re?)initialised title metadata from the (new) plugin.Twitch class
            await asyncio.sleep(1)
        self._title = self._formatTitle(title)
        log.info("resolved stream title")
        self._updateFilepath()
        return

    def updateTitle(self, title):
        self._title = title
        self._updateFilepath() #because of how _updateFilepath() works, updateTitle() should only be called if setTitle() fails to complete
        return

    def setFilepath(self, config):
        directory, streamer, date = config["out_dir"], config["streamer"], self._sanitiseString(time.strftime(config["time_format"])) 
        self._filepath = f'{directory}{streamer}_{date}_live.ts'
        return

    def _updateFilepath(self):
        new_filepath = f'{self._filepath[:-7]}{self._title}.ts' #the [:-7] slices 'live.ts' from the end of the temporary filename
        while True:
            try:
                os.rename(self._filepath, new_filepath)
                break
            except FileExistsError:
                log.warning("'%s' already exists, appending current time", new_filepath)
                new_filepath = f'{self._filepath[:-7]}{self._title}_{time.strftime("%H-%M-%S")}.ts'
        log.info("renamed '%s' to '%s'", self._filepath, new_filepath)
        self._filepath = new_filepath
        return
    
    def _sanitiseString(self, input) -> str:
        forbiddenchars = r'<>:"/\|!?*'
        input = "".join(char for char in input if char not in forbiddenchars)
        input = input.strip()
        return input

    def isLive(self) -> bool:
        if len(self._session.streams(self._url)) != 0:
            return True
        return False

    def writeToFile(self):
        data = self._stream.read(1024)
        with open(self._filepath, "ab") as vod:
            vod.write(data)
        return

config = setConfig(r'./twitch_archiver.config')
logging.basicConfig(level=config["log_level"], format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger()
for option in config:
    log.info("config.%s=%s", option, config[option])
if os.path.isdir(config["out_dir"]) == False:
    message = "'out_dir' in twitch_archiver.config is not a directory or does not exist"
    log.critical(message)
    raise Exception(message)
if config["streamer"] == "":
    message = "'streamer' not set in twitch_archiver.config"
    log.critical(message)
    raise Exception(message)
url = f'https://twitch.tv/{config["streamer"]}'

session = Streamlink()
if config["oauth_token"] != "":
    session.set_plugin_option("twitch", "twitch-api-header", f'Authentication=OAuth {config["oauth_token"]}')
session.set_plugin_option("twitch", "record-reruns", config["record_reruns"])
session.set_plugin_option("twitch", "disable-hosting", config["disable_hosting"])
session.set_plugin_option("twitch", "twitch-disable-ads", config["disable_ads"])

async def mainloop():
    while True:
        stream = Stream(session, url)
        await stream.setStream()
        stream.setFilepath(config)
        fetch_title = asyncio.create_task(stream.setTitle())

        log.info("writing stream to '%s'", stream._filepath)
        while stream.isLive():
            stream.writeToFile()
            await asyncio.sleep(0)
        log.info("stream ended")
        
        if fetch_title.done() == False:
            fetch_title.cancel()
            log.error('unable to retrieve stream title')
            stream.updateTitle("title-error")

asyncio.run(mainloop())