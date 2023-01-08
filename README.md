# twitch_archiver.py
A simple and somewhat barebones implementation of the [Streamlink](https://streamlink.github.io/) python library
## What is this?
This is a small program written for the purpose of recording and downloading livestreams from the livestreaming service 'twitch.tv'

Twitch has a tendency to mute portions and/or remove entire uploads in response to DMCA requests. In addition, be it because of timezones, negligence, ignorance, or choice, it is not possible to be present for every single stream. The problem occurs when missing a stream that also happens to have been DMCA'd, edited, muted, deleted, or is otherwise unavalible through normal means. A problem which is solved by this neat little script, wahoo!

## How do I use this script?
Written and tested for python 3.10.5+, this is __not__ a requirement - your python mileage may vary

You will however need to install the [Streamlink](https://streamlink.github.io/install.html) python library, this __is__ a requirement

Simply clone this repository into a suitable place on your computer or microprocessor of choice, configure the 'twitch_archiver.config' file (see [configuring the config](#configuring-the-config)) and then make sure when you run the script that your working directory contains said config file and you're done.

To get the script to work with minimum effort the only requirement is to set `streamer=YourStreamerHere` and if nothing else is done streams will saved to the working directory.

Now the intended use of this script is running 24/7 as a service on a low power microprocessor, but you could just as easily run this from a dedicated machine you use for other things, or even just a terminal on your desktop every time you want to record a stream, or in a terminal on your desktop all the time like a complete degenerate - if you do the latter I envy your disregard for energy prices

### Configuring the config
The 'twitch_archiver.config' file contains variable settings that change how the script runs, for the most part it is self-documenting however for a more in-depth explanation of each setting there is the following

 - `log_level`
   
   Has a default value `log_level=INFO`  
   Can be any value (in increasing severity) from `NOTSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`  
   This sets the minimum required log severity before an output is given, e.g. with a log level of `WARNING` everything logged with severity `WARNING` or higher is output, whereas anything below is not, so in this example `WARNING`, `ERROR`, and `CRITICAL` logs will be output but `DEBUG` and `INFO` logs will not    
   Note that counter-intuitively a value of `NOTSET` means that everything will be output, regardless of level. In order to 'turn off' logging you should instead set `log_level=CRITICAL`
 - `out_dir`  
   
   Has a default value `out_dir=./`  
   Can be any value that is compatible with the python `os.path()` library method, as such supports both relative and absolute pathing  
   Remember that relative pathing is only relative to the working directory, which is not always where the script is located  
   This is simply the output directory of the script, stream recordings are saved here. Note that the script is not able to create directories so the value must be a directory that already exists, otherwise an exception will be raised
   
 - `streamer`  
 
   Has no default value `streamer=`  
   The value should be the username of the streamer you wish to record  
   Formatting example `streamer=cythorg`  
   This is not case-sensitive  
   A value must be provided otherwise an exception will be raised  

 - `time_format`  
 
   Has a default value `time_format=%d-%m-%Y`  
   Can be any value that is compatible the python `time.strftime()` method  
   The filenames generated by this script include the date the stream was broadcast, the format of this date is defined by the value of `time_format`, e.g. a stream recorded on the 2nd of January 2023 with `time_format=%d-%m-%Y` will produce an output file with the name `streamer_02-01-2023_stream title.ts`  
   Conversely if you are American you may wish to set `time_format=%m-%d-%Y` which using the same example stream as before would output a file with the name `streamer_01-02-2023_stream title.ts`  
   For a more in-depth formatting guide please visit [strftime.org](https://strftime.org)  
   
 - `oauth_token`  
   
   Has no default value `oauth_token=`  
   The value needs to be aquired from twitch directly  
   Formatting example `oauth_token=abcdefghijklmnopqrstuvwxyz0123`  
   By supplying an OAuth token it allows this script to record streams with the authority of your twitch account, this means that if your twitch account is subscribed to the streamer you are recording or you have a twitch turbo subscribtion then adverts will be disabled. Important to note, regardless of if an OAuth token is specified the `twitch-disable-ads` flag in streamlink can be toggled by this config file's `disable_ads` setting (set to disable ads by default) although this is not as effective as using an OAuth token and therefore the recording may be susceptible to small periods of low quality and/or skipping.    
   In order to get the personal OAuth token from Twitch's website which identifies your account, open https://twitch.tv in your web browser and after a successful login, open the developer tools by pressing F12 or CTRL+SHIFT+I. Then navigate to the "Console" tab or its equivalent of your web browser and execute the following JavaScript snippet, which reads the value of the auth-token cookie, if it exists:  
   ```javascript
   document.cookie.split("; ").find(item=>item.startsWith("auth-token="))?.split("=")[1]
   ```
   The output should look something like this `abcdefghijklmnopqrstuvwxyz0123`  
   The resulting string consisting of 30 alphanumerical characters is your OAuth token  
   Credit for the above explaination as well as more information can be found at https://streamlink.github.io/cli/plugins/twitch.html  

 - Other options  
   The following options are an interface for options in the streamlink twitch plugin  
   Their values can be either True or False, represented by `1` or `0` respectivelty  
   
   `record_reruns`  
   Has a default value `record_reruns=0`  
   Determines whether streams labelled as 're-runs' by the broadcaster will be recorded  
   
   `disable_hosting`  
   Has a default value `disable_hosting=1`  
   Determines whether the script will record streams when the streamer is 'hosting' another channel  
   Note this is untested and may cause strange behaviour or other issues  
   
   `disable_ads`  
   Has a default value `disable_ads=1`  
   Determines whether the the script will record adverts embedded into the stream  
   If for some reason you would like to watch ads in your stream, feel free to change this, I do not know why you would do this to yourself  

## A mini tutorial
//todo
