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

async def addTitleToFile(stream, filepath):#todo: cleanup FileExistsError handling
    new_filepath = f'{filepath[:-7]}{stream.title}.ts' #the [:-7] slices 'live.ts' from the end of the temporary filename
    try:
        os.rename(filepath, new_filepath)
    except FileExistsError:
        log.warning("'%s' already exists, appending current time", new_filepath)
        new_filepath = f'{filepath[:-7]}{stream.title}_{time.strftime("%H-%M-%S")}.ts'
    log.info("renamed '%s' to '%s'", filepath, new_filepath)
    return new_filepath

async def writeStreamToFile(stream, filepath):
    log.info("writing stream to '%s'", filepath)
    while stream.isLive():
        data = stream.stream.read(1024)
        with open(filepath, "ab") as vod:
            vod.write(data)
        await asyncio.sleep(0) #allows other tasks to execute
        # if stream._title != None: #utilising classes and callback functions may be a better implementation for this
        #     title = Stream._formatTitle(title.result())
        #     filepath = await addTitleToFile(title, filepath)
    log.info("closed file '%s'", filepath)
    return

class Stream:
    _session = None
    _url = None
    stream = None
    title = None
    def __init__(self, session, url) -> None:
        self._session = session
        self._url = url

    async def setStream(self):
        log.info("waiting for stream to go live")
        streamformats = self._session.streams(self._url)
        while len(streamformats) == 0 and streamformats.get("best", None) == None:
            await asyncio.sleep(1)
            streamformats = self._session.streams(url)
        self.stream = streamformats["best"].open()
        log.info("stream is live")
        return
    
    async def setTitle(self):
        log.info("attempting to resolve stream title")
        while (title := self._session.resolve_url(self._url)[1](self._session, self._url).get_title()) == None:
            # .resolve_url() instantiates a new plugin.Twitch class, returns a tuple(str, type(Plugin), str)
            # .get_title() returns the (re?)initialised title metadata from the (new) plugin.Twitch class
            await asyncio.sleep(1)
        self.title = self._formatTitle(title)
        log.info("resolved stream title")
        return
    
    def _formatTitle(self, title):
        forbiddenchars = r'<>:"/\|!?*'
        title = "".join(char for char in title if char not in forbiddenchars)
        title = title.strip()
        return title

    def isLive(self) -> bool:
        if len(self._session.streams(self._url)) != 0:
            return True
        return False

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

        directory, streamer, date = config["out_dir"], config["streamer"], time.strftime(config["time_format"]) 
        filepath = f'{directory}{streamer}_{date}_live.ts'

        fetchTitle = asyncio.create_task(stream.setTitle())
        fetchTitle.add_done_callback(await addTitleToFile(stream, filepath)) #does not work
        await writeStreamToFile(stream, filepath)

        if stream.title == None:
            fetchTitle.cancel()
            log.error('unable to retrieve stream title')
            addTitleToFile("title-error", filepath)

        await asyncio.sleep(5) #prevents double recording of final ~5 seconds of a stream, linked to bool(data) reliability

asyncio.run(mainloop())