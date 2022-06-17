<div align="center">
<h1 align="center">GG-BOT Upload Assistant & Auto ReUploader</h1>
  <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant">
    <img src="https://i.ibb.co/vsqPhLM/gg-bot-round.png" alt="Logo" width="128">
  </a>
</div>
<br>
<div align="center">
    One size fits all solution for automated torrent uploading
    <br />
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/wikis/home">Read Wiki</a>
    ·
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/issues/new">Report Bug</a>
    ·
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/issues/new">Request Feature</a>
</div>
<br>
<div align="center">
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/commits/master"><img alt="pipeline status" src="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/badges/master/pipeline.svg" /></a>
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/releases"><img alt="Latest Release" src="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/badges/release.svg" /></a>
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/-/commits/master"><img alt="coverage report" src="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant/badges/master/coverage.svg" /></a>
    <a href="https://hub.docker.com/r/noobmaster669/gg-bot-uploader/"><img alt="coverage report" src="https://img.shields.io/docker/pulls/noobmaster669/gg-bot-uploader" /></a>
    <a href="https://gitlab.com/NoobMaster669/gg-bot-upload-assistant"><img src="https://img.shields.io/badge/dynamic/json?color=green&logo=gitlab&label=stars&query=%24.star_count&url=https%3A%2F%2Fgitlab.com%2Fapi%2Fv4%2Fprojects%2F32631784"></a>
</div>

## Overview:
GG-BOT Upload Assistant is a torrent auto uploader to take the manual work out of uploading. The project is a fork of [XPBot](https://github.com/ryelogheat/xpbot) (huge credits to the original team), which has been modified to work with trackers using different codebases. GG-BOT Upload assistant is intended to be a one size fits all solution for automated torrent uploading.


> Please refer to the readme in `dev` branch to see updated roadmaps and new features.

> If you do not wish to use the docker version of the application, its recommended to checkout and use tags instead of branches for stability reasons.


<div align="center">
    <img src="https://imgs.xkcd.com/comics/standards.png">
</div>

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
* Automatic upload to torrent client: Immediate cross-seeding
* Auto Re-Uploader flavour for uploading gods

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
            <td rowspan="11"><strong>UNIT3D</strong></td>
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
            <td><strong>RF</strong></td>
            <td><strong><a href="https://reelflix.xyz/">ReelFliX</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td rowspan="2"><strong>XBTIT</strong></td>
            <td><strong>TSP</strong></td>
            <td><strong><a href="https://thesceneplace.com/">TheScenePlace</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>SZN</strong></td>
            <td><strong><a href="https://swarmazon.club/">Swarmazon</a></strong></td>
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
            <td rowspan="2"><strong>Gazelle</strong></td>
            <td><strong>NBL</strong></td>
            <td><strong><a href="https://nebulance.io">Nebulance</a></strong></td>
        </tr>
        <tr style="text-align: center">
            <td><strong>ANT</strong></td>
            <td><strong><a href="https://anthelion.me">Anthelion</a></strong></td>
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
# Basic setup for Upload Assistant
## Bare Metal / VM:
1. Clone this repository `git clone https://gitlab.com/NoobMaster669/gg-bot-upload-assistant.git`
> It is recommended to checkout a tag and use it instead of using as the master branch, as there is a possibility for master branch to have bug / error / conflicts during merges.<br>
> Checkout a tag using the command `git checkout tags/<TAG>` 
2. Checkout a release tag/version that you wish to use `git checkout tags/2.0`
2. Install necessary packages ```pip install -r requirements.txt```
3. Grand execute permission for user. `chmod u+x auto_upload.py`
4. Copy `config.env` from `samples/assistant` folder to cloned project root.
5. Fill out the required values in `config.env`
> Ensure that you have optional dependencies installed. <br>
> - [MediaInfo](https://mediaarea.net/en/MediaInfo/Download/Ubuntu)
> - [FFmpeg](https://ffmpeg.org/download.html)
> - [unrar]
> - [mktorrent](https://github.com/pobrn/mktorrent): Use --use_mktorrent flag. (Create .torrent using mktorrent instead of torf)
6. Run the script using [Python3](https://www.python.org/downloads/) (If you're having issues or torf isn't installing, try python3.9)
> Run command template ```python3 auto_upload.py -t <TRACKERS> -p "<FILE_OR_FOLDER_TO_BE_UPLOADED>" [OPTIONAL ARGUMENTS 1] [OPTIONAL ARGUMENTS 2...]``
> Please see Bare Metal Installation and Upgrade Wiki for details instructions.

<br>

## Docker (recommended):
1. Create new folder / dir [`mkdir GGBotUploader && cd GGBotUploader`] 
2. Download `samples/assistant/config.env` to the newly created folder (`GGBotUploader`)
3. Fill out the required values in `config.env`
5. Run GG-Bot-Uploader using docker run command below. (For more samples refer to Wiki [Docker Run Command Examples](https://gitlab.com/gg-bot/gg-bot-uploader/-/wikis/Docker-Run-Command-Examples))
```
docker run --rm -it \
    -v <PATH_TO_YOUR_MEDIA>:/data \
    --env-file config.env \
    noobmaster669/gg-bot-uploader -t ATH TSP -p "/data/<YOUR_FILE_FOLDER>"
```
> See [DockerHub](https://hub.docker.com/r/noobmaster669/gg-bot-uploader/tags) for various tags

<br /> 

**Things to note:**
1. We use TMDB API for all things media related (Title, Year, External IDs, etc)
2. If you provide the IMDB ID via ```-imdb```, you must include the 'tt' that precedes the numerical ID
3. When providing multiple database (TMDB, IMDB, TVMAZE ) ids via optional arguments, uploader uses the ids with priority **`IMDB > TMDB > TVMAZE`**
4. Full Disk uploads are supported ONLY in FAT version of the docker images. Look for image tags in the format **`:FullDisk-{TAG}`** 

<br>

**Known Issues / Limitations:** (See RoadMap for release plans)
1. Docker volume mounts in debian host system results in permission error in docker container. (No Proper Fix Available)
    * **Workaround**: Torrent file can be created in debian host os by using mktorrent. Use argument `--use_mktorrent or -mkt`
2. No support for Bluray distributors and Bluray disc regions
3. No official support for Blurays in .iso format
4. No support for 3D Bluray discs

<br>

# Roadmap
### v3.0
- [ ] Add Support for new platforms
    - [ ] Swarmazon
- [ ] Discord notification for auto uploaded data
- [ ] Improved TMDB metadata search Phase 2
- [X] Automatic torrent re-uploader
- [X] Improved dupe check - Phase 1
- [X] Improved screenshots url management
- [X] Improved TMDB metadata search Phase 1
- [X] Support for communicating with torrent clients
    - [X] Qbittorrent
    - [X] Rutorrent
- [X] Implement a caching mechanism
    - [X] Mongo DB
- [X] Release GG-BOT source code to public
- [X] Bug Fixes and Testing Phase 1
- [X] Bug Fixes and Testing Phase 2
- [X] Issue#37: Automatic cross-seeding not working

### v3.0.1
- [ ] EPIC: GG-Bot Visor for reports and failure recoveries
- [ ] Support for overriding target tracker through categories
- [ ] Ability to reuse already existing torrents.

### Backlogs
- [ ] EPIC: Migrate GG-BOT Runtime to work with GG-BOT Auto ReUploader
- [ ] EPIC: Refactor GG-BOT Admin to handle GG-BOT Auto ReUploader
- [ ] Improved Full Disk Support
    - [ ] Support for Bluray Distributors
    - [ ] Detect Bluray disk region automatically
- [ ] Support for communicating with torrent clients
    - [ ] Deluge
    - [ ] Transmission
- [ ] Add support for bitorrent v2 and v2 hybrid torrents
- [ ] Add Support for new platforms
    - [ ] Anasch
    - [ ] MoreThanTV
    - [ ] GreatPosterWall
- [ ] Add support for DVDs

<br>

# Change Log

## **2.0.7**
    Removed Trackers
        * Telly - ShutDown
    
    New Features
        * Ability to resume / reuse assets from previous uploads
        * Improved watch folder movement during post-processing
        * Support for immediate corss-seeding to torrent clients
        * Support for communicating with torrent clients [ immediate-cross-seeding ]
            * Qbittorrent
            * Rutorrent
        * Migrated torrent client feature from v3.0 alpha version
    
    Underhood Changes
        * Refactored dupe check logic
        * Refactored screenshots and image upload logic
        * Add unit tests to existing code
        * Add unit tests to the cicd pipeline
        * Refactored cicd for better performance and faster builds
        * Introded pre-built base images for cicd improvements
        
    Bug Fixes
        * Issue#10: Prevent unnecessary folders from being added in movie uploads
        * Issue#12: 4K WEB-DLs video codec are named as HEVC instead of H.265
        * Issue#33: Dupe check error when dealing with DV HDR release
        * Issue#34: Cross-Seeding uploading torrents for failed uploads
        * Issue#35: HEVC codec being used for web releases
        * Issue#36: Broken screenshots after new UNIT3D update

## **2.0.6**
    New Trackers
        * Anthelion
        * ReelFlix
    
    New Features
        * Refactoring code in anticipation to v3.0 release
        * Improved dupe check with HDR Support
        * Improved dupe check with support for REPACKS and PROPER
        * Dynamic piece size calculation for mktorrent
        * Implemented a Skip Screenshots feature 
        
    Bug Fixes
        * Issue#25: Unhashable list error when uploading tv shows
        * Issue#26: NBL dupe check issue
        * Issue#28: 720p contents being tagged as SD for UNIT3D trackers
        * Issue#30: Application crash while making TMDB API Call
        * Issue#31: Uploads to BIT-HDTV failing

<br>
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
