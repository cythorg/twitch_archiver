import asyncio, time, os
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

def addTitleToFile(title, filepath):#todo: cleanup FileExistsError handling
    new_filepath = f'{filepath[:-7]}{title}.ts' #the [:-7] slices 'live.ts' from the end of the temporary filename
    while True:
        try:
            os.rename(filepath, new_filepath)
            break
        except FileExistsError:
            new_filepath = f'{filepath[:-7]}{title}_{time.strftime("%H-%M")}.ts'
    return new_filepath

def formatTitle(title):
    forbiddenchars = r'<>:"/\|!?*'
    title = "".join(char for char in title if char not in forbiddenchars)
    title = title.strip()
    return title

async def getStreamTitle(session, url):
    title = None
    while title == None:
        await asyncio.sleep(1)
        plugin = session.resolve_url(url)[1](session, url) #instantiates a new plugin.Twitch class, session.resolve_url returns a tuple(str, type(Plugin), str)
        title = plugin.get_title()
    return title

async def getStream(session, url):
    streamformats = session.streams(url)
    while len(streamformats) == 0 and streamformats.get("best", None) == None:
        await asyncio.sleep(1)
        streamformats = session.streams(url)
    stream = streamformats["best"].open()
    return stream

async def writeStreamToFile(stream, filepath, title):#todo: while bool(data): is unreliable
    vod = open(filepath, "ab")
    data = True
    while bool(data): #change with getstream? bool(data) is not reliable
        data = stream.read(1024)
        vod.write(data)
        await asyncio.sleep(0) #allows other tasks to execute
        if type(title) == asyncio.Task and title.done() == True:
            title = formatTitle(title.result())
            vod.close()
            filepath = addTitleToFile(title, filepath)
            vod = open(filepath, "ab")
    vod.close()
    return


config = setConfig(r'./twitch_archiver.config')
if os.path.isdir(config["out_dir"]) == False:
    raise Exception("'out_dir' in twitch_archiver.config is not a directory or does not exist")
if config["streamer"] == "":
    raise Exception("'streamer' not set in twitch_archiver.config")
url = f'https://twitch.tv/{config["streamer"]}'

session = Streamlink()
if config["oauth_token"] != "":
    session.set_plugin_option("twitch", "twitch-api-header", f'Authentication=OAuth {config["oauth_token"]}')
session.set_plugin_option("twitch", "record-reruns", config["record_reruns"])
session.set_plugin_option("twitch", "disable-hosting", config["disable_hosting"])
session.set_plugin_option("twitch", "twitch-disable-ads", config["disable_ads"])

async def mainloop():
    while True:
        stream = await getStream(session, url)

        directory, streamer, date = config["out_dir"], config["streamer"], time.strftime(config["time_format"]) 
        filepath = f'{directory}{streamer}_{date}_live.ts'

        title = asyncio.create_task(getStreamTitle(session, url))

        await writeStreamToFile(stream, filepath, title)

        if title.done() == False:
            title.cancel()
            addTitleToFile("title-error", filepath)

        await asyncio.sleep(5) #prevents double recording of final ~5 seconds of a stream, linked to bool(data) reliability

asyncio.run(mainloop())