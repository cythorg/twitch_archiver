import time, os
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

def formatTitle(title):
    forbiddenchars = r'<>:"/\|!?*'
    title = "".join(char for char in title if char not in forbiddenchars)
    title = title.strip()
    return title

def getTitle(session, url):
    plugin = session.resolve_url(url)
    title = plugin[0](url).get_metadata()["title"]
    title = formatTitle(title)
    return title

def getFilepath(directory, streamer, title):
    date = time.strftime("%d-%m-%Y")
    filepath = f'{directory}{streamer}_{date}_{title}.ts'
    return filepath

def isStreamLive(session, url):
    if len(session.streams(url)) != 0:
        return True
    else:
        return False

def writeStreamToFile(stream, filepath):
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

while True:
    while isStreamLive(session, url) == False:
        time.sleep(1)
    
    stream = session.streams(url)["best"].open()
    directory, streamer, title = config["out_dir"], config["streamer"], getTitle(session, url)
    filepath = getFilepath(directory, streamer, title)
    writeStreamToFile(stream, filepath)