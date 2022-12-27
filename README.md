# twitch_archiver.py
A simple and somewhat barebones implementation of the [streamlink](https://streamlink.github.io/) python library
## what is this?
This is a small program written for the purpose of recording and downloading livestreams from the livestreaming service 'twitch.tv'

Twitch has a tendency to mute portions and/or remove entire uploads in response to DMCA requests. In addition, be it because of timezones, negligence, ignorance, or choice, it is not possible to be present for every single stream. The problem occurs when missing a stream that also happens to have been DMCA'd, edited, muted, deleted, or is otherwise unavalible through normal means. A problem which is solved by this neat little script, wahoo!

## how do I use this script?
Written and tested for python 3.10.5+, this is __not__ a requirement - your python mileage may vary

Simply clone this repository into a suitable place on your computer or microprocessor of choice, configure the 'twitch_archiver.config' file (see [configuring the config](#configuring-the-config)) and then make sure when you run the script that your working directory contains said config file and you're done

Now the intended use of this script is running 24/7 as a service on a low power microprocessor, but you could just as easily run this from a dedicated machine you use for other things, or even just a terminal on your desktop every time you want to record a stream, or in a terminal on your desktop all the time like a complete degenerate - if you do the latter I envy your disregard for energy prices

### configuring the config
## a mini tutorial
