import asyncio
import logging
import os
import time

from streamlink import PluginError, Streamlink
from typing import BinaryIO

class Stream:
    _url: str = None
    _session: Streamlink = None

    _directory: str = None
    _streamer: str = None
    _time_format: str = None
    _start_time: str = None
    _title: str = None
    _filepath: str = None

    _stream: BinaryIO = None

    _is_live: bool = False
    _timeout: int = 5

    _fetch_is_live: asyncio.Task = None
    _fetch_title: asyncio.Task = None

    def __init__(self, config):
        session = Streamlink()
        if config["oauth_token"] != "":
            session.set_plugin_option("twitch", "api-header", {"Authorization":f'OAuth {config["oauth_token"]}'})
        session.set_plugin_option("twitch", "record-reruns", config["record_reruns"])
        session.set_plugin_option("twitch", "disable-hosting", config["disable_hosting"])
        session.set_plugin_option("twitch", "disable-ads", config["disable_ads"])

        directory = config["out_dir"].replace("\\", "/")
        if directory[-1] != "/": directory += "/"

        self._url = f'https://twitch.tv/{config["streamer"]}'
        self._session = session
        self._directory = directory
        self._streamer = config["streamer"]
        self._time_format = config["time_format"]

    def __await__(self):
        async def ainit():
            self._fetch_is_live = asyncio.create_task(self._fetchIsLive())
            log.info("wating for stream to go live")
            while not self._is_live:
                await asyncio.sleep(0)
            log.info("stream is live")

            self._start_time = time.strftime(self._time_format)
            self._stream = self._session.streams(self._url)["best"].open()
            await self._updateFilepath()
            self._fetch_title = asyncio.create_task(self._fetchTitle())
            return self
        return ainit().__await__()

    async def __aenter__(self):
        await self
        return self

    async def __aexit__(self, exception_type, exception_value, exception_traceback):
        self._stream = self._stream.close()
        while self._fetch_is_live is not None and self._fetch_is_live.cancel():
            await asyncio.sleep(0)
            self._is_live = False
        while self._fetch_title is not None and self._fetch_title.cancel():
            await asyncio.sleep(0)
            log.error("unable to retrieve stream title")
            self._title = "title-error"
            await self._updateFilepath()

        if exception_type:
            if exception_type is PluginError:
                # _fetchIsLive() raises PluginError on session expiration, i.e. when twitch refuses the connection
                log.error(exception_value)
                log.info("twitch.tv refused the connection")
            elif exception_type is OSError:
                # self._stream.read() in the record() method raises OSError("Read Timeout") rarely on stream ended
                log.error(exception_value)
            else:
                return
        return True

    async def _fetchIsLive(self):
        while True:
            await asyncio.sleep(self._timeout)
            try:
                if len(self._session.streams(self._url)) != 0:
                    self._is_live = True
                else:
                    self._is_live = False
            except asyncio.CancelledError as message:
                log.info(message)
                raise
            except PluginError as message:
                log.error("PluginError raised in _fetchIsLive")
                log.error(message)
            except BaseException as message:
                log.error("Unhandled Exception raised in _fetchIsLive")
                log.exception(message)

    async def _fetchTitle(self):
        #await asyncio.sleep(0) # in edge cases where title is immediately avaliable, allows _updateFilepath() in ainit() to complete
        log.info("attempting to resolve stream title")
        while (title := self._session.resolve_url(self._url)[1](self._session, self._url).get_title()) is None:
            # .resolve_url() instantiates a new plugin.Twitch class, returns a tuple(str, type(Plugin), str)
            # .get_title() returns the (re?)initialised title metadata from the (new) plugin.Twitch class
            await asyncio.sleep(self._timeout)
        log.info("resolved stream title")
        self._title = title
        await self._updateFilepath()
        return

    async def _updateFilepath(self):
        forbidden_chars = r'<>:"/\|!?*'
        sanitise_filename = lambda filename : "".join(char for char in filename if char not in forbidden_chars)
        generate_filename = lambda *args : sanitise_filename(f'{("".join(f"_{arg}" for arg in args if arg is not None))[1:]}.ts')

        filepath = f'{self._directory}{generate_filename(self._streamer, self._start_time, self._title)}'
        while os.path.exists(filepath):
            await asyncio.sleep(1)
            filepath = f'{self._directory}{generate_filename(self._streamer, self._start_time, self._title, time.strftime("%H-%M-%S"))}'

        if self._filepath is not None:
            os.rename(self._filepath, filepath)
            log.info("renamed %s to %s", self._filepath, filepath)
        self._filepath = filepath
        return

    async def record(self):
        log.info("writing stream to %s", self._filepath)
        while self._is_live:
            await asyncio.sleep(0)
            data = self._stream.read(2048)
            with open(self._filepath, "ab") as vod:
                vod.write(data)
        log.info("stream ended")
        return

def setConfig(config_file) -> dict:
    with open(config_file, 'r') as f:
        lines = f.readlines()
    config = {}
    for line in lines:
        if line.startswith('#') or len(line.strip()) == 0: continue
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
    raise NotADirectoryError(message)
if os.access(config["out_dir"], os.W_OK) == False:
    message = "'out_dir' in twitch_archiver.config does not have write permissions"
    log.critical(message)
    raise PermissionError(message)
if config["streamer"] == "":
    message = "'streamer' not set in twitch_archiver.config"
    log.critical(message)
    raise ValueError(message)

async def mainloop():
    while True:
        async with Stream(config) as stream:
            await stream.record()

asyncio.run(mainloop())