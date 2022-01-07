## GG-BOT Upload Assistant
Automatically parse, rename, and upload torrents to trackers using the UNIT3D codebase, Xbtit codebase with custom API Wrapper

### Supported sites:
* ACM - [**AsianCinema**](https://asiancinema.me/)
* ATH - [**Aither**](https://aither.cc/)
* BHD - [**Beyond-HD**](https://beyond-hd.me)
* BLU - [**Blutopia**](https://blutopia.xyz)
* R4E - [**Racing4Everyone**](https://racing4everyone.eu/)
* Telly - [**Telly.wtf**](https://telly.wtf/)
* Ntelogo - [**Ntelogo**](https://ntelogo.org/)
* TSP - [**TheScenePlace**](https://thesceneplace.com/)
* DT - [**DesiTorrents**](https://desitorrents.rocks/)


## Installation
### Basic setup (Bare Metal / VM):
1. Clone / download this repository
2. Install necessary packages ```pip3 install -r requirements.txt```
3. Rename `config.env.sample` to `config.env`
4. Fill out the required values in `config.env`
5. Ensure you have [mediainfo](https://mediaarea.net/en/MediaInfo/Download/Ubuntu) & [ffmpeg](https://ffmpeg.org/download.html) installed on your system
6. Optional: Install [mktorrent](https://github.com/pobrn/mktorrent) in your system to use --use_mktorrent flag. (Create .torrent using mktorrent instead of torf)
7. Run the script using [Python3](https://www.python.org/downloads/) (If you're having issues or torf isn't installing, try python3.9)
   
### Basic setup (Docker):
1. Create new folder / dir [`mkdir GGBotUploader`]
2. Enter into the new directory [`cd GGBotUploader`]
3. Pull GG-Bot-Uploader docker image ``` docker pull noobmaster669/gg-bot-uploader:latest```
4. Download `config.env.sample` to the folder GGBotUploader
5. Rename `config.env.sample` to `config.env`
6. Fill out the required values in `config.env`
7. Run GG-Bot-Uploader using docker run command below 
```
docker run -it \
    -v <PATH_TO_YOUR_MEDIA>:/data \
    --env-file config.env \
    noobmaster669/gg-bot-uploader -t ATH -p "/data/<YOUR_FILE_FOLDER>"
```
   <br /> 

## Roadmap
TBD 

## Contributing
TBD

## License
TBD

**Things to note:**
1. We use TMDB API for all things media related (Title, Year, External IDs, etc)
2. If you provide the IMDB ID via ```-imdb```, you must include the 'tt' that precedes the numerical ID
3. If you're trying to pass in a file as an arg, you may find autocomplete isn't working. Do this to fix it
    * (What I mean by autocomplete is when you double hit *Tab*, and the filename/folder gets automatically filled in)
    * ```chmod u+x auto_upload.py```
    * run script using ```./auto_upload.py -t etc -p /path/to/file/autocompletes.now```
4. A folder called ``temp_upload`` will be created which will store the files:
    * ```description.txt``` ```mediainfo.txt``` ```*.torrent```

**Known Issues:**
1. BDInfo packed in docker container doesn't work. Hence Full BDs cannot be uploaded using the docker version
2. Docker volume mounts in debian host system results in permission error in docker container

## Wiki
### [Video usage examples](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Usage:-Video-Examples)
### [Arguments and User Inputs](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Arguments-and-User-Inputs)
### [Environment Configuration File (config.env breakdown)](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Environment-Configuration-File)
### [/site_templates/*.json guide](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Tracker-Templates)
### [Automatic re-uploading (autodl)](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/autodl-irssi-automatic-re-uploading)
### [Docker Run Command Examples](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Docker-Run-Command-Examples)

## Change Log
**1.1**
* Added support for new tracker: DesiTorrents 
* No spoiler screenshot feature
* CICD pipeline optimizations
* Default screenshots count changes
* Strip text feature for torrent dupe checks
* Full season tv-show upload bug fix
* Updated tag naming bug fix

**1.0.1**
* Updated naming conventions for HDR, Atmos Audio, and BluRay source

**1.0**
* Initial Release
* Added docker images for aarch64 and armhf OS Architectures
* CICD Pipeline Changes
* Updated Templates
* Support for Xbtit Platform with custom API
* Screenshot thumbnail feature
