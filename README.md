# GG-BOT Upload Assistant
Automatically parse, rename, and upload torrents to trackers using the UNIT3D codebase, Xbtit codebase with custom API Wrapper

### Supported sites:
<table>
    <tbody>
         <tr style="text-align: center; font-size:20px">
            <td><strong>Platform</strong></td>
            <td><strong>Acronym</strong></td>
            <td><strong>Site Name</strong></td>
        </th>
        <tr style="text-align: center">
            <td rowspan="10"><strong>UNIT3D</strong></td>
            <td><strong>ACM</strong></td>
            <td><strong><a href="https://asiancinema.me">AsianCinema</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>ATH</strong></td>
            <td><strong><a href="https://aither.cc">Aither</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>BHD</strong></td>
            <td><strong><a href="https://beyond-hd.me">Beyond-HD</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>BLU</strong></td>
            <td><strong><a href="https://blutopia.xyz">Blutopia</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>R4E</strong></td>
            <td><strong><a href="https://racing4everyone.eu">Racing4Everyone</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>Telly</strong></td>
            <td><strong><a href="https://telly.wtf">Telly.wtf</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>Ntelogo</strong></td>
            <td><strong><a href="https://ntelogo.org">Ntelogo</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>DT</strong></td>
            <td><strong><a href="https://desitorrents.rocks/">DesiTorrents</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>UFHD</strong></td>
            <td><strong><a href="https://uncutflixhd.com/">Uncutflixhd</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>UHDHVN</strong></td>
            <td><strong><a href="https://uhd-heaven.xyz/">UHD-Heaven</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>XBTIT</strong></td>
            <td><strong>TSP</strong></td>
            <td><strong><a href="https://thesceneplace.com/">TheScenePlace</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>TBDev</strong></td>
            <td><strong>SPD</strong></td>
            <td><strong><a href="https://speedapp.io/">SpeedApp</a></strong></td>
        </tr>
    </tbody>
</table>

<br>

<!-- Basic setup -->
# Basic setup (Bare Metal / VM):
1. Clone / download this repository
2. Install necessary packages ```pip3 install -r requirements.txt```
3. Rename `config.env.sample` to `config.env`
4. Fill out the required values in `config.env`
5. Ensure you have [mediainfo](https://mediaarea.net/en/MediaInfo/Download/Ubuntu) & [ffmpeg](https://ffmpeg.org/download.html) installed on your system
6. Optional: Install [mktorrent](https://github.com/pobrn/mktorrent) in your system to use --use_mktorrent flag. (Create .torrent using mktorrent instead of torf)
7. Run the script using [Python3](https://www.python.org/downloads/) (If you're having issues or torf isn't installing, try python3.9)
   
   <br>

# Basic setup (Docker):
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
    * Workaround: .torrent can be created in debian host os by using mktorrent. Provide argument `--use_mktorrent or -mkt`

<br>

# Wiki
### [Video usage examples](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Video-examples)
### [Arguments and User Inputs](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Arguments-and-User-Inputs)
### [Environment Configuration File (config.env breakdown)](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Environment-Configuration-File)
### [/site_templates/*.json guide](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Tracker-Templates)
### [Automatic re-uploading (autodl)](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/autodl-irssi-automatic-re-uploading)
### [Docker Run Command Examples](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Docker-Run-Command-Examples)

<br>

# Roadmap
- [ ] Add Support for new platforms
    - [ ] AvistaZ
    - [ ] BIT-HDTV
- [ ] Full Disk Support
    - [X] Pack BDInfo inside container for full disk uploads
    - [ ] Support for Bluray Distributors
    - [ ] Detect Bluray disk region automatically
- [ ] Add support for DVDs
- [ ] Ensure backwards compatibility with bare metal full disk uploads 
- [ ] Move torrents to different locations based on type
- [ ] Support for custom messages / descriptions during upload
- [x] Dynamic media summary
- [x] Frame accurate screenshots

<br>

# Change Log
**1.2 - UNRELEASED**

    ### Underhood changes
    * Performance Optimizations
    * Platform based site tagging
    * Improved argument description and help
    * Dynamic media summary based on the extracted metadata
    * Frame accurate screenshots
    * Environment file key validations
    * Code refactor
    * Masking sensitive data in log file

    ### New Features
    * Support for Blu-ray Full Disc uploads [fat image required]
    * Ability to choose playlist manually for full disk uploads
    * Improved BDInfo parsing
    * Extended BluRay regions list as configurable json
    * Debug mode for detailed analysis
    * Extended Scene Groups list as configurable json
    * Extended Streaming Services list as configurable json
    * Audio Codec list as configurable json
    * Extended audio codec list for full disk codecs
    * TSP internal uploads
    * New Tracker Support : UHD-Heaven
    * Move dot torrents based on type after upload
    * Feature merges from XPBot
        * Support for new tracker: Uncutflixhd
        * Improved dupe check
        * Improved screenshot upload process
        * Added support for ptpimg
        * Removed support for imgyukle

    ### Bug Fixes
    * No dupe message not being shown in certain cases
    * Invalid PA streaming service tagging
    * PQ10, HLG and WCG HDR Formats not being detected
    * TSP dupe check for web sourced contents

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
