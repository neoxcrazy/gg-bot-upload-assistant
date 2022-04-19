# **GG-BOT Upload Assistant**
GG-BOT Upload Assistant is a torrent auto uploader to take the manual work out of uploading. The project is a fork of [XPBot](https://github.com/ryelogheat/xpbot) (huge credits to the original team), which has been modified to work with trackers using different codebases.

<br>

# Main Features
* Generate, parse and attach Mediainfo or BDInfo to torrent uploads
* Support for Full Disk uploads
* Frame Accurate Screenshots
* Generates, uploads and attach screenshots to torrent description
* Ability to decide the thumbnail size for screenshots in bbcode
* Obtains TMDB/IMDB/MAL ids automatically
* Creates name following proper conventions
* Generate .torrent with pytor or mktorrent
* Uploads to various trackers seamlessly
* Multiple Image Host support
* Packed as a docker container. (No need to install any additional tools)
* Automatically move .torrent and media to specified folders after upload
* Customizable uploader signature for torrent descriptions

<br>

## Supported Platforms And Trackers
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
            <td><strong>STT</strong></td>
            <td><strong><a href="https://skipthetrailers.xyz/">SkipTheTrailers</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>STC</strong></td>
            <td><strong><a href="https://skipthecommericals.xyz/">SkipTheCommericals</a></strong></td>
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
        <tr style="text-align: center">
            <td><strong>TorrentDB</strong></td>
            <td><strong>TDB</strong></td>
            <td><strong><a href="https://torrentdb.net/">TorrentDB</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>BIT-HDTV</strong></td>
            <td><strong>BHDTV</strong></td>
            <td><strong><a href="https://www.bit-hdtv.com">BIT-HDTV</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>Gazelle</strong></td>
            <td><strong>NBL</strong></td>
            <td><strong><a href="https://nebulance.io">Nebulance</a></strong></td>
        </tr>
    </tbody>
</table>

## Supported image Hosts
<table>
    <tbody>
        <tr style="text-align: center; font-size:20px">
            <td><strong>#</strong></td>
            <td><strong>Image Host</strong></td>
        </tr>
        <tr>
            <td>1</td>
            <td>imgbox</td>
        </tr>
        <tr>
            <td>2</td>
            <td>imgbb</td>
        </tr>
        <tr>
            <td>3</td>
            <td>freeimage</td>
        </tr>
        <tr>
            <td>4</td>
            <td>ptpimg</td>
        </tr>
        <tr>
            <td>5</td>
            <td>imgfi</td>
        </tr>
        <tr>
            <td>6</td>
            <td>imgur</td>
        </tr>
        <tr>
            <td>7</td>
            <td>snappie</td>
        </tr>
    </tbody>
</table>

<br>

<!-- Basic setup -->
# Basic setup
## Bare Metal / VM:
1. Clone / download this repository
2. Install necessary packages ```pip3 install -r requirements.txt```
3. Rename `config.env.sample` to `config.env`
4. Fill out the required values in `config.env`
5. Ensure you have [mediainfo](https://mediaarea.net/en/MediaInfo/Download/Ubuntu) & [ffmpeg](https://ffmpeg.org/download.html) installed on your system
6. Optional: Install [mktorrent](https://github.com/pobrn/mktorrent) in your system to use --use_mktorrent flag. (Create .torrent using mktorrent instead of torf)
7. Run the script using [Python3](https://www.python.org/downloads/) (If you're having issues or torf isn't installing, try python3.9)
8. Run command template ```python3 auto_upload.py -t TSP SPD BHD BLU -p "FILE_OR_FOLDER_TO_BE_UPLOADED" [OPTIONAL ARGUMENTS 1] [OPTIONAL ARGUMENTS 2...]```

## Docker:
1. Create new folder / dir [`mkdir GGBotUploader`]
2. Enter into the new directory [`cd GGBotUploader`]
3. Pull GG-Bot-Uploader docker image ``` docker pull noobmaster669/gg-bot-uploader:latest``` (See [DockerHub](https://hub.docker.com/r/noobmaster669/gg-bot-uploader/tags) for various tags)
4. Download `config.env.sample` to the folder GGBotUploader
5. Rename `config.env.sample` to `config.env`
6. Fill out the required values in `config.env`
7. Run GG-Bot-Uploader using docker run command below. (For more samples refer to Wiki [Docker Run Command Examples](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Docker-Run-Command-Examples))
```
docker run --rm -it \
    -v <PATH_TO_YOUR_MEDIA>:/data \
    --env-file config.env \
    noobmaster669/gg-bot-uploader -t ATH TSP -p "/data/<YOUR_FILE_FOLDER>"
```

<br /> 

**Things to note:**
1. We use TMDB API for all things media related (Title, Year, External IDs, etc)
2. If you provide the IMDB ID via ```-imdb```, you must include the 'tt' that precedes the numerical ID
3. If you're trying to pass in a file as an arg, you may find autocomplete isn't working. Do this to fix it
    * (What I mean by autocomplete is when you double hit *Tab*, and the filename/folder gets automatically filled in)
    * ```chmod u+x auto_upload.py```
    * run script using ```./auto_upload.py -t etc -p /path/to/file/autocompletes.now```
    * NOTE: This is applicable only when you use the upload assistant on bare metal. Everyhting is taken care of in the docker version.
4. A folder called ``temp_upload`` will be created which will store the files:
    * `*.torrent`
    * `mediainfo.txt` 
    * `url_images.txt`
    * `description.txt`
    * `image_paths.txt`
5. Full Disk uploads are supported ONLY in FAT version of the docker images. Look for image tags in the format **:FullDisk-{TAG}** 

<br>

**Known Issues / Limitations:** (See RoadMap for release plans)
1. Docker volume mounts in debian host system results in permission error in docker container. (No Proper Fix Available)
    * **Workaround**: Torrent file can be created in debian host os by using mktorrent. Use argument `--use_mktorrent or -mkt`
2. No support for Bluray distributors and Bluray disc regions
3. No official support for Blurays in .iso format
4. No support for 3D Bluray discs

<br>

# Roadmap
### v2.0.6
- [ ] Add Support for new platforms
    - [ ] Anasch
- [ ] Add support to apply hybrid mapping to multiple fields
- [X] Refactoring code in anticipation to v3.0 release
- [X] Improved dupe check with HDR Support
- [X] Dynamic piece size calculation for mktorrent
- [X] Issue#25: Unhashable list error when uploading tv shows
- [X] Issue#26: NBL dupe check issue
- [X] Issue#28: 720p contents being tagged as SD for UNIT3D trackers

### v2.0.7
- [ ] Add support for immediate cross-seeding to torrent clients
- [X] Support for communicating with torrent clients [ immediate-cross-seeding ]
    - [X] Qbittorrent
    - [X] Rutorrent
- [ ] Migrate torrent client feature from v3.0 alpha version

### v3.0
- [X] Automatic torrent re-uploader
- [X] Improved dupe check - Phase 1
- [X] Improved TMDB metadata search
- [X] Support for communicating with torrent clients
    - [X] Qbittorrent
    - [X] Rutorrent
- [X] Implement a caching mechanism
    - [X] Mongo DB
    - [X] Redis DB - Half baked (Might be deprecated)
- [X] GG-Bot Visor for reports and failure recoveries
- [ ] Support for overriding target tracker through categories
- [ ] Bug Fixes and Testing
- [ ] Discord notification for auto uploaded data

### Backlogs
- [ ] Improved Full Disk Support
    - [ ] Support for Bluray Distributors
    - [ ] Detect Bluray disk region automatically
- [ ] Improved dupe check - Phase 2
- [ ] Support for communicating with torrent clients
    - [ ] Deluge
    - [ ] Transmission
- [ ] Add support for bitorrent v2 and v2 hybrid torrents
- [ ] Add Support for new platforms
    - [ ] Anthelion
    - [ ] MoreThanTV
    - [ ] ReelFliX
- [ ] Add support for DVDs

<br>

# Change Log

## **2.0.5**
    New Trackers
        * SkipTheTrailers

    New Features
        * Support for default trackers
        * Ability to upload to all available trackers (USE WITH CAUTION)
        * Improved TMDB search results filtering
    
    Bug Fixes
        * Issue#19: Multiple episode naming bug fixed
        * Issue#20: Uploader crash when handling complete packs from tracker
        * Issue#23: IMDB Id cannot be obtained from TVMaze

<br>

## **2.0.4**

    New Trackers
        * BIT-HDTV
        * Nebulance

    New Image Hosts
        * Snappie

    New Features
        * Added new bugs to be fixed :p
        * Support for TVMaze and a database for TV Shows
        * Improved key translations and mapping for tracker specific jobs
        * Support for screenshots without thumbnail size limit
        * New Hybrid Mapping for tracker SkipTheCommercials
        * Added support for more streaming services

    Bug Fixes
        * Issue#9: Multiple dupe prompt being asked bug fixed
        * Issue#11: DTS-X audio codec naming error bug fixed
        * Issue#14: BHDTV <3 symbol missing bug fixed
        * Issue#15: HLG not detected from file name bug fixed

<br>

## **2.0.3**

    New Image Hosts
        * Imgur

    Bug Fixes
        * ptp image uploads not working bug fix

<br>

## **2.0.2**

    New Trackers
        * TorrentDB

    New Features
        * Support for custom messages / descriptions during upload
        * Support for custom upload signatures for regular uploaders

    Bug Fixes
        * SpeedApp screenshots missing bug fixed

<br>

## **2.0.1**

    New Trackers
        * SkipTheCommercials

    New Image Hosts
        * Imgfi

    Underhood changes
        * Improved batch processing
        * Refactor tracker acronyms and api keys to config file

<br>

## **2.0**

    New Trackers
        * SpeedApp
        * UHD-Heaven

    Underhood changes
        * Performance Optimizations
        * Platform based site tagging
        * Improved argument description and help
        * Dynamic media summary based on the extracted metadata
        * Frame accurate screenshots
        * Environment file key validations
        * Code refactor
        * Masking sensitive data in log file
        * Various steps added to reduce the coupling with UNIT3D codebase

    New Features
        * Hybrid category mapping [See Site-Templates Wiki]
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
        * Move dot torrents based on type after upload
        * Feature merges from XPBot
            * Improved dupe check
            * Improved screenshot upload process
            * Added support for ptpimg
            * Removed support for imgyukle

    Bug Fixes
        * No dupe message not being shown in certain cases
        * Invalid PA streaming service tagging
        * PQ10, HLG and WCG HDR Formats not being detected
        * TSP dupe check for web sourced contents

<br>

##  **1.1**
    New Trackers
        * DesiTorrents 
    New Features
        * No spoiler screenshot feature
        * CICD pipeline optimizations
        * Default screenshots count changes
        * Strip text feature for torrent dupe checks
    Bug Fixes
        * Full season tv-show upload bug fix
        * Updated tag naming bug fix

<br>

##  **1.0.1**
    Bug Fixes
        * Updated naming conventions for HDR, Atmos Audio, and BluRay source

<br>

##  **1.0**
    New Features
        * Initial Release
        * Added docker images for aarch64 and armhf OS Architectures
        * CICD Pipeline Changes
        * Updated Templates
        * Support for Xbtit Platform with custom API
        * Screenshot thumbnail feature

<br>

# Wiki
### [Video usage examples](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Usage:-Video-Examples)
### [Arguments and User Inputs](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Arguments-and-User-Inputs)
### [Environment Configuration File (config.env breakdown)](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Environment-Configuration-File)
### [/site_templates/*.json guide](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Tracker-Templates)
### [Automatic re-uploading (autodl)](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/autodl-irssi-automatic-re-uploading)
### [Docker: Run Command Examples](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Docker-Run-Command-Examples)
### [Docker: Noob Friendly Setup Guide](https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/Noob-Friendly-Setup-Guide)

<br>
