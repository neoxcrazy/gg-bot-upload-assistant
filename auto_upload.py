#!/usr/bin/env python3

# default included packages
import os
import re
import sys
import glob
import time
import json
import shutil
import logging
import argparse
import subprocess
import datetime
from pprint import pformat
from pathlib import Path

# These packages need to be installed
import requests
from torf import Torrent
from ffmpy import FFprobe
from guessit import guessit
from dotenv import load_dotenv
from dotenv import dotenv_values
from pymediainfo import MediaInfo

# Rich is used for printing text & interacting with user input
from rich import box
from rich.table import Table
from rich.console import Console
from rich.traceback import install
from rich.prompt import Prompt, Confirm

# Search for **START** to get to the execution entry point of the bot.

# This is used to take screenshots and eventually upload them to either imgbox, imgbb, ptpimg or freeimage
from images.upload_screenshots import take_upload_screens

# Method that will search for dupes in trackers.
from search_for_dupes import search_for_dupes_api

# Used for rich.traceback
install()

# For more control over rich terminal content, import and construct a Console object.
console = Console()

# Import & set some global variables that we reuse later
# This shows the full path to this files location
working_folder = os.path.dirname(os.path.realpath(__file__))

# This is an important dict that we use to store info about the media file as we discover it
# Once all necessary info has been collected we will loop through this dict and set the correct tracker API Keys to it
torrent_info = {}

# Debug logs for the upload processing
# Logger running in "w" : write mode
logging.basicConfig(filename='{}/upload_script.log'.format(working_folder), filemode="w", level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')

# Load the .env file that stores info like the tracker/image host API Keys & other info needed to upload
load_dotenv(f'{working_folder}/config.env')
# Getting the keys present in the config.env.sample
# These keys are then used to compare with the env variable keys provided during runtime.
# Presently we just displays any missing keys, in the future do something more useful with this information
sample_env_keys = dotenv_values(f'{working_folder}/config.env.sample').keys()

# validating env file with expected keys from sample file
for key in sample_env_keys:
    if os.getenv(key) is None:
        console.print(f"Outdated config.env file. Variable [red][bold]{key}[/bold][/red] is missing.", style="blue")

# Used to correctly select json file
# the value in this dictionay must correspond to the file name of the site template
acronym_to_tracker = {"blu": "blutopia",
                      "bhd": "beyond-hd",
                      "r4e": "racing4everyone",
                      "acm": "asiancinema",
                      "ath": "aither",
                      "telly": "telly",
                      "tsp": "thesceneplace",
                      "dt": "desitorrents",
                      "ufhd": "uncutflixhd",
                      "ntelogo": "ntelogo"}

# Now assign some of the values we get from 'config.env' to global variables we use later
api_keys_dict = {
    'bhd_api_key': os.getenv('BHD_API_KEY'),
    'dt_api_key': os.getenv('DT_API_KEY'),
    'ufhd_api_key': os.getenv('UFHD_API_KEY'),
    'blu_api_key': os.getenv('BLU_API_KEY'),
    'acm_api_key': os.getenv('ACM_API_KEY'),
    'r4e_api_key': os.getenv('R4E_API_KEY'),
    'ath_api_key': os.getenv('ATH_API_KEY'),
    'telly_api_key': os.getenv('TELLY_API_KEY'),
    'ntelogo_api_key': os.getenv('NTELOGO_API_KEY'),
    'tmdb_api_key': os.getenv('TMDB_API_KEY'),
    'tsp_api_key': os.getenv('TSP_API_KEY')
}
# Make sure the TMDB API is provided [Mandatory Property]
try:
    if len(api_keys_dict['tmdb_api_key']) == 0:
        raise AssertionError("TMDB API key is required")
except AssertionError as err:  # Log AssertionError in the logfile and quit here
    logging.exception("TMDB API Key is required")
    raise err

# Import 'auto_mode' status
if str(os.getenv('auto_mode')).lower() not in ['true', 'false']:
    logging.critical('auto_mode is not set to true/false in config.env')
    raise AssertionError("set 'auto_mode' equal to true/false in config.env")
auto_mode = str(os.getenv('auto_mode')).lower()

# import discord webhook url (if exists)
if len(os.getenv('DISCORD_WEBHOOK')) != 0:
    discord_url = str(os.getenv('DISCORD_WEBHOOK'))
else:
    discord_url = None

# TODO change the implementation to work with containerized solution
bdinfo_script = os.getenv('bdinfo_script')
# TODO integrate this feature with AvistaZ platform
is_live_on_site = str(os.getenv('live')).lower()

# Setup args
parser = argparse.ArgumentParser()

# Required Arguments [Mandatory]
required_args = parser.add_argument_group('Required Arguments')
required_args.add_argument('-t', '--trackers', nargs='*', required=True, help="Tracker(s) to upload to. Space-separates if multiple (no commas)")
required_args.add_argument('-p', '--path', nargs='*', required=True, help="Use this to provide path(s) to file/folder")

# Commonly used args:
common_args = parser.add_argument_group('Commonly Used Arguments')
common_args.add_argument('-tmdb', nargs=1, help="Use this to manually provide the TMDB ID")
common_args.add_argument('-imdb', nargs=1, help="Use this to manually provide the IMDB ID")
common_args.add_argument('-anon', action='store_true', help="if you want your upload to be anonymous (no other info needed, just input '-anon'")

# Less commonly used args (Not essential for most)
uncommon_args = parser.add_argument_group('Less Common Arguments')
uncommon_args.add_argument('-title', nargs=1, help="Custom title provided by the user")
uncommon_args.add_argument('-type', nargs=1, help="Use to manually specify 'movie' or 'tv'")
uncommon_args.add_argument('-reupload', nargs='*', help="This is used in conjunction with autodl to automatically re-upload any filter matches")
uncommon_args.add_argument('-batch', action='store_true', help="Pass this arg if you want to upload all the files/folder within the folder you specify with the '-p' arg")
uncommon_args.add_argument('-disc', action='store_true', help="If you are uploading a raw dvd/bluray disc you need to pass this arg")
uncommon_args.add_argument('-e', '--edition', nargs='*', help="Manually provide an 'edition' (e.g. Criterion Collection, Extended, Remastered, etc)")
uncommon_args.add_argument('-nfo', nargs=1, help="Use this to provide the path to an nfo file you want to upload")
uncommon_args.add_argument('-d', '--debug', action='store_true', help="Used for debugging. Writes debug lines to log file")
uncommon_args.add_argument('-mkt', '--use_mktorrent', action='store_true', help="Use mktorrent instead of torf (Latest git version only)")
uncommon_args.add_argument('-fpm', '--force_pymediainfo', action='store_true', help="Force use PyMediaInfo to extract video codec over regex extraction from file name")

# args for Internal uploads
internal_args = parser.add_argument_group('Internal Upload Arguments')
internal_args.add_argument('-internal', action='store_true', help="(Internal) Used to mark an upload as 'Internal'")
internal_args.add_argument('-freeleech', action='store_true', help="(Internal) Used to give a new upload freeleech")
internal_args.add_argument('-featured', action='store_true', help="(Internal) feature a new upload")
internal_args.add_argument('-doubleup', action='store_true', help="(Internal) Give a new upload 'double up' status")
internal_args.add_argument('-tripleup', action='store_true', help="(Internal) Give a new upload 'triple up' status [XBTIT Exclusive]")
internal_args.add_argument('-sticky', action='store_true', help="(Internal) Pin the new upload")

args = parser.parse_args()


def write_file_contents_to_log_as_debug(file_path):
    """
        Method reads and writes the contents of the provided `file_path` to the log as debug lines.
        note that the method doesn't check for debug mode or not, those checks needs to be done by the caller
    """
    with open(file_path, 'r') as file_contents:
        lines = file_contents.readlines()
        [ logging.debug(line.replace('\\n','').strip()) for line in lines ]


def parse_bdinfo(bdinfo_location):
    # TODO add support for .iso extraction
    # TODO add support for 3D bluray disks
    """
        Attributes in returned bdinfo
        -----KEY------------DESCRIPTION-----------------------------EXAMPLE VALUE----------
            playlist: playlist being parsed                     : 00001.MPL
            size    : size of the disk                          : 54.597935752011836
            length  : duration of playback                      : 1:37:17
            title   : title of the disk                         : Venom: Let There Be Carnage - 4K Ultra HD
            label   : label of the disk                         : Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
            video   : {
                "codec"         : video codec                   : MPEG-H HEVC Video
                "bitrate"       : the video bitrate             : 55873 kbps
                "resolution"    : the resolution of the video   : 2160p
                "fps"           : the fps                       : 23.976 fps
                "aspect_ratio"  : the aspect ratio              : 16:9
                "profile"       : the video profile             : Main 10 @ Level 5.1 @ High
                "bit_depth"     : the bit depth                 : 10 bits
                "dv_hdr"        : DV or HDR (if present)        : HDR10
                "color"         : the color parameter           : BT.2020
            }
            audio   : {
                "language"      : the audio language            : English
                "codec"         : the audio codec               : Dolby TrueHD
                "channels"      : the audo channels             : 7.1
                "sample_rate"   : the sample rate               : 48 kHz
                "bitrate"       : the average bit rate          : 4291 kbps
                "bit_depth"     : the bit depth of the audio    : 24-bit
                "atmos"         : whether atmos is present      : Atmos Audio
            }
    """
    bdinfo = dict()
    bdinfo['video'] = list()
    bdinfo['audio'] = list()
    with open(bdinfo_location, 'r') as file_contents:
        lines = file_contents.readlines()
        for line in lines:
            line = line.strip()
            line = line.replace("*", "").strip() if line.startswith("*") else line
            if line.startswith("Playlist:"):                        # Playlist: 00001.MPLS              ==> 00001.MPLS
                bdinfo['playlist'] = line.split(':', 1)[1].strip() 
            elif line.startswith("Disc Size:"):                     # Disc Size: 58,624,087,121 bytes   ==> 54.597935752011836
                size = line.split(':', 1)[1].replace("bytes", "").replace(",", "")
                size = float(size)/float(1<<30)
                bdinfo['size'] = size                              
            elif line.startswith("Length:"):                        # Length: 1:37:17.831               ==> 1:37:17
                bdinfo['length'] = line.split(':', 1)[1].split('.',1)[0].strip()
            elif line.startswith("Video:"):
                """
                    video_components: examples [video_components_dict is the mapping of these components and their indexes]
                    MPEG-H HEVC Video / 55873 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-H HEVC Video / 2104 kbps / 1080p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / Dolby Vision / BT.2020
                    MPEG-H HEVC Video / 35033 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-4 AVC Video / 34754 kbps / 1080p / 23.976 fps / 16:9 / High Profile 4.1
                """
                video_components_dict = {
                    0 : "codec",
                    1 : "bitrate",
                    2 : "resolution",
                    3 : "fps",
                    4 : "aspect_ratio",
                    5 : "profile",
                    6 : "bit_depth",
                    7 : "dv_hdr",
                    8 : "color",
                }
                video_components = line.split(':', 1)[1].split('/')
                video_metadata = {}
                for loop_variable in range(0, video_components.__len__()):
                    video_metadata[video_components_dict[loop_variable]] = video_components[loop_variable]

                if "HEVC" in video_metadata["codec"]:
                    video_metadata["codec"] = "HEVC"
                elif "AVC" in video_metadata["codec"]:
                    video_metadata["codec"] = "AVC"

                bdinfo["video"].append(video_metadata)
            elif line.startswith("Audio:"):
                """
                    audio_components: examples 
                    English / Dolby TrueHD/Atmos Audio / 7.1 / 48 kHz /  4291 kbps / 24-bit (AC3 Embedded: 5.1 / 48 kHz /   640 kbps / DN -31dB)
                    English / DTS-HD Master Audio / 7.1 / 48 kHz /  5002 kbps / 24-bit (DTS Core: 5.1 / 48 kHz /  1509 kbps / 24-bit)
                    English / Dolby Digital Audio / 5.1 / 48 kHz /   448 kbps / DN -31dB
                    English / DTS Audio / 5.1 / 48 kHz /   768 kbps / 24-bit
                """
                audio_components_dict = {
                    0 : "language",
                    1 : "codec", # atmos => added if present optionally
                    2 : "channels",
                    3 : "sample_rate",
                    4 : "bitrate",
                    5 : "bit_depth" 
                }
                if "(" in line:
                    line = line.split("(")[0] # removing the contents inside bracket
                audio_components = line.split(':', 1)[1].split('/ ') # not so sure about this /{space}
                audio_metadata = {}
                for loop_variable in range(0, audio_components.__len__()):
                    if "Atmos" in audio_components[loop_variable]: # identifying and tagging atmos audio
                        codec_split = audio_components[loop_variable].split("/")
                        audio_metadata["atmos"] = codec_split[1].strip()
                        audio_components[loop_variable] = codec_split[0].strip()

                    audio_metadata[audio_components_dict[loop_variable]] = audio_components[loop_variable]
                bdinfo["audio"].append(audio_metadata)
            elif line.startswith("Disc Title:"):        # Disc Title: Venom: Let There Be Carnage - 4K Ultra HD
                bdinfo['title'] = line.split(':', 1)[1].strip()
            elif line.startswith("Disc Label:"):        # Disc Label: Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
                bdinfo['label'] = line.split(':', 1)[1].strip()
    return bdinfo


def check_for_dupes_in_tracker(tracker, temp_tracker_api_key):
    """
        Method to check for any duplicate torrents in the tracker.
        First we read the configuration for the tracker and format the title according to the tracker configuration
        Then invoke the `search_for_dupes_api` method and return the result.

        Returns True => Dupes are present in the tracker and cannot proceed with the upload
        Returns False => No dupes present in the tracker and upload can continue
    """
    # Open the correct .json file since we now need things like announce URL, API Keys, and API info
    with open(f"{working_folder}/site_templates/" + str(acronym_to_tracker.get(str(tracker).lower())) + ".json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    # -------- format the torrent title --------
    format_title(config)

    # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
    return search_for_dupes_api(acronym_to_tracker[str(tracker).lower()], torrent_info["imdb"], torrent_info=torrent_info, tracker_api=temp_tracker_api_key, debug=args.debug)


def delete_leftover_files():
    """
        Used to remove temporary files (mediainfo.txt, description.txt, screenshots) from the previous upload
        Func is called at the start of each run to make sure there are no mix up with wrong screenshots being uploaded etc.

        Not much significance when using the containerized solution, however if the `temp_upload` folder in container
        is mapped to a docker volume / host path, then clearing would be best. Hence keeping this method.
    """
    for old_temp_data in ["/temp_upload/", "/images/screenshots/"]:
        # We need these folders to store things like screenshots, .torrent & description files.
        # So create them now if they don't exist
        try:
            os.mkdir(f"{working_folder}{old_temp_data}")
        except FileExistsError:
            # If they do already exist then we need to remove any old data from them
            files = glob.glob(f'{working_folder}{old_temp_data}*')
            for f in files:
                os.remove(f)
            logging.info("deleted the contents of the folder: {}".format(working_folder + old_temp_data))


def identify_type_and_basic_info(full_path, guess_it_result):
    """
        guessit is typically pretty good at getting the title, year, resolution, group extracted
        but we need to do some more work for things like audio channels, codecs, etc
            (Some groups (D-Z0N3 is a pretty big offender here)

        for example 'D-Z0N3' used to not include the audio channels in their filename so we need to use
            ffprobe to get that ourselves (pymediainfo has issues when dealing with atmos and more complex codecs)
        
        :param full_path: the full path for the file / folder

        Returns `skip_to_next_file` if there are no video files in thhe provided folder
    """
    console.line(count=2)
    console.rule(f"Analyzing & Identifying Video", style='red', align='center')
    console.line(count=1)
    
    # ------------ Save obvious info we are almost guaranteed to get from guessit into torrent_info dict ------------ #
    # But we can immediately assign some values now like Title & Year
    if not guess_it_result["title"]:
        raise AssertionError("Guessit could not even extract the title, something is really wrong with this filename..")

    torrent_info["title"] = guess_it_result["title"]
    if "year" in guess_it_result:  # Most TV Shows don't have the year included in the filename
        torrent_info["year"] = str(guess_it_result["year"])

    # ------------ Save basic info we get from guessit into torrent_info dict ------------ #
    # We set a list of the items that are required to successfully build a torrent name later
    # if we are missing any of these keys then call another function that will use ffprobe, pymediainfo, regex, etc
    # to try and extract it ourselves, should that fail we can prompt the user
    # (only if auto_mode=false otherwise we just guess and upload what we have)
    keys_we_want_torrent_info = ['release_group', 'episode_title']
    keys_we_need_torrent_info = ['screen_size', 'source', 'audio_channels']

    if args.type:
        if args.type[0] in ('tv', 'movie'):
            torrent_info["type"] = 'episode' if args.type[0] == 'tv' else 'movie'
            logging.info(f"Using user provided type {torrent_info['type']}")
        else:
            logging.error(f'User has provided invalid media type as argument {args.type[0]}. Type will be detected dynamically!')
            keys_we_need_torrent_info.append('type')
    else:
        logging.info("Type will be detected dynamically!")
        keys_we_need_torrent_info.append('type')    

    keys_we_need_but_missing_torrent_info = []
    # We can (need to) have some other information in the final torrent title like 'editions', 'hdr', etc
    # All of that is important but not essential right now so we will try to extract that info later in the script
    logging.debug(f"Attempting to detect the following keys from guessit :: {keys_we_need_torrent_info}")
    for basic_key in keys_we_need_torrent_info:
        if basic_key in guess_it_result:
            torrent_info[basic_key] = str(guess_it_result[basic_key])
        else:
            keys_we_need_but_missing_torrent_info.append(basic_key)
 
    # As guessit evolves and adds more info we can easily support whatever they add
    # and insert it into our main torrent_info dict
    logging.debug(f"Attempting to detect the following keys from guessit :: {keys_we_want_torrent_info}")
    for wanted_key in keys_we_want_torrent_info:
        if wanted_key in guess_it_result:
            torrent_info[wanted_key] = str(guess_it_result[wanted_key])

    # setting NOGROUP as group if the release_group cannot be identified from guessit
    if torrent_info["release_group"] is None:
        torrent_info["release_group"] == "NOGROUP"
        logging.debuf(f"Release group could not be identified by guessit. Setting release group as NOGROUP")
    
    # ------------ Format Season & Episode (Goal is 'S01E01' type format) ------------ #
    # Depending on if this is a tv show or movie we have some other 'required' keys that we need (season/episode)
    if "type" not in torrent_info:
        raise AssertionError("'type' is not set in the guessit output, something is seriously wrong with this filename")
    if torrent_info["type"] == "episode":  # guessit uses 'episode' for all tv related content (including seasons)
        # Set a default value for season and episode
        torrent_info["season_number"] = 0
        torrent_info["episode_number"] = 0

        if 'season' not in guess_it_result:
            logging.error("could not detect the 'season' using guessit")
            if 'date' in guess_it_result:  # we can replace the S**E** format with the daily episodes date
                daily_episode_date = str(guess_it_result["date"])
                logging.info(f'detected a daily episode, using the date ({daily_episode_date}) instead of S**E**')
                torrent_info["s00e00"] = daily_episode_date
            else:
                logging.critical("Could not detect Season or date (daily episode) so we can not upload this")
                sys.exit(console.print("\ncould not detect the 'season' or 'date' (daily episode). Cannot upload this.. quitting now\n", style="bold red"))
        else:
            # This else is for when we have a season number, so we can immediately assign it to the torrent_info dict
            torrent_info["season_number"] = int(guess_it_result["season"])
            # check if we have an episode number
            if 'episode' in guess_it_result:
                torrent_info["episode_number"] = int(guess_it_result["episode"])
                torrent_info["s00e00"] = f'S{torrent_info["season_number"]:02d}E{torrent_info["episode_number"]:02d}'
            else:
                # if we don't have an episode number we will just use the season number
                torrent_info["s00e00"] = f'S{torrent_info["season_number"]:02d}'
            
    # ------------ If uploading folder, select video file from within folder ------------ #
    # First make sure we have the path to the actual video file saved in the torrent_info dict
    # for example someone might want to upload a folder full of episodes, we need to select at least 1 episode to use pymediainfo/ffprobe on
    if os.path.isdir(torrent_info["upload_media"]):
        # Add trailing forward slash if missing
        if not str(torrent_info["upload_media"]).endswith('/'):
            torrent_info["upload_media"] = f'{str(torrent_info["upload_media"])}/'

        # the episode/file that we select will be stored under "raw_video_file" (full path + episode/file name)
        
        # Some uploads are movies within a folder and those folders occasionally contain non-video files nfo, sub, srt, etc files
        # we need to make sure we select a video file to use for mediainfo later

        # First check to see if we are uploading a 'raw bluray disc'
        if args.disc:
            # Verify that the bdinfo script exists only when executed on bare metal / VM instead of container
            # The containerized version has bdinfo packed inside.
            if not os.getenv("IS_CONTAINERIZED") == "true" and not os.path.isfile(bdinfo_script):
                logging.critical("You've specified the '-disc' arg but have not supplied a valid bdinfo script path in config.env")
                logging.info("Can not upload a raw disc without bdinfo output, update the 'bdinfo_script' path in config.env")
                raise AssertionError(f"The bdinfo script you specified: ({bdinfo_script}) does not exist")

            # Now that we've "verified" bdinfo is on the system, we can analyze the folder and continue the upload
            if not os.path.exists(f'{torrent_info["upload_media"]}BDMV/STREAM/'):
                logging.critical("BD folder not recognized. We can only upload if we detect a '/BDMV/STREAM/' folder")
                raise AssertionError("Currently unable to upload .iso files or disc/folders that does not contain a '/BDMV/STREAM/' folder")

            bd_max_size = 0
            bd_max_file = ""
            for folder, subfolders, files in os.walk(f'{torrent_info["upload_media"]}BDMV/STREAM/'):
                # checking the size of each file
                for bd_file in files:
                    size = os.stat(os.path.join(folder, bd_file)).st_size
                    # updating maximum size
                    if size > bd_max_size:
                        bd_max_size = size
                        bd_max_file = os.path.join(folder, bd_file)

            torrent_info["raw_video_file"] = bd_max_file # file with the largest size inside the STEAM folder

            bdinfo_output_split = str(' '.join(str(subprocess.check_output(["mono", "/usr/src/app/build/BDInfo.exe", torrent_info["upload_media"], "-l"])).split())).split(' ')
            all_mpls_playlists = re.findall(r'\d\d\d\d\d\.MPLS', str(bdinfo_output_split))
            logging.info(f"All mpls playlists identified from bluray disc {all_mpls_playlists}")
            logging.debug("BDInfo List Output ::::::::::::::::::::::::::::::::")
            logging.debug(pformat(bdinfo_output_split))

            dict_of_playlist_length_size = {}
            dict_of_playlist_info_list = [] # list of dict
            # Still identifying the largest playlist here...
            for index, mpls_playlist in enumerate(bdinfo_output_split):
                if mpls_playlist in all_mpls_playlists:
                    playlist_details = {}
                    playlist_details["no"] = bdinfo_output_split[index - 2].replace("\\n", "")
                    playlist_details["group"] = bdinfo_output_split[index - 1]
                    playlist_details["file"] = bdinfo_output_split[index]
                    playlist_details["length"] = bdinfo_output_split[index + 1]
                    playlist_details["est_bytes"] = bdinfo_output_split[index + 2]
                    playlist_details["msr_bytes"] = bdinfo_output_split[index + 3]
                    playlist_details["size"] = int(str(bdinfo_output_split[index + 2]).replace(",", ""))
                    dict_of_playlist_info_list.append(playlist_details)
                    dict_of_playlist_length_size[mpls_playlist] = int(str(bdinfo_output_split[index + 2]).replace(",", ""))

            # sorting list based on the `size` key inside the dictionary
            dict_of_playlist_info_list = sorted(dict_of_playlist_info_list, key=lambda d: [d["size"]], reverse=True)
            
            # In auto_mode we just choose the largest playlist
            if auto_mode == 'false':
                # here we display the playlists identified ordered in decending order by size
                # the default choice will be the largest playlist file
                # user will be given the option to choose any different playlist file
                bdinfo_list_table = Table(box=box.SQUARE, title='BDInfo Playlists', title_style='bold #be58bf')
                bdinfo_list_table.add_column("Playlist #", justify="center", style='#38ACEC')
                bdinfo_list_table.add_column("Group", justify="center", style='#38ACEC')
                bdinfo_list_table.add_column("Playlist File", justify="center", style='#38ACEC')
                bdinfo_list_table.add_column("Duration", justify="center", style='#38ACEC')
                bdinfo_list_table.add_column("Estimated Bytes", justify="center", style='#38ACEC')
                # bdinfo_list_table.add_column("Measured Bytes", justify="center", style='#38ACEC') # always `-` in the tested BDs
                
                for playlist_details in dict_of_playlist_info_list:
                    bdinfo_list_table.add_row(str(playlist_details['no']), playlist_details['group'], f"[chartreuse1][bold]{str(playlist_details['file'])}[/bold][/chartreuse1]", 
                        playlist_details['length'], playlist_details['est_bytes'], end_section=True)
                
                console.print("For BluRay disk you need to select which playlist need to be analyzed", style='bold blue')
                console.print("By default the largest playlist will be selected\n")
                console.print(bdinfo_list_table)

                list_of_num = []
                for i in range(len(dict_of_playlist_info_list)):
                    i += 1
                    list_of_num.append(str(i))
                
                user_input_playlist_id_num = Prompt.ask("Choose which `Playlist #` to analyze:", choices=list_of_num, default="1")
                largest_playlist = dict_of_playlist_info_list[int(user_input_playlist_id_num) - 1]["file"]
                logging.debug(f"Used decided to select the playlist [{largest_playlist}] with Playlist # [{user_input_playlist_id_num}]")
                torrent_info["largest_playlist"] = largest_playlist
                logging.info(f"Largest playlist obtained from bluray disc: {largest_playlist}")
            else:
                largest_playlist_value = max(dict_of_playlist_length_size.values())
                largest_playlist = list(dict_of_playlist_length_size.keys())[list(dict_of_playlist_length_size.values()).index(largest_playlist_value)]
                torrent_info["largest_playlist"] = largest_playlist
                logging.info(f"Largest playlist obtained from bluray disc: {largest_playlist}")
        else:
            for individual_file in sorted(glob.glob(f"{torrent_info['upload_media']}/*")):
                found = False  # this is used to break out of the double nested loop
                logging.info(f"Checking to see if {individual_file} is a video file")
                if os.path.isfile(individual_file):
                    file_info = MediaInfo.parse(individual_file)
                    for track in file_info.tracks:
                        if track.track_type == "Video":
                            torrent_info["raw_video_file"] = individual_file
                            logging.info(f"Using {individual_file} for bdinfo tests")
                            found = True
                            break
                    if found:
                        break

        if 'raw_video_file' not in torrent_info:
            logging.critical(f"The folder {torrent_info['upload_media']} does not contain any video files")
            console.print(f"The folder {torrent_info['upload_media']} does not contain any video files\n\n", style='bold red')
            return "skip_to_next_file"
            # sys.exit(f"The folder {torrent_info['upload_media']} does not contain any video files")

        torrent_info["raw_file_name"] = os.path.basename(os.path.dirname(f"{full_path}/"))  # this is used to isolate the folder name
    else:
        # For regular movies and single video files we can use the following the just get the filename
        torrent_info["raw_file_name"] = os.path.basename(full_path)  # this is used to isolate the file name

    
    #---------------------------------Full Disk BDInfo Parsing--------------------------------------#
    # if the upload is for a full disk, we parse the bdinfo to indentify more information before moving on to the existing logic.
    keys_we_need_but_missing_torrent_info_list = ['video_codec', 'audio_codec'] # for disc we don't need mediainfo
    if args.disc:
        bdinfo_start_time = time.perf_counter()
        logging.debug(f"\nGenerating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}")
        console.print(f"\nGenerating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}", style='bold blue')
        torrent_info["bdinfo"] = generate_and_parse_bdinfo() # TODO idle and handle non-happy paths
        logging.debug(f"Parsed BDInfo output :: {pformat(torrent_info['bdinfo'])}")
        bdinfo_end_time = time.perf_counter()
        logging.debug(f"Time taken for full bdinfo parsing :: {(bdinfo_end_time - bdinfo_start_time)}")
    else:
        # since this is not a disc, media info will be appended to the list
        keys_we_need_but_missing_torrent_info_list.append("mediainfo")

    # ------------ GuessIt doesn't return a video/audio codec that we should use ------------ #
    # For 'x264', 'AVC', and 'H.264' GuessIt will return 'H.264' which might be a little misleading since things like 'x264' is used for encodes while AVC for Remuxs (usually) etc
    # For audio it will insert "Dolby Digital Plus" into the dict when what we want is "DD+"
    # ------------ If we are missing any other "basic info" we try to identify it here ------------ #
    if len(keys_we_need_but_missing_torrent_info) != 0:
        logging.error("Unable to automatically extract all the required info from the FILENAME")
        logging.error(f"We are missing this info: {keys_we_need_but_missing_torrent_info}")
        # Show the user what is missing & the next steps
        console.print(f"[bold red underline]Unable to automatically detect the following info from the FILENAME:[/bold red underline] [green]{keys_we_need_but_missing_torrent_info}[/green]")    

    
    # We do some extra processing for the audio & video codecs since they are pretty important for the upload process & accuracy so they get appended each time
    for identify_me in keys_we_need_but_missing_torrent_info_list: # ['mediainfo', 'video_codec', 'audio_codec'] or ['video_codec', 'audio_codec'] for disks
        if identify_me not in keys_we_need_but_missing_torrent_info:
            keys_we_need_but_missing_torrent_info.append(identify_me)

    # parsing mediainfo, this will be reused for further processing.
    # only when the required data is mediainfo, this will be computed again, but as `text` format to write to file.
    parse_me = torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"]
    logging.debug(f"Mediainfo will parse the file: {parse_me}")
    
    meddiainfo_start_time = time.perf_counter()
    media_info_result = MediaInfo.parse(parse_me)
    meddiainfo_end_time = time.perf_counter()
    
    logging.debug(f"Time taken for mediainfo to parse the file {parse_me} :: {(meddiainfo_end_time - meddiainfo_start_time)}")

    #  Now we'll try to use regex, mediainfo, ffprobe etc to try and auto get that required info
    for missing_val in keys_we_need_but_missing_torrent_info:
        # Save the analyze_video_file() return result into the 'torrent_info' dict
        torrent_info[missing_val] = analyze_video_file(missing_value=missing_val, media_info=media_info_result)

    # Show the user what we identified so far
    columns_we_want = {
        'type': 'Type', 
        'title': 'Title',
        's00e00': f'{("Season" if len(torrent_info["s00e00"]) == 3 else "Episode") if "s00e00" in torrent_info else ""}',
        'year': f'{"Year" if "year" in torrent_info and torrent_info["type"] == "movie" else ""}',
        'source': 'Source', 
        'screen_size': 'Resolution', 
        'video_codec': 'Video codec',
        'hdr': 'HDR Format',
        'dv': 'Dolby Vision',
        'audio_codec': 'Audio codec', 
        'audio_channels': 'Channels',
        'atmos': 'Dolby Atmos',
        'release_group': f'{"Group" if "release_group" in torrent_info else None}'
    }
    presentable_type = 'Movie' if torrent_info["type"] == 'movie' else 'TV Show'

    codec_result_table = Table(box=box.SQUARE, title='Basic media summary', title_style='bold #be58bf')

    for column_display_value in columns_we_want.values():
        if len(column_display_value) != 0:
            codec_result_table.add_column(f"{column_display_value}", justify='center', style='#38ACEC')

    basic_info = []
    # add the actual data now
    for column_query_key, column_display_value in columns_we_want.items():
        if len(column_display_value) != 0:
            torrent_info_key_failsafe = (torrent_info[column_query_key] if column_query_key != 'type' else presentable_type) if column_query_key in torrent_info else None
            basic_info.append(torrent_info_key_failsafe)

    codec_result_table.add_row(basic_info[0], basic_info[1], basic_info[2], basic_info[3], basic_info[4], basic_info[5], basic_info[6], basic_info[7], basic_info[8])

    console.line(count=2)
    console.print(codec_result_table, justify='center')
    console.line(count=1)


def generate_and_parse_bdinfo():
    """
        Method generates the BDInfo for the full disk and writes to the mediainfo.txt file.
        Once it has been generated the generated BDInfo is parsed using the `parse_bdinfo` method 
        and result is saved in `torrent_info` as `bdinfo`
    """
    # if largest_playlist is already in torrent_info, then why this computation again???
    # Get the BDInfo, parse & save it all into a file called mediainfo.txt (filename doesn't really matter, it gets uploaded to the same place anyways)
    logging.debug(f"`largest_playlist` and `upload_media` from torrent_info :: {torrent_info['largest_playlist']} --- {torrent_info['upload_media']}")
    subprocess.run(["mono", "/usr/src/app/build/BDInfo.exe", torrent_info["upload_media"], "--mpls=" + torrent_info['largest_playlist']])

    shutil.move(f'{torrent_info["upload_media"]}BDINFO.{torrent_info["raw_file_name"]}.txt', f'{working_folder}/temp_upload/mediainfo.txt')
    if os.path.isfile("/usr/bin/sed"):
        sed_path = "/usr/bin/sed"
    else:
        sed_path = "/bin/sed"
    os.system(f"{sed_path} -i '0,/<---- END FORUMS PASTE ---->/d' {working_folder}/temp_upload/mediainfo.txt")
    # torrent_info["mediainfo"] = f'{working_folder}/temp_upload/mediainfo.txt'
    # displaying bdinfo to log in debug mode
    if args.debug:
        logging.debug("Dumping the BDInfo Quick Summary ::::::::::::::::::::::::::::")
        write_file_contents_to_log_as_debug(f'{working_folder}/temp_upload/mediainfo.txt')
    return parse_bdinfo(f'{working_folder}/temp_upload/mediainfo.txt')


def analyze_video_file(missing_value, media_info):
    """
        This method is being called in loop with mediainfo calculation all taking place multiple times.
        Optimize this code for better performance
    """
    logging.debug(f"Trying to identify the {missing_value}...")

    # ffprobe/mediainfo need to access to video file not folder, set that here using the 'parse_me' variable
    parse_me = torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"]

    # In pretty much all cases "media_info.tracks[1]" is going to be the video track and media_info.tracks[2] will be the primary audio track
    media_info_video_track = media_info.tracks[1]
    # I've encountered a media file without an audio track one time... this try/exception should handle any future situations like that
    try:
        media_info_audio_track = media_info.tracks[2]
    except IndexError:
        media_info_audio_track = None
    
    # ------------ Save mediainfo to txt ------------ #
    if missing_value == "mediainfo":
        logging.info("Generating mediainfo.txt")

        # If its not a bluray disc we can get mediainfo, otherwise we need BDInfo
        if "largest_playlist" not in torrent_info:
            # We'll remove the full file path for privacy reasons and only show the file (or folder + file) path in the "Complete name" of media_info_output
            if 'raw_video_file' in torrent_info:
                essential_path = f"{torrent_info['raw_file_name']}/{os.path.basename(torrent_info['raw_video_file'])}"
            else:
                essential_path = f"{os.path.basename(torrent_info['upload_media'])}"
            # depending on if the user is uploading a folder or file we need for format it correctly so we replace the entire path with just media file/folder name
            logging.info(f"Using the following path in mediainfo.txt: {essential_path}")

            media_info_output = str(MediaInfo.parse(parse_me, output="text", full=False)).replace(parse_me, essential_path)
            save_location = str(working_folder + '/temp_upload/mediainfo.txt')
            logging.info(f'Saving mediainfo to: {save_location}')
            logging.debug(":::::::::::::::::::::::::::: MediaInfo Output ::::::::::::::::::::::::::::")
            logging.debug(media_info_output)

            with open(save_location, 'w+') as f:
                f.write(media_info_output)
            # now save the mediainfo txt file location to the dict
            # torrent_info["mediainfo"] = save_location
            return save_location

    def quit_log_reason(reason):
        logging.critical(f"auto_mode is enabled (no user input) & we can not auto extract the {missing_value}")
        logging.critical(f"Exit Reason: {reason}")
        # let the user know the error/issue
        console.print(f"\nCritical error when trying to extract: {missing_value}", style='red bold')
        console.print(f"Exit Reason: {reason}")
        # and finally exit since this will affect all trackers we try and upload to, so it makes no sense to try the next tracker
        sys.exit()

    # !!! [ Block tests/probes start now ] !!!

    # ------------------- Source ------------------- #
    if missing_value == "source":
        # Well shit, this is a problem and I can't think of a good way to consistently & automatically get the right result
        # if auto_mode is set to false we can ask the user but if auto_mode is set to true then we'll just need to quit since we can't upload without it
        if auto_mode == 'false':
            console.print(f"Can't auto extract the [bold]{missing_value}[/bold] from the filename, you'll need to manually specify it", style='red', highlight=False)

            basic_source_to_source_type_dict = {
                # this dict is used to associate a 'parent' source with one if its possible final forms
                'bluray': ['disc', 'remux', 'encode'],
                'web': ['rip', 'dl'],
                'hdtv': 'hdtv',
                'dvd': ['disc', 'remux', 'rip']
            }

            # First get a basic source into the torrent_info dict, we'll prompt the user for a more specific source next (if needed, e.g. 'bluray' could mean 'remux', 'disc', or 'encode')
            user_input_source = Prompt.ask("Input one of the following: ", choices=["bluray", "web", "hdtv", "dvd"])
            torrent_info["source"] = user_input_source
            # Since the parent source isn't the filename we know that the 'final form' definitely won't be so we don't return the 'parent source' yet
            # We instead prompt the user again to figure out if its a remux, encode, webdl, rip, etc etc
            # Once we figure all that out we can return the 'parent source'

            # Now that we have the basic source we can prompt for a more specific source
            if isinstance(basic_source_to_source_type_dict[torrent_info["source"]], list):
                specific_source_type = Prompt.ask(f"\nNow select one of the following 'formats' for [green]'{user_input_source}'[/green]: ",
                    choices=basic_source_to_source_type_dict[torrent_info["source"]])
                # The user is given a list of options that are specific to the parent source they choose earlier (e.g.  bluray --> disc, remux, encode )
                torrent_info["source_type"] = f'{user_input_source}_{specific_source_type}'
            else:
                # Right now only HDTV doesn't have any 'specific' variation so this will only run if HDTV is the source
                torrent_info["source_type"] = f'{user_input_source}'

            # Now that we've got all the source related info, we can return the 'parent source' and move on
            return user_input_source

        else: # shit
            quit_log_reason(reason="auto_mode is enabled & we can't auto detect the source (e.g. bluray, webdl, dvd, etc). Upload form requires the Source")

    # ---------------- Video Resolution ---------------- #
    if missing_value == "screen_size":
        width_to_height_dict = {"720": "576", "960": "540", "1280": "720", "1920": "1080", "4096": "2160", "3840": "2160"}

        if args.disc and torrent_info["bdinfo"] is not None:
            logging.info(f"`screen_size` identifed from bdinfo as {torrent_info['bdinfo']['video'][0]['resolution']}")
            return torrent_info["bdinfo"]["video"][0]["resolution"]

        # First we use attempt to use "width" since its almost always constant (Groups like to crop black bars so "height" is always changing)
        elif str(media_info_video_track.width) != "None":
            track_width = str(media_info_video_track.width)
            if track_width in width_to_height_dict:
                height = width_to_height_dict[track_width]
                logging.info(f"Used pymediainfo 'track.width' to identify a resolution of: {str(height)}p")
                return f"{str(height)}p"

        # If "Width" somehow fails its unlikely that "Height" will work but might as well try
        elif str(media_info_video_track.height) != "None":
            logging.info(f"Used pymediainfo 'track.height' to identify a resolution of: {str(media_info_video_track.height)}p")
            return f"{str(media_info_video_track.height)}p"

        # User input as a last resort
        else:
            # If auto_mode is enabled we can prompt the user for input
            if auto_mode == 'false':
                screen_size_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g. 720p, 1080p, 2160p) ')
                return str(screen_size_input)

            # If we don't have the resolution we can't upload this media since all trackers require the resolution in the upload form
            quit_log_reason(reason="Resolution not in filename, and we can't extract it using pymediainfo. Upload form requires the Resolution")

    # ---------------- Audio Channels ---------------- #
    if missing_value == "audio_channels":

        if args.disc and torrent_info["bdinfo"] is not None:
            logging.info(f"`audio_channels` identifed from bdinfo as {torrent_info['bdinfo']['audio'][0]['channels']}")
            return torrent_info["bdinfo"]["audio"][0]["channels"]

        # First try detecting the 'audio_channels' using regex
        elif "raw_file_name" in torrent_info:
            # First split the filename by '-' & '.'
            file_name_split = re.sub(r'[-.]', ' ', str(torrent_info["raw_file_name"]))
            # Now search for the audio channels
            re_extract_channels = re.search(r'\s[0-9]\s[0-9]\s', file_name_split)
            if re_extract_channels is not None:
                # Because this isn't something I've tested extensively I'll only consider it a valid match if its a super common channel layout (e.g.  7.1  |  5.1  |  2.0  etc)
                re_extract_channels = re_extract_channels.group().split()
                mid_pos = len(re_extract_channels) // 2
                # joining and construction using single line
                possible_audio_channels = str(' '.join(re_extract_channels[:mid_pos] + ["."] + re_extract_channels[mid_pos:]).replace(" ", ""))
                # Now check if the regex match is in a list of common channel layouts
                if possible_audio_channels in ['1.0', '2.0', '5.1', '7.1']:
                    # It is! So return the regex match and skip over the ffprobe process below
                    logging.info(f"Used regex to identify audio channels: {possible_audio_channels}")
                    return possible_audio_channels

        # If the regex failed ^^ (Likely) then we use ffprobe to try and auto detect the channels
        audio_info_probe = FFprobe(inputs={parse_me: None}, 
            global_options=['-v', 'quiet', '-print_format', 'json', '-select_streams a:0', '-show_format', '-show_streams']).run(stdout=subprocess.PIPE)

        audio_info = json.loads(audio_info_probe[0].decode('utf-8'))
        for stream in audio_info["streams"]:

            if "channel_layout" in stream:  # make sure 'channel_layout' exists first (on some amzn webdls it doesn't)
                # convert the words 'mono, stereo, quad' to work with regex below
                ffmpy_channel_layout_translation = {'mono': '1.0', 'stereo': '2.0', 'quad': '4.0'}
                if str(stream["channel_layout"]) in ffmpy_channel_layout_translation.keys():
                    stream["channel_layout"] = ffmpy_channel_layout_translation[stream["channel_layout"]]

                # Make sure what we got back from the ffprobe search fits into the audio_channels 'format' (num.num)
                audio_channel_layout = re.search(r'\d\.\d', str(stream["channel_layout"]).replace("(side)", ""))
                if audio_channel_layout is not None:
                    audio_channels_ff = str(audio_channel_layout.group())
                    logging.info(f"Used ffmpy.ffprobe to identify audio channels: {audio_channels_ff}")
                    return audio_channels_ff

        # Another thing we can try is pymediainfo and count the 'Channel layout' then subtract 1 depending on if 'LFE' is one of them
        if media_info_audio_track.channel_layout is not None:
            channel_total = str(media_info_audio_track.channel_layout).split(" ")
            if 'LFE' in channel_total:
                audio_channels_pymedia = f'{int(len(channel_total)) - 1}.1'
            else:
                audio_channels_pymedia = f'{int(len(channel_total))}.0'

            logging.info(f"Used pymediainfo to identify audio channels: {audio_channels_pymedia}")
            return audio_channels_pymedia

        # If no audio_channels have been extracted yet then we try user_input next
        if auto_mode == 'false':
            audio_channel_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g.  5.1 | 2.0 | 7.1  )')
            logging.info(f"Used user_input to identify audio channels: {audio_channel_input}")
            return str(audio_channel_input)

        # -- ! This runs if auto_mode == true !
        # We could technically upload without the audio channels in the filename, check to see what the user wants
        if str(os.getenv('force_auto_upload')).lower() == 'true':  # This means we will still force an upload without the audio_channels
            logging.info("force_auto_upload=true so we'll upload without the audio_channels in the filename")
            return ""

        # Well shit, if nothing above returned any value then it looks like this is the end of our journey :(
        # Exit the script now
        quit_log_reason(reason="Audio_Channels are not in the filename, and we can't extract it using regex or ffprobe. force_auto_upload=false so we quit now")
    
    # ---------------- Audio Codec ---------------- #
    if missing_value == "audio_codec":

        # We store some common audio code translations in this dict
        audio_codec_dict = {"AC3": "DD", "AC3+": "DD+", "Dolby Digital Plus": "DD+", "Dolby Digital": "DD",
                            "AAC": "AAC", "AC-3": "DD", "FLAC": "FLAC", "DTS": "DTS", "Opus": "Opus", "OPUS": "Opus", "E-AC-3": "DD+", "A_EAC3": "DD+", "A_AC3": "DD"}

        if args.disc and torrent_info["bdinfo"] is not None:
            logging.info(f"`audio_channels` identifed from bdinfo as {torrent_info['bdinfo']['audio'][0]['codec']}")
            return torrent_info["bdinfo"]["audio"][0]["codec"]

        # First check to see if GuessIt inserted an audio_codec into torrent_info and if it did then we can verify its formatted correctly
        elif "audio_codec" in torrent_info:
            logging.debug(f"audio_codec is present in the torrent info [{torrent_info['audio_codec']}]. Trying to match it with audio_codec_dict")
            for key in audio_codec_dict.keys():
                if str(torrent_info["audio_codec"]) == key:
                    logging.info(f'Used (audio_codec_dict + GuessIt) to identify the audio codec: {audio_codec_dict[torrent_info["audio_codec"]]}')
                    return audio_codec_dict[torrent_info["audio_codec"]]

        # This regex is mainly for bluray_discs
        # TODO rewrite this to be more inclusive of other audio codecs
        bluray_disc_audio_codec_regex = re.search(r'(?P<TrueHD>TrueHD)|(?P<DTSHDMA>DTS-HD.MA)', torrent_info["raw_file_name"].replace(".", " "), re.IGNORECASE)
        if bluray_disc_audio_codec_regex is not None:
            for audio_codec in ["TrueHD", "DTSHDMA"]:
                # Yeah I've kinda given up here, this is mainly to avoid mediainfo running on full bluray discs since TrueHD is really just AC3 which historically I assumed was Dolby Digital...
                #  Don't really wanna deal with that ^^ so we try to match the 2 most popular Bluray Disc audio codecs (DTS-HD.MA & TrueHD) and move on
                if bluray_disc_audio_codec_regex.group(audio_codec) is not None:
                    if audio_codec == "DTSHDMA": 
                        audio_codec = "DTS-HD MA"
                    logging.info(f'Used regex to identify the audio codec: {audio_codec}')
                    return audio_codec

        # Now we try to identify the audio_codec using pymediainfo
        if media_info_audio_track is not None:
            if media_info_audio_track.codec_id is not None:
                # The release "La.La.Land.2016.1080p.UHD.BluRay.DDP7.1.HDR.x265-NCmt.mkv" when using media_info_audio_track.codec shows the codec as AC3 not EAC3..
                # so well try to use media_info_audio_track.codec_id first
                audio_codec = media_info_audio_track.codec_id
            elif media_info_audio_track.codec is not None:
                # On rare occasion *.codec is not available and we need to use *.format
                audio_codec = media_info_audio_track.codec
            elif media_info_audio_track.format is not None:
                # Only use *.format if *.codec is unavailable
                audio_codec = media_info_audio_track.format
            # Set audio_codec equal to None if neither of those three ^^ exist and we'll move onto user input
            else:
                audio_codec = None
        else:
            audio_codec = None

        # If we got something from pymediainfo we can try to analyze it now
        if audio_codec:
            if "AAC" in audio_codec:
                # AAC gets its own 'if' statement because 'audio_codec' can return something like 'AAC LC-SBR' or 'AAC-HE/LC'
                # Its unnecessary for a torrent title and we only need the "AAC" part
                logging.info(f'Used pymediainfo to identify the audio codec: {audio_codec}')
                return "AAC"
            
            if "FLAC" in audio_codec:
                # This is similar to the AAC situation right above ^^, on a recent upload I got the value "A_FLAC" which can be shortened to 'FLAC'
                logging.info(f'Used pymediainfo to identify the audio codec: FLAC')
                return "FLAC"

            if "DTS" in audio_codec:
                # DTS audio is a bit "special" and has a few possible profiles so we deal with that here
                # We'll first try to extract it all via regex, should that fail we can use ffprobe
                match_dts_audio = re.search(r'DTS(-HD(.MA\.)|-ES\.|(.x\.|x\.)|(.HD\.|HD\.)|)', torrent_info["raw_file_name"].replace(" ", "."), re.IGNORECASE)
                if match_dts_audio is not None:
                    logging.info(f'Used (pymediainfo + regex) to identify the audio codec: {str(match_dts_audio.group()).upper().replace(".", " ")}')
                    return str(match_dts_audio.group()).upper().replace(".", " ").strip()

                # If the regex failed we can try ffprobe
                audio_info_probe = FFprobe( inputs={parse_me: None}, 
                    global_options=['-v', 'quiet', '-print_format', 'json', '-select_streams a:0', '-show_format', '-show_streams']).run(stdout=subprocess.PIPE)
                audio_info = json.loads(audio_info_probe[0].decode('utf-8'))

                for stream in audio_info["streams"]:
                    logging.info(f'Used ffprobe to identify the audio codec: {stream["profile"]}')
                    return stream["profile"]

            if audio_codec in audio_codec_dict.keys():
                # Now its a bit of a Hail Mary and we try to match whatever pymediainfo returned to our audio_codec_dict/translation
                logging.info(f'Used (pymediainfo + audio_codec_dict) to identify the audio codec: {audio_codec_dict[audio_codec]}')
                return audio_codec_dict[audio_codec]

        # If the audio_codec has not been extracted yet then we try user_input
        if auto_mode == 'false':
            audio_codec_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g.  DTS | DDP | FLAC | TrueHD | Opus  )')
            logging.info(f"Used user_input to identify the audio codec: {audio_codec_input}")
            return str(audio_codec_input)

        # -- ! This runs if auto_mode == true !
        # We could technically upload without the audio codec in the filename, check to see what the user wants
        if str(os.getenv('force_auto_upload')).lower() == 'true':  # This means we will still force an upload without the audio_codec
            logging.info("force_auto_upload=true so we'll upload without the audio_codec in the torrent title")
            return ""

        # Well shit, if nothing above returned any value then it looks like this is the end of our journey :(
        # Exit the script now
        quit_log_reason(reason="Could not detect audio_codec via regex, pymediainfo, & ffprobe. force_auto_upload=false so we quit now")

    # ---------------- Video Codec ---------------- #
    # I'm pretty confident that a video_codec will be selected automatically each time, unless mediainfo fails catastrophically we should always
    # have a codec we can return. User input isn't needed here

    if missing_value == "video_codec":
        """
            along with video_codec extraction the HDR format is also updated from here.
            Steps:
            get Color primaries from MediaInfo
            if it is one of "BT.2020", "REC.2020" then
                try to get HDR format from MediaInfo
                    if HDR10 is present in HDR Format then HDR = HDR
                    if HDR10+ is present in HDR Format then HDR = HDR10+
                on any errors
                    confirm the HDRFormat doesn't exist in the media info 
                    check whether its PQ is present in Transfer characteristics or transfer_characteristics_Original from MediaInfo 
                        HDR = PQ10 
                get transfer_characteristics_Original from media info
                if HLG is present in that then HDR = HLG
                else if "BT.2020 (10-bit)" is present then HDR = WCG
        """
        try:
            color_primaries = media_info_video_track.color_primaries
            if color_primaries is not None and color_primaries in ("BT.2020", "REC.2020"):
                try:
                    hdr_format = f"{media_info_video_track.hdr_format}, {media_info_video_track.hdr_format_version}, {media_info_video_track.hdr_format_compatibility}"
                    if "HDR10" in hdr_format:
                        torrent_info["hdr"] = "HDR"
                    if "HDR10+" in hdr_format:
                        torrent_info["hdr"] = "HDR10+"
                except:
                    if media_info_video_track.hdr_format is None and "PQ" in (media_info_video_track.transfer_characteristics, media_info_video_track.transfer_characteristics_Original, None):
                        torrent_info["hdr"] = "PQ10"
                transfer_characteristics = media_info_video_track.transfer_characteristics_Original
                if "HLG" in transfer_characteristics:
                    torrent_info["hdr"] = "HLG"
                elif "BT.2020 (10-bit)" in transfer_characteristics:
                    torrent_info["hdr"] = "WCG"
        except:
            logging.error(f"Error occured while trying to parse HDR information from mediainfo")
        
        # TODO dolby vision and HDR is not handled
        if args.disc and torrent_info["bdinfo"] is not None: 
            logging.info(f"`audio_channels` identifed from bdinfo as {torrent_info['bdinfo']['video'][0]['codec']}")
            return torrent_info["bdinfo"]["video"][0]["codec"]
        
        # First try to use our own Regex to extract it, if that fails then we can ues ffprobe/mediainfo
        filename_video_codec_regex = re.search(r'(?P<HEVC>HEVC)|(?P<AVC>AVC)|'
                                               r'(?P<H265>H(.265|265))|'
                                               r'(?P<H264>H(.264|264))|'
                                               r'(?P<x265>x265)|(?P<x264>x264)|'
                                               r'(?P<MPEG2>MPEG(-2|2))|'
                                               r'(?P<VC1>VC(-1|1))', torrent_info["raw_file_name"], re.IGNORECASE)
        regex_video_codec = None
        if filename_video_codec_regex is not None:
            rename_codec = {'VC1': 'VC-1', 'MPEG2': 'MPEG-2', 'H264': 'H.264', 'H265': 'H.265'}

            for video_codec in ["HEVC", "AVC", "H265", "H264", "x265", "x264", "MPEG2", "VC1"]:
                if filename_video_codec_regex.group(video_codec) is not None:
                    # Now check to see if the 'codec' is in the rename_codec dict we created earlier
                    if video_codec in rename_codec.keys():
                        regex_video_codec = rename_codec[video_codec]
                    else:
                        # if this executes its AVC/HEVC or x265/x264
                        regex_video_codec = video_codec
                    # return regex_video_codec
        # If the regex didn't work and the code has reached this point, we will now try pymediainfo

        # If video codec is HEVC then depending on the specific source (web, bluray, etc) we might need to format that differently
        if "HEVC" in media_info_video_track.format:
            if media_info_video_track.writing_library is not None:
                pymediainfo_video_codec = 'x265'
            # Possible video_codecs now are either H.265 or HEVC
            # If the source is WEB I think we should use H.265 & leave HEVC for bluray discs/remuxs (encodes would fall under x265)
            elif "source" in torrent_info and torrent_info["source"] == "Web":
                pymediainfo_video_codec = 'H.265'
            # for everything else we can just default to 'HEVC' since it'll technically be accurate no matter what
            else:
                logging.info(f"Defaulting video_codec as HEVC because writing library is missing and source is {torrent_info['source']}")
                pymediainfo_video_codec = 'HEVC'

        # Now check and assign AVC based codecs
        elif "AVC" in media_info_video_track.format:
            if media_info_video_track.writing_library is not None:
                pymediainfo_video_codec = 'x264'
            # Possible video_codecs now are either H.264 or AVC
            # If the source is WEB we should use H.264 & leave AVC for bluray discs/remuxs (encodes would fall under x265)
            elif "source" in torrent_info and torrent_info["source"] == "Web":
                pymediainfo_video_codec = 'H.264'
            # for everything else we can just default to 'AVC' since it'll technically be accurate no matter what
            else:
                logging.info(f"Defaulting video_codec as AVC because writing library is missing and source is {torrent_info['source']}")
                pymediainfo_video_codec = 'AVC'
        # For anything else we'll just use whatever pymediainfo returned for 'format'
        else:
            pymediainfo_video_codec = media_info_video_track.format

        # Log it!
        logging.info(f"Regex identified the video_codec as: {regex_video_codec}")
        logging.info(f"Pymediainfo identified the video_codec as: {pymediainfo_video_codec}")
        if regex_video_codec == pymediainfo_video_codec:
            logging.debug(f"Regex extracted video_codec [{regex_video_codec}] and pymediainfo extracted video_codec [{pymediainfo_video_codec}] matches")
            return regex_video_codec

        logging.error(f"Regex extracted video_codec [{regex_video_codec}] and pymediainfo extracted video_codec [{pymediainfo_video_codec}] doesn't match!!")
        logging.info(f"If `--force_pymediainfo` or `-fpm` is provided as argument, PyMediaInfo video_codec will be used, else regex extracted video_codec will be used")
        if args.force_pymediainfo:
            return pymediainfo_video_codec

        return regex_video_codec
    # TODO write more block/tests here as we come across issues

    # !!! [ Block tests/probes end here ] !!!


def identify_miscellaneous_details(guess_it_result):
    """
        This function is dedicated to analyzing the filename and extracting snippets such as "repack, "DV", "AMZN", etc
        Depending on what the "source" is we might need to search for a "web source" (amzn, nf, hulu, etc)
        
        We also search for "editions" here, this info is typically made known in the filename so we can use some simple regex to extract it 
        (e.g. extended, Criterion, directors, etc)
    """
    # ------ Specific Source info ------ #
    if "source_type" not in torrent_info:
        match_source = re.search(r'(?P<bluray_remux>.*blu(.ray|ray).*remux.*)|'
                                 r'(?P<bluray_disc>.*blu(.ray|ray)((?!x(264|265)|h.(265|264)).)*$)|'
                                 r'(?P<webrip>.*web(.rip|rip).*)|'
                                 r'(?P<webdl>.*web(.dl|dl|).*)|'
                                 r'(?P<bluray_encode>.*blu(.ray|ray).*|x(264|265)|h.(265|264))|'
                                 r'(?P<dvd>HD(.DVD|DVD)|.*DVD.*)|'
                                 r'(?P<hdtv>.*HDTV.*)', torrent_info["raw_file_name"], re.IGNORECASE)
        if match_source is not None:
            for source_type in ["bluray_disc", "bluray_remux", "bluray_encode", "webdl", "webrip", "dvd", "hdtv"]:
                if match_source.group(source_type) is not None:
                    # add it directly to the torrent_info dict
                    torrent_info["source_type"] = source_type

        # Well firstly if we got this far with auto_mode enabled that means we've somehow figured out the 'parent' source but now can't figure out its 'final form'
        # If auto_mode is disabled we can prompt the user
        elif auto_mode == 'false':
            # Yeah yeah this is just copy/pasted from the original user_input source code, it works though ;)
            basic_source_to_source_type_dict = {
                # this dict is used to associate a 'parent' source with one if its possible final forms
                'bluray': ['disc', 'remux', 'encode'],
                'web': ['rip', 'dl'],
                'hdtv': 'hdtv',
                'dvd': ['disc', 'remux', 'rip']
            }
            # Since we already know the 'parent source' from an earlier function we don't need to prompt the user for it twice
            if isinstance(basic_source_to_source_type_dict[str(torrent_info["source"]).lower()], list):
                console.print("\nError: Unable to detect this medias 'format'", style='red')
                console.print(f"\nWe've successfully detected the 'parent source': [bold]{torrent_info['source']}[/bold] but are unable to detect its 'final form'", highlight=False)
                logging.error(f"We've successfully detected the 'parent source': [bold]{torrent_info['source']}[/bold] but are unable to detect its 'final form'")

                # Now prompt the user
                specific_source_type = Prompt.ask(f"\nNow select one of the following 'formats' for [green]'{torrent_info['source']}'[/green]: ", 
                        choices=basic_source_to_source_type_dict[torrent_info["source"]])
                # The user is given a list of options that are specific to the parent source they choose earlier (e.g.  bluray --> disc, remux, encode )
                torrent_info["source_type"] = f'{torrent_info["source"]}_{specific_source_type}'
            else:
                # Right now only HDTV doesn't have any 'specific' variation so this will only run if HDTV is the source
                torrent_info["source_type"] = f'{torrent_info["source"]}'


        # Well this sucks, we got pretty far this time but since 'auto_mode=true' we can't prompt the user & it probably isn't a great idea to start making assumptions about a media files source,
        # that seems like a good way to get a warning/ban so instead we'll just quit here and let the user know why
        else:
            logging.critical("auto_mode is enabled (no user input) & we can not auto extract the 'source_type'")
            # let the user know the error/issue
            console.print("\nCritical error when trying to extract: 'source_type' (more specific version of 'source', think bluray_remux & just bluray) ", style='red bold')
            console.print("Quitting now..")
            # and finally exit since this will affect all trackers we try and upload to, so it makes no sense to try the next tracker
            sys.exit()

    # ------ WEB streaming service stuff here ------ #
    if torrent_info["source"] == "Web":
        """
            First priority is given to guessit
            If guessit can get the `streaming_service`, then we'll use that
            Otherwise regex is used to detect the streaming service
        """
        # reading stream sources param json.
        # You can add more streaming platforms to the json file.
        # The value of the json keys will be used to create the torrent file name. 
        # the keys are used to match the output from guessit
        streaming_sources = json.load(open(f'{working_folder}/parameters/streaming_services.json'))

        web_source = guess_it_result.get('streaming_service', '')
        guessit_output = streaming_sources.get(web_source)
        if guessit_output is not None:
            torrent_info["web_source"] = guessit_output
            logging.info(f'Used guessit to extract the WEB Source: {guessit_output}')
        else:
            source_regex = "[\.|\ ](" + "|".join(streaming_sources.values()) + ")[\.|\ ]"
            match_web_source = re.search(source_regex, torrent_info["raw_file_name"].upper())
            if match_web_source is not None:
                torrent_info["web_source"] = match_web_source.group()
                logging.info(f'Used Regex to extract the WEB Source: {match_web_source.group()}')
            else:
                logging.error("Not able to extract the web source information from REGEX and GUESSIT")

    # --- Custom & extra info --- #
    # some torrents have 'extra' info in the title like 'repack', 'DV', 'UHD', 'Atmos', 'remux', etc
    # We simply use regex for this and will add any matches to the dict 'torrent_info', later when building the final title we add any matches (if they exist) into the title

    # repacks
    match_repack = re.search(r'RERIP|REPACK|PROPER|REPACK2|REPACK3', torrent_info["raw_file_name"], re.IGNORECASE)
    if match_repack is not None:
        torrent_info["repack"] = match_repack.group()
        logging.info(f'Used Regex to extract: [bold]{match_repack.group()}[/bold] from the filename')

    # --- Bluray disc type --- #
    if torrent_info["source_type"] == "bluray_disc":
        # This is just based on resolution & size so we just match that info up to the key we create below
        possible_types = [25, 50, 66, 100]
        bluray_prefix = 'uhd' if torrent_info["screen_size"] == "2160p" else 'bd'
        total_size = sum(f.stat().st_size for f in Path(torrent_info["upload_media"]).glob('**/*') if f.is_file())

        for possible_type in possible_types:
            if total_size < int(possible_type * 1000000000):
                torrent_info["bluray_disc_type"] = str(f'{bluray_prefix}_{possible_type}')
                break

    # Bluray disc regions
    # Regions are read from new json file
    bluray_regions = json.load(open(f'{working_folder}/parameters/bluray_regions.json'))

    # Try to split the torrent title and match a few key words
    # End user can add their own 'key_words' that they might want to extract and add to the final torrent title
    key_words = {'remux': 'REMUX', 'hdr': torrent_info.get("hdr", "HDR"),  'uhd': 'UHD', 'hybrid': 'Hybrid', 'atmos': 'Atmos'}
    
    hdr_hybrid_remux_keyword_search = str(torrent_info["raw_file_name"]).replace(" ", ".").replace("-", ".").split(".")

    for word in hdr_hybrid_remux_keyword_search:
        if str(word).lower() in key_words.keys():
            logging.info(f"extracted the key_word: {word.lower()} from the filename")
            torrent_info[str(word).lower()] = key_words[str(word).lower()]

        # Bluray region source
        if "disc" in torrent_info["source_type"]:
            # This is either a bluray or dvd disc, these usually have the source region in the filename, try to extract it now
            if str(word).upper() in bluray_regions.keys():
                torrent_info["region"] = str(word).upper()

        # Dolby vision (filename detection)
        # HDR is also added from here. The type of hdr is updated from media info
        if any(x in str(word).lower() for x in ['dv', 'dovi', 'do-vi']):
            logging.info("Detected Dolby Vision from the filename")
            torrent_info["dv"] = "DV"

    # use regex (sourced and slightly modified from official radarr repo) to find torrent editions (Extended, Criterion, Theatrical, etc)
    # https://github.com/Radarr/Radarr/blob/5799b3dc4724dcc6f5f016e8ce4f57cc1939682b/src/NzbDrone.Core/Parser/Parser.cs#L21
    try:
        torrent_editions = re.search(
            r"((Recut.|Extended.|Ultimate.|Criterion.|International.)?(Director.?s|Collector.?s|Theatrical|Ultimate|Final|Criterion|International(?=(.(Cut|Edition|Version|Collection)))|Extended|Rogue|Special|Despecialized|\d{2,3}(th)?.Anniversary)(.(Cut|Edition|Version|Collection))?(.(Extended|Uncensored|Remastered|Unrated|Uncut|IMAX|Fan.?Edit))?|(Uncensored|Remastered|Unrated|Uncut|IMAX|Fan.?Edit|Edition|Restored|(234)in1))",
            torrent_info["upload_media"])
        torrent_info["edition"] = str(torrent_editions.group()).replace(".", " ")
        logging.info(f"extracted '{torrent_info['edition']}' as the 'edition' for the final torrent name")
    except AttributeError:
        logging.error("No custom 'edition' found for this torrent")

    # --------- Fix scene group tags --------- #
    # Scene releases after they unrared are all lowercase (usually) so we fix the torrent title here (Never rename the actual file)
    # new groups can be added in the `scene_groups.json`
    scene_group_capitalization = json.load(open(f'{working_folder}/parameters/scene_groups.json'))

    # Whilst most scene group names are just capitalized but occasionally as you can see ^^ some are not (e.g. KOGi)
    # either way we don't want to be capitalizing everything (e.g. we want 'NTb' not 'NTB') so we still need a dict of scene groups and their proper capitalization
    if "release_group" in torrent_info:
        # compare the release group we extracted to the groups in the dict above ^^
        if str(torrent_info["release_group"]).lower() in scene_group_capitalization.keys():
            # replace the "release_group" in torrent_info with the dict value we have
            torrent_info["release_group"] = scene_group_capitalization[str(torrent_info["release_group"]).lower()]
            # Also save the fact that this is a scene group for later (we can add a 'scene' tag later to BHD)
            torrent_info["scene"] = 'true'

    # --------- SD? --------- #
    res = re.sub("[^0-9]", "", torrent_info["screen_size"])
    if int(res) <= 720:
        torrent_info["sd"] = 1


def search_tmdb_for_id(query_title, year, content_type):
    console.line(count=2)
    console.rule(f"TMDB Search Results", style='red', align='center')
    console.line(count=1)

    if content_type == "episode":  # translation for TMDB API
        content_type = "tv"

    result_num = 0
    result_dict = {}

    if len(year) != 0:
        query_year = "&year=" + str(year)
    else:
        query_year = ""

    search_tmdb_request_url = f"https://api.themoviedb.org/3/search/{content_type}?api_key={os.getenv('TMDB_API_KEY')}&query={query_title}&page=1&include_adult=false{query_year}"

    search_tmdb_request = requests.get(search_tmdb_request_url)
    logging.info(f"GET Request: {search_tmdb_request_url}")
    if search_tmdb_request.ok:
        # print(json.dumps(search_tmdb_request.json(), indent=4, sort_keys=True))
        if len(search_tmdb_request.json()["results"]) == 0:
            logging.critical("No results found on TMDB using the title '{}' and the year '{}'".format(query_title, year))
            sys.exit("No results found on TMDB, try running this script again but manually supply the tmdb or imdb ID")

        tmdb_search_results = Table(show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim")
        tmdb_search_results.add_column("Result #", justify="center")
        tmdb_search_results.add_column("Title", justify="center")
        tmdb_search_results.add_column("TMDB URL", justify="center")
        tmdb_search_results.add_column("Release Date", justify="center")
        tmdb_search_results.add_column("Language", justify="center")
        tmdb_search_results.add_column("Overview", justify="center")

        for possible_match in search_tmdb_request.json()["results"]:

            result_num += 1  # This counter is used so that when we prompt a user to select a match, we know which one they are referring to
            result_dict[str(result_num)] = possible_match["id"]  # here we just associate the number count ^^ with each results TMDB ID

            # ---- Parse the output and process it ---- #
            # Get the movie/tv 'title' from json response
            # TMDB will return either "title" or "name" depending on if the content your searching for is a TV show or movie
            title_match = list(map(possible_match.get, filter(lambda x: x in "title, name", possible_match)))
            if len(title_match) > 0:
                title_match_result = title_match.pop()
            else:
                logging.error(f"Title not found on TMDB for TMDB ID: {str(possible_match['id'])}")
                title_match_result = "N.A."

            # Same situation as with the movie/tv title. The key changes depending on what the content type is
            year_match = list(map(possible_match.get, filter(lambda x: x in "release_date, first_air_date", possible_match)))
            if len(year_match) > 0:
                year = year_match.pop()
            else:
                logging.error(f"Year not found on TMDB for TMDB ID: {str(possible_match['id'])}")
                year = "N.A."

            if "overview" in possible_match:
                if len(possible_match["overview"]) > 1:
                    overview = possible_match["overview"]
                else:
                    logging.error(f"Overview not found on TMDB for TMDB ID: {str(possible_match['id'])}")
                    overview = "N.A."
            else:
                overview = "N.A."
            # ---- (DONE) Parse the output and process it (DONE) ---- #

            # Now add that json data to a row in the table we show the user
            tmdb_search_results.add_row(
                f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]", title_match_result,
                f"themoviedb.org/{content_type}/{str(possible_match['id'])}", str(year), possible_match["original_language"], overview, end_section=True )

        logging.info(f"total number of results for TMDB search: {str(result_num)}")
        # once the loop is done we can show the table to the user
        console.print(tmdb_search_results)

        list_of_num = []  # here we convert our integer that was storing the total num of results into a list
        for i in range(result_num):
            i += 1
            # The idea is that we can then show the user all valid options they can select
            list_of_num.append(str(i))

        if auto_mode == 'false':
            # prompt for user input with 'list_of_num' working as a list of valid choices
            user_input_tmdb_id_num = Prompt.ask("Input the correct Result #", choices=list_of_num, default="1")
        else:
            console.print("auto selected #1...")
            user_input_tmdb_id_num = "1"
            logging.info(f"auto_mode is enabled so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")

        # We take the users (valid) input (or auto selected number) and use it to retrieve the appropriate TMDB ID
        torrent_info["tmdb"] = str(result_dict[user_input_tmdb_id_num])
        # Now we can call the function 'get_external_id()' to try and identify the IMDB ID (insert it into torrent_info dict right away)
        torrent_info["imdb"] = str(get_external_id(id_site='tmdb', id_value=torrent_info["tmdb"], content_type=torrent_info["type"]))


def get_external_id(id_site, id_value, content_type):
    # This is pretty self explanatory, We only call this function when we only have 1 ID (TMDB or IMDB doesn't matter)
    # If we only have 1 ID then we can use TMDB API to get the other sites ID, we do that below
    if content_type == "episode":  # translation for TMDB API
        content_type = "tv"

    get_imdb_id_url = f"https://api.themoviedb.org/3/{content_type}/{id_value}/external_ids?api_key={os.getenv('TMDB_API_KEY')}&language=en-US"
    get_tmdb_id_url = f"https://api.themoviedb.org/3/find/{id_value}?api_key={os.getenv('TMDB_API_KEY')}&language=en-US&external_source=imdb_id"

    if id_site == 'tmdb':
        imdb_id_request = requests.get(get_imdb_id_url).json()
        logging.info(f"GET Request: {get_imdb_id_url}")
        if imdb_id_request["imdb_id"] is None:
            return ""
        return imdb_id_request["imdb_id"]

    if id_site == 'imdb':
        tmdb_id_request = requests.get(get_tmdb_id_url).json()
        logging.info(f"GET Request: {get_tmdb_id_url}")
        for item in tmdb_id_request:
            if len(tmdb_id_request[item]) == 1:
                return str(tmdb_id_request[item][0]["id"])


def search_for_mal_id(content_type, tmdb_id):
    # if 'content_type == tv' then we need to get the TVDB ID since we're going to need it to try and get the MAL ID
    if content_type == 'tv':
        get_tvdb_id = f" https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={os.getenv('TMDB_API_KEY')}&language=en-US"
        get_tvdb_id_response = requests.get(get_tvdb_id).json()
        # Look for the tvdb_id key
        if 'tvdb_id' in get_tvdb_id_response and get_tvdb_id_response['tvdb_id'] is not None:
            torrent_info["tvdb"] = str(get_tvdb_id_response['tvdb_id'])

    # We use this small dict to auto fill the right values into the url request below
    content_type_to_value_dict = {'movie': 'tmdb', 'tv': 'tvdb'}

    # Now we we get the MAL ID

    # Before you get too concerned, this address is a flask app I quickly set up to convert TMDB/IMDB IDs to mal using this project/collection https://github.com/Fribb/anime-lists
    # You can test it out yourself with the url: http://195.201.146.92:5000/api/?tmdb=10515 to see what it returns (it literally just returns the number "513" which is the corresponding MAL ID)
    # I might just start include the "tmdb --> mal .json" map with this bot instead of selfhosting it as an api, but for now it works so I'll revisit the subject later
    tmdb_tvdb_id_to_mal = f"http://195.201.146.92:5000/api/?{content_type_to_value_dict[content_type]}={torrent_info[content_type_to_value_dict[content_type]]}"
    mal_id_response = requests.get(tmdb_tvdb_id_to_mal)

    # If the response returns http code 200 that means that a number has been returned, it'll either be the real mal ID or it will just be 0, either way we can use it
    if mal_id_response.status_code == 200:
        torrent_info["mal"] = str(mal_id_response.json())


def compare_tmdb_data_local(content_type):
    # We need to use TMDB to make sure we set the correct title & year as well as correct punctuation so we don't get held up in torrent moderation queues
    # I've outlined some scenarios below that can trigger issues if we just try to copy and paste the file name as the title

    # 1. For content that is 'non-english' we typically have a foreign title that we can (should) include in the torrent title using 'AKA' (K so both TMDB & OMDB API do not include this info, so we arent doing this)
    # 2. Some content has special characters (e.g.  The Hobbit: An Unexpected Journey   or   Welcome, or No Trespassing  ) we need to include these in the torrent title
    # 3. For TV Shows, Scene groups typically don't include the episode title in the filename, but we get this info from TMDB and include it in the title
    # 4. Occasionally movies that have a release date near the start of a new year will be using the incorrect year (e.g. the movie '300 (2006)' is occasionally mislabeled as '300 (2007)'

    # This will run regardless is auto_mode is set to true or false since I consider it pretty important to comply with all site rules and avoid creating extra work for tracker staff

    if content_type == "episode":  # translation for TMDB API
        content_type = "tv"
        content_title = "name"  # Again TV shows on TMDB have different keys then movies so we need to set that here
    else:
        content_title = "title"

    # We should only need 1 API request, so do that here
    get_media_info_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key={os.getenv('TMDB_API_KEY')}"
    get_media_info = requests.get(get_media_info_url).json()
    logging.info(f"GET Request: {get_media_info_url}")

    # Check the genres for 'Animation', if we get a hit we should check for a MAL ID just in case
    if "genres" in get_media_info:
        for genre in get_media_info["genres"]:
            if genre["name"] == 'Animation':
                search_for_mal_id(content_type=content_type, tmdb_id=torrent_info["tmdb"])

    # Acquire and set the title we get from TMDB here
    if content_title in get_media_info:
        torrent_info["title"] = get_media_info[content_title]
        logging.info(f"Using the title we got from TMDB: {torrent_info['title']}")

    # Set the year (if exists)
    if "release_date" in get_media_info and len(get_media_info["release_date"]) > 0:
        # if len(get_media_info["release_date"]) > 0:
        torrent_info["year"] = get_media_info["release_date"][:4]


def format_title(json_config):
    # If the user provides this arg with the title right after in double quotes then we automatically use that
    if args.title:
        torrent_info["torrent_title"] = str(args.title[0])

    # If the user does not manually provide the title (Most common) then we pull the renaming template from *.json & use all the info we gathered earlier to generate a title
    else:
        # ------------------ Load correct "naming config" ------------------ #
        # Here we open the uploads corresponding .json file and using the current uploads "source" we pull in a custom naming config
        # this "naming config" can individually tweaked for each site & "content_type" (bluray_encode, web, etc)

        # Because 'webrips' & 'webdls' have basically the same exact naming style we convert the 'source_type' to just 'web' (we do something similar to DVDs as well)
        if str(torrent_info["source"]).lower() == "dvd":
            config_profile = "dvd"
        elif str(torrent_info["source"]).lower() == "web":
            config_profile = "web"
        else:
            config_profile = torrent_info["source_type"]

        # tracker_torrent_name_style_config = torrent_info["source_type"] if str(torrent_info["source"]).lower() != "web" else "web"
        tracker_torrent_name_style_config = config_profile
        tracker_torrent_name_style = json_config['torrent_title_format'][torrent_info["type"]][str(tracker_torrent_name_style_config)]

        # ------------------ Set some default naming styles here ------------------ #
        # Fix BluRay
        if "bluray" in torrent_info["source_type"]:
            if "disc" in torrent_info["source_type"]:
                # Raw bluray discs have a "-" between the words "Blu" & "Ray"
                torrent_info["source"] = "Blu-ray"
            else:
                # BluRay encodes & Remuxs just use the complete word "BluRay"
                torrent_info["source"] = "BluRay"

        # Now fix WEB
        if str(torrent_info["source"]).lower() == "web":
            if torrent_info["source_type"] == "webrip":
                torrent_info["web_type"] = "WEBRip"
            else:
                torrent_info["web_type"] = "WEB-DL"

        # Fix DVD
        if str(torrent_info["source"]).lower() == "dvd":
            if torrent_info["source_type"] in ('dvd_remux', 'dvd_disc'):
                # later in the script if this ends up being a DVD Remux we will add the tag "Remux" to the torrent title
                torrent_info["source"] = "DVD"
            else:
                # Anything else is just a dvdrip
                torrent_info["source"] = "DVDRip"

        # ------------------ Actual format the title now ------------------ #

        # This dict will store the "torrent_info" response for each item in the "naming config"
        generate_format_string = {}
        temp_load_torrent_info = tracker_torrent_name_style.replace("{", "").replace("}", "").split(" ")
        for item in temp_load_torrent_info:
            # Here is were we actual get the torrent_info response and add it to the "generate_format_string" dict we declared earlier
            generate_format_string[item] = torrent_info[item] if item in torrent_info else ""

        formatted_title = ""  # This is the final torrent title, we add any info we get from "torrent_info" to it using the "for loop" below
        for key, value in generate_format_string.items():
            # ignore no matches (e.g. most TV Shows don't have the "year" added to its title so unless it was directly specified in the filename we also ignore it)
            if len(value) != 0:  
                formatted_title = f'{formatted_title}{"-" if key == "release_group" else " "}{value}'

        # Finally save the "formatted_title" into torrent_info which later will get passed to the dict "tracker_settings" 
        # which is used to store the payload for the actual POST upload request
        torrent_info["torrent_title"] = str(formatted_title[1:])

    # Update discord channel
    if discord_url:
        time.sleep(1)
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content='f'Torrent Title: **{torrent_info["torrent_title"]}**')


# ---------------------------------------------------------------------- #
#                       generate/edit .torrent file                      #
# ---------------------------------------------------------------------- #

def generate_callback(torrent, filepath, pieces_done, pieces_total):
    calculate_percentage = 100 * float(pieces_done) / float(pieces_total)
    print_progress_bar(calculate_percentage, 100, prefix='Creating .torrent file:', suffix='Complete', length=30)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


def generate_dot_torrent(media, announce, source, callback=None):
    """
        media : the -p path param passed to GGBot. (dot torrent will be created for this path or file)
    """
    logging.info("Creating the .torrent file now")
    logging.info("announce url: {}".format(announce[0]))
    if len(glob.glob(working_folder + "/temp_upload/*.torrent")) == 0:
        logging.info("Existing .torrent file does not exist so we need to generate a new one")
        # we need to actually generate a torrent file "from scratch"
        if args.use_mktorrent:
            print("Using mktorrent to generate the torrent")
            logging.info("Using MkTorrent to generate the torrent")
            """
            mktorrent options
                -v => Be verbose.
                -p => Set the private flag.
                -a => Specify the full announce URLs.  Additional -a adds backup trackers.
                -o => Set the path and filename of the created file.  Default is <name>.torrent.
                -c => Add a comment to the metainfo.
                -s => Add source string embedded in infohash.
                
                -e *.txt,*.jpg,*.png,*.nfo,*.svf,*.rar,*.screens,*.sfv # TODO to be added when supported mktorrent is available in alpine
            current version of mktorrent pulled from alpine package doesn't have the -e flag.
            Once an updated version is available, the flag can be added
            """
            if len(announce) == 1:
                os.system(f"mktorrent -v -p -l 23 -c \"Torrent created by GG-Bot-Uploader\" -s '{source}' -a '{announce[0]}' -o \"{working_folder}/temp_upload/{tracker}-{torrent_info['torrent_title']}.torrent\" \"{media}\"")
            else:
                os.system(f"mktorrent -v -p -l 23 -c \"Torrent created by GG-Bot-Uploader\" -s '{source}' -a '{announce}' -o \"{working_folder}/temp_upload/{tracker}-{torrent_info['torrent_title']}.torrent\" \"{media}\"")
            logging.info("Mktorrent .torrent write into {}".format("[" + source + "]" + torrent_info["torrent_title"] + ".torrent"))
        else:
            print("Using python torf to generate the torrent")
            torrent = Torrent(media,
                              trackers=announce,
                              source=source,
                              comment="Torrent created by GG-Bot-Uploader",
                              created_by="GG-Bot-Uploader",
                              exclude_globs=["*.txt", "*.jpg", "*.png", "*.nfo", "*.svf", "*.rar", "*.screens","*.sfv"],
                              private=True,
                              creation_date=datetime.datetime.now())
            torrent.generate(callback=callback)
            torrent.write(f'{working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent')
            # Save the path to .torrent file in torrent_settings
            torrent_info["dot_torrent"] = f'{working_folder}/temp_upload/{torrent_info["torrent_title"]}.torrent'
            logging.info("Trying to write into {}".format("[" + source + "]" + torrent_info["torrent_title"] + ".torrent"))
    else:
        print("Editing previous .torrent file to work with {} instead of generating a new one".format(source))
        logging.info("Editing previous .torrent file to work with {} instead of generating a new one".format(source))

        # just choose whichever, doesn't really matter since we replace the same info anyways
        edit_torrent = Torrent.read(glob.glob(working_folder + '/temp_upload/*.torrent')[0])

        edit_torrent.metainfo['announce'] = announce[0]
        edit_torrent.metainfo['info']['source'] = source
        edit_torrent.metainfo['comment'] = ""
        # Edit the previous .torrent and save it as a new copy
        Torrent.copy(edit_torrent).write(f'{working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent')

    if os.path.isfile(f'{working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent'):
        logging.info(f'Successfully created the following file: {working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent')
    else:
        logging.error(f'The following .torrent file was not created: {working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent')


# ---------------------------------------------------------------------- #
#                  Set correct tracker API Key/Values                    #
# ---------------------------------------------------------------------- #

def choose_right_tracker_keys():
    required_items = config["Required"]
    optional_items = config["Optional"]

    # BLU requires the IMDB with the "tt" removed so we do that here, BHD will automatically put the "tt" back in... so we don't need to make an exception for that
    if "imdb" in torrent_info:
        if len(torrent_info["imdb"]) >= 2:
            if str(torrent_info["imdb"]).startswith("tt"):
                torrent_info["imdb"] = str(torrent_info["imdb"]).replace("tt", "")
        else:
            torrent_info["imdb"] = "0"

    # torrent title
    tracker_settings[config["translation"]["torrent_title"]] = torrent_info["torrent_title"]

    # Save a few key values in a list that we'll use later to identify the resolution and type
    relevant_torrent_info_values = []
    for torrent_info_k in torrent_info:
        if torrent_info_k in ["source_type", "screen_size", "bluray_disc_type"]:
            relevant_torrent_info_values.append(torrent_info[torrent_info_k])

    def identify_resolution_source(target_val):
        # 0 = optional
        # 1 = required
        # 2 = select from available items in list

        possible_match_layer_1 = []
        for key in config["Required"][(config["translation"][target_val])]:
            total_num_of_required_keys = 0
            total_num_of_acquired_keys = 0

            # If we have a list of options to choose from, each match is saved here
            total_num_of_acquired_keys_val = 0

            select_from_optional_values_list = []
            for sub_key, sub_val in config["Required"][(config["translation"][target_val])][key].items():

                if sub_val == 1:
                    total_num_of_required_keys += 1
                    # Now check if the sub_key is in the relevant_torrent_info_values list
                    if sub_key in str(relevant_torrent_info_values).lower():
                        total_num_of_acquired_keys += 1

                if sub_val == 2:
                    if sub_key in str(relevant_torrent_info_values).lower():
                        total_num_of_acquired_keys_val += 1
                    select_from_optional_values_list.append(sub_key)

            # print(f'\nselect_from_optional_values_list: {select_from_optional_values_list}')
            # print(f'total_num_of_required_keys: {total_num_of_required_keys}')
            # print(f'total_num_of_acquired_keys_val: {total_num_of_acquired_keys_val}')
            # print(f'total_num_of_acquired_keys: {total_num_of_acquired_keys}\n')

            if int(total_num_of_required_keys) == int(total_num_of_acquired_keys):
                possible_match_layer_1.append(key)
                # We check for " == 0" so that if we get a profile that matches all the "1" then we can break immediately (2160p BD remux requires 'remux', '2160p', 'bluray')
                # so if we find all those values in select_from_optional_values_list list then we can break knowing that we hit 100% of the required values instead of having to
                # cycle through the "optional" values and select one of them
                if len(select_from_optional_values_list) == 0 and key != "Other":
                    break

                if len(select_from_optional_values_list) >= 2 and int(total_num_of_acquired_keys_val) == 1:
                    break

            if len(possible_match_layer_1) >= 2 and "Other" in possible_match_layer_1:
                possible_match_layer_1.remove("Other")

        if len(possible_match_layer_1) == 1:
            target_val = possible_match_layer_1.pop()
        else:
            # this means we either have 2 potential matches or no matches at all (this happens if the media does not fit any of the allowed parameters)
            logging.critical('Unable to find a suitable "source" match for this file')
            logging.error("Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip to BLU is not allowed")
            console.print(f'\nThis "Type" ([bold]{torrent_info["source"]}[/bold]) or this "Resolution" ([bold]{torrent_info["screen_size"]}[/bold]) is not allowed on this tracker',
                style='Red underline', highlight=False)
            sys.exit()

        return target_val

    # ------------ required_items ------------
    for required_key, required_value in required_items.items():
        for translation_key, translation_value in config["translation"].items():
            if str(required_key) == str(translation_value):

                # the torrent file is always submitted as a file
                if required_value == "file":
                    if translation_key in torrent_info:
                        tracker_settings[config["translation"][translation_key]] = torrent_info[translation_key]
                    # Make sure you select the right .torrent file
                    if translation_key == "dot_torrent":
                        tracker_settings[config["translation"]["dot_torrent"]] = f'{working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent'

                # The reason why we keep this elif statement here is because the conditional right above is also technically a "string"
                # but its easier to keep mediainfo and description in text files until we need them so we have that small exception for them
                elif required_value == "string":

                    # We dump all the info from torrent_info in tracker_settings here
                    if translation_key in torrent_info:
                        tracker_settings[config["translation"][translation_key]] = torrent_info[translation_key]

                    # BHD requires the key "live" (0 = Sent to drafts and 1 = Live on site)
                    elif required_key == "live":
                        live = '1' if is_live_on_site == 'true' else '0'
                        logging.info(f"Upload live status: {'Live (Visible)' if is_live_on_site == 'true' else 'Draft (Hidden)'}")
                        tracker_settings[config["translation"][translation_key]] = live

                    # If the user supplied the "-anon" argument then we want to pass that along when uploading
                    elif translation_key == "anon" and args.anon:
                        logging.info("Uploading anonymously")
                        tracker_settings[config["translation"][translation_key]] = "1"

                    # Adding support for internal args
                    elif translation_key in ['doubleup', 'featured', 'freeleech', 'internal', 'sticky', 'tripleup']:
                        tracker_settings[config["translation"][translation_key]] = "1" if getattr(args, translation_key) is True else "0"

                    # This work as a sort of 'catch all', if we don't have the correct data in torrent_info, we just send a 0 so we can successfully post
                    else:
                        tracker_settings[config["translation"][translation_key]] = "0"

                # Set the category ID, this could be easily hardcoded in (1=movie & 2=tv) but I chose to use JSON data just in case a future tracker switches this up
                if translation_key == "type":
                    for key_cat, val_cat in config["Required"][required_key].items():
                        if torrent_info["type"] == val_cat:
                            tracker_settings[config["translation"][translation_key]] = key_cat

                if translation_key in ('source', 'resolution'):
                    # value = identify_resolution_source(translation_key)
                    tracker_settings[config["translation"][translation_key]] = identify_resolution_source(translation_key)

    # ------------ optional_items ------------
    # This mainly applies to BHD since they are the tracker with the most 'Optional' fields, BLU/ACM only have 'nfo_file' as an optional item which we take care of later
    # It is for this reason ^^ why the following block is coded with BHD specifically in mind
    for optional_key, optional_value in optional_items.items():

        # -!-!- Editions -!-!- #
        if optional_key == 'edition' and 'edition' in torrent_info:
            # First we remove any 'fluff' so that we can try to match the edition to the list BHD has, if not we just upload it as a custom edition
            local_edition_formatted = str(torrent_info["edition"]).lower().replace("edition", "").replace("cut", "").replace("'", "").replace(" ", "")
            if local_edition_formatted.endswith('s'):  # Remove extra 's'
                local_edition_formatted = local_edition_formatted[:-1]
            # Now check to see if what we got out of the filename already exists on BHD
            for bhd_edition in optional_value:
                if str(bhd_edition).lower() == local_edition_formatted:
                    # If its a match we save the value to tracker_settings here
                    tracker_settings[optional_key] = bhd_edition
                    break
                else:
                    # We use the 'custom_edition' to set our own, again we only do this if we can't match what BHD already has available to select
                    tracker_settings["custom_edition"] = torrent_info["edition"]

        # -!-!- Region -!-!- # (Disc only)
        if optional_key == 'region' and 'region' in torrent_info:
            # This will only run if you are uploading a bluray_disc
            for region in optional_value:
                if str(region).upper() == str(torrent_info["region"]).upper():
                    tracker_settings[optional_key] = region
                    break

        # -!-!- Tags -!-!- #
        if optional_key == 'tags':  # (Only supported on BHD)
            # We only support 2 tags atm, Scene & WEBDL/RIP on bhd
            # All we currently support regarding tags, is to assign the 'Scene' tag if we are uploading a scene release
            upload_these_tags_list = []
            for tag in optional_value:

                # This will check for the 'Scene' tag
                if str(tag).lower() in str(torrent_info.keys()).lower():
                    upload_these_tags_list.append(str(tag))
                    # tracker_settings[optional_key] = str(tag)

                # This will check for webdl/webrip tag
                if str(tag) in ["WEBRip", "WEBDL"]:
                    # Check if we are uploading one of those ^^ 'sources'
                    if str(tag).lower() == str(torrent_info["source_type"]).lower():
                        upload_these_tags_list.append(str(tag))
            if len(upload_these_tags_list) != 0:
                tracker_settings[optional_key] = ",".join(upload_these_tags_list)

        # TODO figure out why .nfo uploads fail on BHD & don't display on BLU...
        # if optional_key in ["nfo_file", "nfo"] and "nfo_file" in torrent_info:
        #     # So far
        #     tracker_settings[optional_key] = torrent_info["nfo_file"]

        if optional_key == 'sd' and "sd" in torrent_info:
            tracker_settings[optional_key] = 1

        if optional_key in ['season_number', 'episode_number'] and optional_key in torrent_info:
            tracker_settings[optional_key] = torrent_info.get(optional_key, "")


# ---------------------------------------------------------------------- #
#                             Upload that shit!                          #
# ---------------------------------------------------------------------- #
def upload_to_site(upload_to, tracker_api_key):
    logging.info("Attempting to upload to: {}".format(upload_to))
    url = str(config["upload_form"]).format(api_key=tracker_api_key)

    payload = {}
    files = []
    display_files = {}

    for key, val in tracker_settings.items():
        # First check to see if its a required or optional key
        if key in config["Required"]:
            req_opt = 'Required'
        else:
            req_opt = 'Optional'

        # Now that we know if we are looking for a required or optional key we can try to add it into the payload
        if str(config[req_opt][key]) == "file":
            if os.path.isfile(tracker_settings['{}'.format(key)]):
                post_file = f'{key}', open(tracker_settings[f'{key}'], 'rb')
                files.append(post_file)
                display_files[key] = tracker_settings[f'{key}']
            else:
                logging.critical("The file/path {} does not exist!".format(tracker_settings['{}'.format(key)]))
                continue
        else:
            # if str(val).endswith(".nfo") or str(val).endswith(".txt"):
            if str(val).endswith(".txt"):
                if not os.path.exists(val):
                    create_file = open(val, "w+")
                    create_file.close()
                with open(val, 'r') as txt_file:
                    val = txt_file.read()
            if req_opt == "Optional":
                print(key, val)
            payload[key] = val

    if auto_mode == "false":
        # prompt the user to verify everything looks OK before uploading

        # ------- Show the user a table of the API KEY/VAL (TEXT) that we are about to send ------- #
        review_upload_settings_text_table = Table(title=f"\n\n\n\n[bold][deep_pink1]{upload_to} POST data (Text):[/bold][/deep_pink1]", 
            show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim", show_lines=True, title_justify='left')

        review_upload_settings_text_table.add_column("Key", justify="left")
        review_upload_settings_text_table.add_column("Value (TEXT)", justify="left")
        # Insert the data into the table, raw data (no paths)
        for payload_k, payload_v in sorted(payload.items()):
            # Add torrent_info data to each row
            review_upload_settings_text_table.add_row(f"[deep_pink1]{payload_k}[/deep_pink1]", f"[dodger_blue1]{payload_v}[/dodger_blue1]")
        console.print(review_upload_settings_text_table, justify="center")

        # ------- Show the user a table of the API KEY/VAL (FILE) that we are about to send ------- #
        review_upload_settings_files_table = Table(title=f"\n\n\n\n[bold][green3]{upload_to} POST data (FILES):[/green3][/bold]", 
            show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim", show_lines=True, title_justify='left')

        review_upload_settings_files_table.add_column("Key", justify="left")
        review_upload_settings_files_table.add_column("Value (FILE)", justify="left")
        # Insert the path to the files we are uploading
        for payload_file_k, payload_file_v in sorted(display_files.items()):
            # Add torrent_info data to each row
            review_upload_settings_files_table.add_row(f"[green3]{payload_file_k}[/green3]", f"[dodger_blue1]{payload_file_v}[/dodger_blue1]")
        console.print(review_upload_settings_files_table, justify="center")

        # Give the user a chance to stop the upload
        continue_upload = Prompt.ask("Do you want to upload with these settings?", choices=["y", "n"])
        if continue_upload != "y":
            console.print(f"\nCanceling upload to [bright_red]{upload_to}[/bright_red]")
            logging.error(f"User-input chose to cancel the upload to {tracker}")
            return

    logging.info("Payload for {site} is {payload}".format(site=upload_to, payload=payload))
    logging.info("Files for {site} is {files}".format(site=upload_to, files=files))

    logging.fatal("URL: {url} \n Data: {data} \n Files: {files}".format(url=url, data=payload, files=files))

    response = requests.request("POST", url, data=payload, files=files)
    logging.info(f"POST Request: {url}")
    logging.info(f"Response code: {response.status_code}")

    console.print(f'Site response: [blue]{response.text}[/blue]')
    logging.info(response.text)

    if response.status_code == 200:
        logging.info(f"upload response for {upload_to}: {response.text.encode('utf8')}")
        # Update discord channel
        if discord_url:
            requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f"content=Upload response: **{response.text.encode('utf8')}**")

        if "success" in str(response.json()).lower():
            if str(response.json()["success"]).lower() == "true":
                logging.info("Upload to {} was a success!".format(upload_to))
                console.print(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style="bold green1 underline")
            else:
                logging.critical("Upload to {} failed".format(upload_to))
        else:
            logging.critical("Something really went wrong when uploading to {} and we didn't even get a 'success' json key".format(upload_to))

    elif response.status_code == 404:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print('Upload failed', style='bold red')
        logging.critical(f"404 was returned on that upload, this is a problem with the site ({tracker})")
        logging.error("Upload failed")

    elif response.status_code == 500:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The upload might have [red]failed[/], the site isn't returning the uploads status")
        # This is to deal with the 500 internal server error responses BLU has been recently returning
        logging.error(f"HTTP response status code '{response.status_code}' was returned (500=Internal Server Error)")
        logging.info("This doesn't mean the upload failed, instead the site simply isn't returning the upload status")

    else:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The status code isn't [green]200[/green] so something failed, upload may have failed")
        logging.error('status code is not 200, upload might have failed')


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#  **START** This is the first code that executes when we run the script, we log that info and we start a timer so we can keep track of total script runtime **START** #
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#
script_start_time = time.perf_counter()
starting_new_upload = f" {'-' * 24} Starting new upload {'-' * 24} "

logging.info(starting_new_upload)

if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"Arguments provided by user: {args}")

if args.tripleup and args.doubleup:
    console.print("You can not use the arg [deep_sky_blue1]-doubleup[/deep_sky_blue1] and [deep_sky_blue1]-tripleup[/deep_sky_blue1] together. Only one can be used at a time\n", style='bright_red')
    console.print("Exiting...\n", style='bright_red bold')
    sys.exit()

# Set the value of args.path to a variable that we can overwrite with a path translation later (if needed)
user_supplied_paths = args.path

# Verify the script is in "auto_mode" and if needed map rtorrent download path to system path
if args.reupload:
    logging.info('reuploading a match from autodl')

    # Firstly remove the underscore separator from the trackers the user provided in the autodl filter & make replace args.trackers with it
    args.trackers = str(args.trackers[0]).split('_')

    # set auto_mode equal to True for this upload (if its not already)
    # since we are reuploading autodl matches its probably safe to say this is all automated & no one will be available to approve or interact with any prompt
    if auto_mode == 'false':
        logging.info('Temporarily switching "auto_mode" to "true" for this autodl reupload')
        auto_mode = 'true'

    if str(os.getenv('translation_needed')).lower() == 'true':
        # Currently it is only possible for 1 path to be based from autodl but just in case & for futureproofing we will treat it as a list of multiple paths
        logging.info('Translating paths... ("translation_needed" flag set to True in config.env) ')

        # Just in case the user didn't end the path with a forward slash...
        host_path = f"{os.getenv('host_path')}/".replace('//', '/')
        remote_path = f"{os.getenv('remote_path')}/".replace('//', '/')

        # Now we replace the remote (rtorrent) path with the system one
        for path in user_supplied_paths:
            translated_path = str(path).replace(remote_path, host_path)

            # Remove the old path from the list & add the new one in its place
            user_supplied_paths.remove(path)
            user_supplied_paths.append(translated_path)

            # And finally log the changes
            logging.info(f'rtorrent path: {path}')
            logging.info(f'Translated path: {translated_path}')

# If a user has supplied a discord webhook URL we can send updates to that channel
if discord_url:
    requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content={starting_new_upload}')

# Verify we support the tracker specified
upload_to_trackers = []
logging.debug(f"Trackers provided by user {args.trackers}")

for tracker in args.trackers:
    if "{tracker}_api_key".format(tracker=str(tracker).lower()) in api_keys_dict:
        # Make sure that an API key is set for that site
        try:
            if len(api_keys_dict[(str(tracker).lower()) + "_api_key"]) <= 1:
                raise AssertionError("Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)")
            if str(tracker).upper() not in upload_to_trackers : upload_to_trackers.append(str(tracker).upper())
        except AssertionError as err:
            logging.error("We can't upload to '{}' because that sites API key is not specified".format(tracker))
    else:
        logging.error("We can't upload to '{}' because that site is not supported".format(tracker))

# Make sure that the user provides at least 1 valid tracker we can upload to
try:
    # if len(upload_to_trackers) == 0 that means that the user either didn't provide any site at all, the site is not supported, or the API key isn't provided
    if len(upload_to_trackers) < 1:
        raise AssertionError("Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)")
except AssertionError as err:  # Log AssertionError in the logfile and quit here
    logging.exception("No valid trackers specified for upload destination (e.g. BHD, BLU, ACM)")
    raise err

logging.debug(f"Trackers selected by bot: {upload_to_trackers}")

# Show the user what sites we will upload to
console.line(count=2)
console.rule(f"Target Trackers", style='red', align='center')
console.line(count=1)
upload_to_trackers_overview = Table(box=box.SQUARE, show_header=True, header_style="bold cyan")

for upload_to_tracker in ["Acronym", "Site", "URL", "Platform"]:
    upload_to_trackers_overview.add_column(f"{upload_to_tracker}", justify='center', style='#38ACEC')

for tracker in upload_to_trackers:
    with open(f"{working_folder}/site_templates/{str(acronym_to_tracker.get(str(tracker).lower()))}.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    # Add tracker data to each row & show the user an overview
    upload_to_trackers_overview.add_row(tracker, config["name"], config["url"], config["platform"])

console.print(upload_to_trackers_overview)

# If not in 'auto_mode' then verify with the user that they want to continue with the upload
if auto_mode == "false":
    if not Confirm.ask("Continue upload to these sites?", default='y'):
        logging.info("User canceled upload when asked to confirm sites to upload to")
        sys.exit(console.print("\nOK, quitting now..\n", style="bold red", highlight=False))

# The user has confirmed what sites to upload to at this point (or auto_mode is set to true)
# Get media file details now, check to see if we are running in "batch mode"

# TODO an issue with batch mode currently is that we have a lot of "assert" & sys.exit statements during the prep work we do for each upload, if one of these "assert/quit" statements
#  get triggered, then it will quit the entire script instead of just moving on to the next file in the list 'upload_queue'

# ---------- Batch mode prep ---------- #
if args.batch and len(args.path) > 1:
    logging.critical("the arg '-batch' can not be run with multiple '-path' args")
    logging.info("the arg '-batch' should be used to upload all the files in 1 folder that you specify with the '-path' arg")
    console.print("You can not use the arg [deep_sky_blue1]-batch[/deep_sky_blue1] while supplying multiple [deep_sky_blue1]-path[/deep_sky_blue1] args\n", style='bright_red')
    console.print("Exiting...\n", style='bright_red bold')
    sys.exit()


elif args.batch and not os.path.isdir(args.path[0]):
    # Since args.path is required now, we don't need to check if len(args.path) == 0 since that's impossible
    # instead we check to see if its a folder, if not then
    logging.critical("the arg '-batch' can not be run an a single video file")
    logging.info("the arg '-batch' should be used to upload all the files in 1 folder that you specify with the '-path' arg")
    console.print("We can not [deep_sky_blue1]-batch[/deep_sky_blue1] upload a single video file, [deep_sky_blue1]-batch[/deep_sky_blue1] is supposed to be used on a "
        "single folder containing multiple files you want to individually upload\n", style='bright_red')
    console.print("Exiting...\n", style='bright_red bold')
    sys.exit()

# all files we upload (even if its 1) get added to this list
upload_queue = []

if args.batch:
    logging.info("running in batch mode")
    logging.info(f"Uploading all the items in the folder: {args.path}")
    # This should be OK to upload, we've caught all the obvious issues above ^^ so if this is able to run we should be alright
    for arg_file in glob.glob(f'{args.path[0]}/*'):
        # Since we are in batch mode, we upload every file/folder we find in the path the user specified
        upload_queue.append(arg_file)  # append each item to the list 'upload_queue' now
else:
    logging.info("Running in regular '-path' mode, starting upload now")
    # This means the ran the script normally and specified a direct path to some media (or multiple media items, in which case we append it like normal to the list 'upload_queue')
    for arg_file in user_supplied_paths:
        upload_queue.append(arg_file)

logging.debug(f"Upload queue: {upload_queue}")

# Now for each file we've been supplied (batch more or just the user manually specifying multiple files) we create a loop here that uploads each of them until none are left
for file in upload_queue:
    # Remove all old temp_files & data from the previous upload
    delete_leftover_files()
    torrent_info.clear()

    # File we're uploading
    console.print(f'Uploading File/Folder: [bold][blue]{file}[/blue][/bold]')

    # If the path the user specified is a folder with .rar files in it then we unpack the video file & set the torrent_info key equal to the extracted video file
    if os.path.isdir(file):
        logging.debug(f"User wants to upload a folder: {file}")
        # Set the 'upload_media' right away, if we end up extracting from a rar archive we will just overwriting it with the .mkv we extracted
        torrent_info["upload_media"] = file

        # Now we check to see if the dir contains rar files
        rar_file = glob.glob(f"{os.path.join(file, '')}*rar")
        if rar_file:
            logging.info(f"'{file}' is a .rar archive, extracting now")
            logging.info(f"rar file: {rar_file[0]}")

            # Now verify that unrar is installed
            unrar_sys_package = '/usr/bin/unrar'
            if os.path.isfile(unrar_sys_package):
                logging.info("Found 'unrar' system package, Using it to extract the video file now")

                # run the system package unrar and save the extracted file to its parent dir
                subprocess.run([unrar_sys_package, 'e', rar_file[0], file])
                logging.debug(f"Successfully extracted file : {rar_file[0]}")

                # This is how we identify which file we just extracted (Last modified)
                list_of_files = glob.glob(f"{os.path.join(file, '')}*")
                latest_file = max(list_of_files, key=os.path.getctime)

                # Overwrite the value for 'upload_media' with the path to the video file we just extracted
                torrent_info["upload_media"] = latest_file
                logging.debug(f"Using the extracted {latest_file} for further processing")

            # If the user doesn't have unrar installed then we let them know here and move on to the next file (if exists)
            else:
                console.print('unrar is not installed, Unable to extract the rar archinve\n', style='bold red')
                logging.critical('"unrar" is not installed, Unable to extract rar archive')
                logging.info('Perhaps first try "sudo apt-get install unrar" then run this script again')
                continue  # Skip this entire 'file upload' & move onto the next (if exists)
    else:
        torrent_info["upload_media"] = file
        logging.info(f'uploading the following file: {file}')

    # Performing guessit on the rawfile name and reusing the result instead of calling guessit over and over again
    guessit_start_time = time.perf_counter()
    guess_it_result = guessit(torrent_info["upload_media"])
    guessit_end_time = time.perf_counter()
    logging.debug(f'Time taken for guessit regex operations :: {guessit_end_time - guessit_start_time}')
    logging.debug("::::::::::::::::::::::::::::: GuessIt output result :::::::::::::::::::::::::::::")
    logging.debug(pformat(guess_it_result))
    
    # -------- Basic info --------
    # So now we can start collecting info about the file/folder that was supplied to us (Step 1)
    if identify_type_and_basic_info(torrent_info["upload_media"], guess_it_result) == 'skip_to_next_file':
        # If there is an issue with the file & we can't upload we use this check to skip the current file & move on to the next (if exists)
        logging.debug(f"Skipping {torrent_info['upload_media']} because type and basic information cannot be identified.")
        continue

    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
                data=f'content=Uploading: **{torrent_info["upload_media"]}**')

    # -------- add .nfo if exists --------
    if args.nfo:
        if os.path.isfile(args.nfo[0]):
            torrent_info["nfo_file"] = args.nfo[0]

    # If the user didn't supply the path we can still try to auto detect it
    else:
        nfo = glob.glob(f"{torrent_info['upload_media']}/*.nfo")
        if nfo and len(nfo) > 0:
            torrent_info["nfo_file"] = nfo[0]

    # -------- Fix/update values --------
    # set the correct video & audio codecs (Dolby Digital --> DDP, use x264 if encode vs remux etc)
    identify_miscellaneous_details(guess_it_result)
    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
            data=f'content='f'Video Code: **{torrent_info["video_codec"]}**  |  Audio Code: **{torrent_info["audio_codec"]}**')

    # -------- Get TMDB & IMDB ID --------
    # If the TMDB/IMDB was not supplied then we need to search TMDB for it using the title & year

    for media_id_key, media_id_val in {"tmdb": args.tmdb, "imdb": args.imdb}.items():
        if media_id_val is not None and len(media_id_val[0]) > 1:  # we include ' > 1 ' to prevent blank ID's and issues later

            # We have one more check here to verify that the "tt" is included for the IMDB ID (TMDB won't accept it if it doesnt)
            if media_id_key == 'imdb' and not str(media_id_val[0]).lower().startswith('tt'):
                torrent_info["imdb"] = f'tt{media_id_val[0]}'
            else:
                torrent_info[media_id_key] = media_id_val[0]

    if all(x in torrent_info for x in ['imdb', 'tmdb']):
        # This means both the TMDB & IMDB ID are already in the torrent_info dict
        logging.info("Both TMDB & IMDB ID have been supplied by the user, so no need to make any TMDB API request")
    elif any(x in torrent_info for x in ['imdb', 'tmdb']):
        # This means we can skip the search via title/year and instead use whichever ID to get the other (tmdb -> imdb and vice versa)
        missing_id_key = 'tmdb' if 'imdb' in torrent_info else 'imdb'
        existing_id_key = 'tmdb' if 'tmdb' in torrent_info else 'imdb'
        logging.info(f"We are missing '{missing_id_key}' starting TMDB API request now")
        # Now we call the function that will use the TMDB API to get whichever ID we are missing
        torrent_info[missing_id_key] = get_external_id(id_site=existing_id_key, id_value=torrent_info[existing_id_key], content_type=torrent_info["type"])
    else:
        logging.info("We are missing both the 'TMDB' & 'IMDB' ID, trying to identify it via title & year")
        search_tmdb_for_id(query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"])
    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
                data=f'content='f'IMDB: **{torrent_info["imdb"]}**  |  TMDB: **{torrent_info["tmdb"]}**')

    # -------- Use official info from TMDB --------
    compare_tmdb_data_local(torrent_info["type"])

    # -------- User input edition --------
    # Support for user adding in custom edition if its not obvious from filename
    if args.edition:
        user_input_edition = str(args.edition[0])
        logging.info(f"User specified edition: {user_input_edition}")
        console.print(f"\nUsing the user supplied edition: [medium_spring_green]{user_input_edition}[/medium_spring_green]")
        torrent_info["edition"] = user_input_edition

    # -------- Dupe check for single tracker uploads --------
    # If user has provided only one Tracker to upload to, then we do dupe check prior to taking screenshots. [if dupe_check is enabled]
    # If there are duplicates in the tracker, then we do not waste time taking and uploading screenshots.
    if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) == 1:
        tracker = upload_to_trackers[0]
        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]

        console.print('\n\n')
        console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')

        dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
        # If dupes are present and user decided to stop upload, for single tracker uploads we stop operation immediately
        # True == dupe_found
        # False == no_dupes/continue upload
        if dupe_check_response :
            logging.error(f"Could not upload to: {tracker} because we found a dupe on site")
            if discord_url:  # Send discord notification if enabled
                requests.post(url=discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
                        data=f'content='f'Dupe check failed, upload to **{str(tracker).upper()}** canceled')
            sys.exit(console.print("\nOK, quitting now..\n", style="bold red", highlight=False))

    # -------- Take / Upload Screenshots --------
    media_info_duration = MediaInfo.parse(torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"]).tracks[1]
    torrent_info["duration"] = str(media_info_duration.duration).split(".", 1)[0]  
    # This is used to evenly space out timestamps for screenshots
    # Call function to actually take screenshots & upload them (different file)
    take_upload_screens(duration=torrent_info["duration"],
        upload_media_import=torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"],
        torrent_title_import=torrent_info["title"], base_path=working_folder, discord_url=discord_url)

    if os.path.exists(f'{working_folder}/temp_upload/bbcode_images.txt'):
        torrent_info["bbcode_images"] = f'{working_folder}/temp_upload/bbcode_images.txt'

    # At this point the only stuff that remains to be done is site specific so we can start a loop here for each site we are uploading to
    logging.info("Now starting tracker specific tasks")
    for tracker in upload_to_trackers:
        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]
        logging.info(f"Trying to upload to: {tracker}")

        # Update discord channel
        if discord_url:
            requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content=Uploading to: **{config["name"]}**')

        # Create a new dictionary that we store the exact keys/vals that the site is expecting
        tracker_settings = {}
        tracker_settings.clear()

        # Open the correct .json file since we now need things like announce URL, API Keys, and API info
        with open("{}/site_templates/".format(working_folder) + str(acronym_to_tracker.get(str(tracker).lower())) + ".json", "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        # -------- format the torrent title --------
        format_title(config)

        # -------- Fill in description.txt --------
        if "bbcode_images" in torrent_info:
            # (Theory) BHD has a different bbcode parser then BLU/ACM so the line break is different for each site
            #   this is why we set it in each sites *.json file then retrieve it here in this 'for loop' since its different for each site
            bbcode_line_break = config['bbcode_line_break']

            # If the user is uploading to multiple sites we don't want to keep appending to the same description.txt file so remove it each time and write clean bbcode to it
            #  (Note, this doesn't delete bbcode_images.txt so you aren't uploading the same images multiple times)
            if os.path.isfile(f'{working_folder}/temp_upload/description.txt'):
                os.remove(f'{working_folder}/temp_upload/description.txt')

            # Now open up the correct files and format all the bbcode/tags below
            with open(torrent_info["bbcode_images"], 'r') as bbcode, open(f'{working_folder}/temp_upload/description.txt', 'a') as description:
                # First add the [center] tags, "Screenshots" header, Size tags etc etc. This only needs to be written once which is why its outside of the 'for loop' below
                description.write(f'{bbcode_line_break}[center] ---------------------- [size=22]Screenshots[/size] ---------------------- {bbcode_line_break}{bbcode_line_break}')

                # Now write in the actual screenshot bbcode
                for line in bbcode:
                    description.write(line)

                # Finally append the entire thing with some shameless self promotion ;) & and the closing [/center] tags and some line breaks
                description.write(f'{bbcode_line_break}{bbcode_line_break} Uploaded with [color=red]{"<3" if str(tracker).upper() in ("BHD") or os.name == "nt" else "❤"}[/color] using GG-BOT-Uploader[/center]')

            # Add the finished file to the 'torrent_info' dict
            torrent_info["description"] = f'{working_folder}/temp_upload/description.txt'

        # -------- Check for Dupes Multiple Trackers --------
        # when the user has configured multiple trackers to upload to
        # we take the screenshots and uploads them, then do dupe check for the trackers.
        # dupe check need not be performed if user provided only one tracker.
        # in cases where only one tracker is provided, dupe check will be performed prior to taking screenshots.
        if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) > 1:
            console.print('\n\n')
            console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')
            # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
            dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
            # True == dupe_found
            # False == no_dupes/continue upload
            if dupe_check_response:
                logging.error(f"Could not upload to: {tracker} because we found a dupe on site")
                # Send discord notification if enabled
                if discord_url:
                    requests.post(url=discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content='f'Dupe check failed, upload to **{str(tracker).upper()}** canceled')

                # If dupe was found & the script is auto_mode OR if the user responds with 'n' for the 'dupe found, continue?' prompt
                #  we will essentially stop the current 'for loops' iteration & jump back to the beginning to start next cycle (if exists else quits)
                continue

        # -------- Generate .torrent file --------
        console.print(f'\n[bold]Generating .torrent file for [chartreuse1]{tracker}[/chartreuse1][/bold]')

        generate_dot_torrent(
            media=torrent_info["upload_media"],
            announce=list(os.getenv(f"{str(tracker).upper()}_ANNOUNCE_URL").split(" ")),
            source=tracker,
            callback=generate_callback
        )

        # -------- Assign specific tracker keys --------
        choose_right_tracker_keys()  # This function takes the info we have the dict torrent_info and associates with the right key/values needed for us to use X trackers API
        logging.debug(f"Final torrent_info with all data filled ::::::::::::::::::::::::::::")
        logging.debug(pformat(torrent_info))
        # -------- Upload everything! --------
        # 1.0 everything we do in this for loop isn't persistent, its specific to each site that you upload to
        # 1.1 things like screenshots, TMDB/IMDB ID's can & are reused for each site you upload to
        # 2.0 we take all the info we generated outside of this loop (mediainfo, description, etc) and combine it with tracker specific info and upload it all now
        upload_to_site(upload_to=tracker, tracker_api_key=temp_tracker_api_key)

        # Tracker Settings
        tracker_settings_table = Table(show_header=True, header_style="bold cyan")
        tracker_settings_table.add_column("Key", justify="left")
        tracker_settings_table.add_column("Value", justify="left")

        for tracker_settings_key, tracker_settings_value in sorted(tracker_settings.items()):
            # Add torrent_info data to each row
            tracker_settings_table.add_row(f"[purple][bold]{tracker_settings_key}[/bold][/purple]", str(tracker_settings_value))
        console.print(tracker_settings_table)

    # -------- Post Processing --------
    # After we upload the media we can move the .torrent & media files to a place the user specifies
    # This isn't tracker specific so its outside of that ^^ 'for loop'

    move_locations = {"torrent": f"{os.getenv('dot_torrent_move_location')}", "media": f"{os.getenv('media_move_location')}"}

    for move_location_key, move_location_value in move_locations.items():
        # If the user supplied a path & it exists we proceed
        if len(move_location_value) != 0 and os.path.exists(move_location_value):
            logging.info(f"The path {move_location_value} exists")

            if move_location_key == 'torrent':
                # The user might have upload to a few sites so we need to move all files that end with .torrent to the new location
                list_dot_torrent_files = glob.glob(f"{working_folder}/temp_upload/*.torrent")
                for dot_torrent_file in list_dot_torrent_files:
                    # Move each .torrent file we find into the directory the user specified
                    shutil.copy(dot_torrent_file, move_locations["torrent"])

            # Media files are moved instead of copied so we need to make sure they don't already exist in the path the user provides
            if move_location_key == 'media':
                if str(f"{Path(torrent_info['upload_media']).parent}/") == move_location_value:
                    console.print(f'\nError, {torrent_info["upload_media"]} is already in the move location you specified: "{move_location_value}"\n', style="red", highlight=False)
                    logging.error(f"{torrent_info['upload_media']} is already in {move_location_value}, Not moving the media")
                else:
                    logging.info(f"Moved {torrent_info['upload_media']} to {move_location_value}")
                    shutil.move(torrent_info["upload_media"], move_location_value)

    # Torrent Info
    torrent_info_table = Table(show_header=True, header_style="bold cyan")
    torrent_info_table.add_column("Key", justify="left")
    torrent_info_table.add_column("Value", justify="left")

    for torrent_info_key, torrent_info_value in sorted(torrent_info.items()):
        # Add torrent_info data to each row
        torrent_info_table.add_row("[purple][bold]{}[/bold][/purple]".format(torrent_info_key), str(torrent_info_value))
    
    console.print(torrent_info_table)

    script_end_time = time.perf_counter()
    total_run_time = f'{script_end_time - script_start_time:0.4f}'
    logging.info(f"Total runtime is {total_run_time} seconds")
    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content='f'Total runtime: **{total_run_time} seconds**')
