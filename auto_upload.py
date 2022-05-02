#!/usr/bin/env python3

# default included packages
import os
import re
import sys
import math
import glob
import time
import json
import base64
import shutil
import logging
import argparse
import subprocess
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

# Search for **START** to get to the execution entry point of the upload assistant.

# This is used to take screenshots and eventually upload them to either imgbox, imgbb, ptpimg or freeimage
from images.upload_screenshots import take_upload_screens

# utility methods
# Method that will read and accept text components for torrent description
from utilities.custom_user_input import collect_custom_messages_from_user
# Method that will search for dupes in trackers.
from utilities.search_for_dupes import search_for_dupes_api
from utilities.utils_miscellaneous import *
from utilities.utils_translation import *
from utilities.utils_metadata import *
from utilities.utils_bdinfo import *
from utilities.utils_basic import *
from utilities.utils import *

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
validate_env_file(f'{working_folder}/config.env.sample')

# Used to correctly select json file
# the value in this dictionay must correspond to the file name of the site template
acronym_to_tracker = json.load(open(f'{working_folder}/parameters/tracker/acronyms.json'))

# the `prepare_tracker_api_keys_dict` prepares the api_keys_dict and also does mandatory property validations
api_keys_dict = prepare_and_validate_tracker_api_keys_dict(f'{working_folder}/parameters/tracker/api_keys.json')

# Import 'auto_mode' status
if str(os.getenv('auto_mode')).lower() not in ['true', 'false']:
    logging.error('[Main] `auto_mode` is not set to `true/false` in `config.env`. Defaulting to `false`')
auto_mode = str(os.getenv('auto_mode', 'false')).lower()

# import discord webhook url (if exists)
if len(os.getenv('DISCORD_WEBHOOK')) != 0:
    discord_url = str(os.getenv('DISCORD_WEBHOOK'))
else:
    discord_url = None

# BHD Live/Draft
is_live_on_site = str(os.getenv('live')).lower()

# Setup args
parser = argparse.ArgumentParser()

# Required Arguments [Mandatory]
required_args = parser.add_argument_group('Required Arguments')
required_args.add_argument('-p', '--path', nargs='*', required=True, help="Use this to provide path(s) to file/folder")

# Commonly used args:
common_args = parser.add_argument_group('Commonly Used Arguments')
common_args.add_argument('-t', '--trackers', nargs='*', help="Tracker(s) to upload to. Space-separates if multiple (no commas)")
common_args.add_argument('-a', '--all_trackers', action='store_true', help="Select all trackers that can be uploaded to")
common_args.add_argument('-tmdb', nargs=1, help="Use this to manually provide the TMDB ID")
common_args.add_argument('-imdb', nargs=1, help="Use this to manually provide the IMDB ID")
common_args.add_argument('-tvmaze', nargs=1, help="Use this to manually provide the TVmaze ID")
common_args.add_argument('-anon', action='store_true', help="Tf you want your upload to be anonymous (no other info needed, just input '-anon'")

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

uncommon_args.add_argument('-3d', action='store_true', help="Mark the upload as 3D content")
uncommon_args.add_argument('-foreign', action='store_true', help="Mark the upload as foreign content [Non-English]")

# args for Internal uploads
internal_args = parser.add_argument_group('Internal Upload Arguments')
internal_args.add_argument('-internal', action='store_true', help="(Internal) Used to mark an upload as 'Internal'")
internal_args.add_argument('-freeleech', action='store_true', help="(Internal) Used to give a new upload freeleech")
internal_args.add_argument('-featured', action='store_true', help="(Internal) feature a new upload")
internal_args.add_argument('-doubleup', action='store_true', help="(Internal) Give a new upload 'double up' status")
internal_args.add_argument('-tripleup', action='store_true', help="(Internal) Give a new upload 'triple up' status [XBTIT Exclusive]")
internal_args.add_argument('-sticky', action='store_true', help="(Internal) Pin the new upload")

args = parser.parse_args()


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
    return search_for_dupes_api(acronym_to_tracker[str(tracker).lower()], 
        imdb=torrent_info["imdb"], tmdb=torrent_info["tmdb"], tvmaze=torrent_info["tvmaze"], torrent_info=torrent_info, 
        tracker_api=temp_tracker_api_key, debug=args.debug, working_folder=working_folder, auto_mode=os.getenv('auto_mode'))


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
        raise AssertionError("Guessit could not even extract the title, something is really wrong with this filename.")

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

    if has_user_provided_type(args.type):
        torrent_info["type"] = torrent_info["type"] = 'episode' if args.type[0] == 'tv' else 'movie'
    else:
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
    if (torrent_info["release_group"] if "release_group" in torrent_info and len(torrent_info["release_group"]) > 0 else None ) is None :
        torrent_info["release_group"] = "NOGROUP"
        logging.debug(f"Release group could not be identified by guessit. Setting release group as NOGROUP")
    elif torrent_info["release_group"].startswith("X-"):
        # a special case where title ends with DTS-X-EPSILON and guess it extracts release group as X-EPSILON
        logging.info(f'Guessit identified release group as {torrent_info["release_group"]}. Since this starts with X- (probably from DTS-X-RELEASE_GROUP), overwriting release group as {torrent_info["release_group"][2:]}')
        torrent_info["release_group"] = torrent_info["release_group"][2:]
    

    if "type" not in torrent_info:
        raise AssertionError("'type' is not set in the guessit output, something is seriously wrong with this filename")

    # ------------ Format Season & Episode (Goal is 'S01E01' type format) ------------ #
    # Depending on if this is a tv show or movie we have some other 'required' keys that we need (season/episode)
    if torrent_info["type"] == "episode":  # guessit uses 'episode' for all tv related content (including seasons)
        s00e00, season_number, episode_number, complete_season, individual_episodes, daily_episodes = basic_get_episode_basic_details(guess_it_result)
        torrent_info["s00e00"] = s00e00
        torrent_info["season_number"] = season_number
        torrent_info["episode_number"] = episode_number
        torrent_info["complete_season"] = complete_season
        torrent_info["individual_episodes"] = individual_episodes
        torrent_info["daily_episodes"] = daily_episodes

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
            # validating presence of bdinfo script for bare metal
            bdinfo_validate_bdinfo_script_for_bare_metal(bdinfo_script)
            # validating presence of BDMV/STREAM/
            bdinfo_validate_presence_of_bdmv_stream(torrent_info["upload_media"])

            raw_video_file, largest_playlist = bdinfo_get_largest_playlist(bdinfo_script, auto_mode, torrent_info["upload_media"])

            torrent_info["raw_video_file"] = raw_video_file
            torrent_info["largest_playlist"] = largest_playlist
        else:
            raw_video_file = basic_get_raw_video_file(torrent_info['upload_media'])
            if raw_video_file is not None:
                torrent_info["raw_video_file"] = raw_video_file

        if 'raw_video_file' not in torrent_info:
            logging.critical(f"The folder {torrent_info['upload_media']} does not contain any video files")
            console.print(f"The folder {torrent_info['upload_media']} does not contain any video files\n\n", style='bold red')
            return "skip_to_next_file"

        torrent_info["raw_file_name"] = os.path.basename(os.path.dirname(f"{full_path}/"))  # this is used to isolate the folder name
    else:
        # For regular movies and single video files we can use the following the just get the filename
        torrent_info["raw_file_name"] = os.path.basename(full_path)  # this is used to isolate the file name

    
    #---------------------------------Full Disk BDInfo Parsing--------------------------------------#
    # if the upload is for a full disk, we parse the bdinfo to indentify more information before moving on to the existing logic.
    keys_we_need_but_missing_torrent_info_list = ['video_codec', 'audio_codec'] # for disc we don't need mediainfo
    if args.disc:
        bdinfo_start_time = time.perf_counter()
        logging.debug(f"Generating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}")
        console.print(f"\nGenerating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}\n", style='bold blue')
        torrent_info["mediainfo"] = f'{working_folder}/temp_upload/mediainfo.txt'
        torrent_info["bdinfo"] = bdinfo_generate_and_parse_bdinfo(bdinfo_script, working_folder, torrent_info, args.debug) # TODO handle non-happy paths
        logging.debug(f"::::::::::::::::::::::::::::: Parsed BDInfo output :::::::::::::::::::::::::::::")
        logging.debug(f"\n{pformat(torrent_info['bdinfo'])}")
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
    media_info_result = basic_get_mediainfo(parse_me)
    
    if args.disc:
        # for full disk uploads the bdinfo summary itself will be set as the `mediainfo_summary`
        logging.info("[Main] Full Disk Upload. Setting bdinfo summary as mediainfo summary")
        with open(f'{working_folder}/temp_upload/mediainfo.txt', 'r') as summary:
            bdInfo_summary = summary.read()
            torrent_info["mediainfo_summary"] = bdInfo_summary
    else:
        # certain release groups will add IMDB, TMDB and TVDB id in the general section of mediainfo. If one such id is present then we can use it and 
        # consider it the same as being provided by the user (no need to search)
        # PS: We don't use the tvdb id obtained here. (Might be deprecated)
        mediainfo_summary, tmdb, imdb, tvdb = basic_get_mediainfo_summary(media_info_result.to_data())
        torrent_info["mediainfo_summary"] = mediainfo_summary
        if tmdb != "0":
            tmdb = tmdb[tmdb.find("/") + 1:] if tmdb.find("/") >= 0 else tmdb # we will get movie/12345 or tv/12345 => we only need 12345 part.
            args.tmdb = [tmdb]
            logging.info(f"[Main] Obtained TMDB Id from mediainfo summary. Proceeding with {args.tmdb}")
        if imdb != "0":
            args.imdb = [imdb]
            logging.info(f"[Main] Obtained IMDB Id from mediainfo summary. Proceeding with {args.imdb}")

    #  Now we'll try to use regex, mediainfo, ffprobe etc to try and auto get that required info
    for missing_val in keys_we_need_but_missing_torrent_info:
        # Save the analyze_video_file() return result into the 'torrent_info' dict
        torrent_info[missing_val] = analyze_video_file(missing_value=missing_val, media_info=media_info_result)

    logging.debug("::::::::::::::::::::::::::::: Torrent Information collected so far :::::::::::::::::::::::::::::")
    logging.debug(f"\n{pformat(torrent_info)}")
    # Show the user what we identified so far
    columns_we_want = {
        'type': 'Type', 
        'title': 'Title',
        's00e00': f'{("Season" if len(torrent_info["s00e00"]) == 3 else "Episode") if "s00e00" in torrent_info else ""}',
        'year': f'{"Year" if "year" in torrent_info and torrent_info["type"] == "movie" else ""}',
        'source': 'Source', 
        'screen_size': 'Resolution', 
        'video_codec': 'Video Codec',
        'hdr': f'{"HDR Format" if "hdr" in torrent_info else ""}',
        'dv': f'{"Dolby Vision" if "dv" in torrent_info else ""}',
        'audio_codec': 'Audio Codec', 
        'audio_channels': 'Audio Channels',
        'atmos': f'{"Dolby Atmos" if "atmos" in torrent_info else ""}',
        'release_group': f'{"Release Group" if "release_group" in torrent_info else ""}'
    }
    logging.debug(f"The columns that we want to show are {columns_we_want}")
    presentable_type = 'Movie' if torrent_info["type"] == 'movie' else 'TV Show'

    codec_result_table = Table(box=box.SQUARE, title='Basic media summary', title_style='bold #be58bf')

    for column_display_value in columns_we_want.values():
        if len(column_display_value) != 0:
            logging.debug(f"Adding column {column_display_value} to the torrent details result table")
            codec_result_table.add_column(f"{column_display_value}", justify='center', style='#38ACEC')

    basic_info = []
    # add the actual data now
    for column_query_key, column_display_value in columns_we_want.items():
        if len(column_display_value) != 0:
            torrent_info_key_failsafe = (torrent_info[column_query_key] if column_query_key != 'type' else presentable_type) if column_query_key in torrent_info else None
            logging.debug(f"Getting value for {column_query_key} with display {column_display_value} as {torrent_info_key_failsafe} for the torrent details result table")
            basic_info.append(torrent_info_key_failsafe)

    codec_result_table.add_row(*basic_info)

    console.line(count=2)
    console.print(codec_result_table, justify='center')
    console.line(count=1)


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
        return basic_get_missing_mediainfo(torrent_info, parse_me, working_folder)

    # ------------------- Source ------------------- #
    if missing_value == "source":
        source, source_type = basic_get_missing_source(torrent_info, args.disc, auto_mode, missing_value)
        torrent_info["source"] = source
        torrent_info["source_type"] = source_type
        return source

    # ---------------- Video Resolution ---------------- #
    if missing_value == "screen_size":
        return basic_get_missing_screen_size(torrent_info, args.disc, media_info_video_track, auto_mode, missing_value)

    # ---------------- Audio Channels ---------------- #
    if missing_value == "audio_channels":
        return basic_get_missing_audio_channels(torrent_info, args.disc, auto_mode, parse_me, media_info_audio_track, missing_value)
    
    # ---------------- Audio Codec ---------------- #
    if missing_value == "audio_codec":
        audio_codec, atmos =  basic_get_missing_audio_codec(torrent_info=torrent_info, is_disc=args.disc, auto_mode=auto_mode, 
            audio_codec_file_path=f'{working_folder}/parameters/audio_codecs.json',
            media_info_audio_track=media_info_audio_track, parse_me=parse_me,
            missing_value=missing_value)
        
        if atmos is not None:
            torrent_info["atmos"] = atmos
        if audio_codec is not None:
            return audio_codec

    # ---------------- Video Codec ---------------- #
    # I'm pretty confident that a video_codec will be selected automatically each time, unless mediainfo fails catastrophically we should always
    # have a codec we can return. User input isn't needed here
    if missing_value == "video_codec":
        dv, hdr, video_codec = basic_get_missing_video_codec(torrent_info=torrent_info,
            is_disc=args.disc, auto_mode=auto_mode,
            media_info_video_track=media_info_video_track, force_pymediainfo=args.force_pymediainfo
        )
        if dv is not None:
            torrent_info["dv"] = dv
        if hdr is not None:
            torrent_info["hdr"] = hdr
        return video_codec


def identify_miscellaneous_details(guess_it_result):
    """
        This function is dedicated to analyzing the filename and extracting snippets such as "repack, "DV", "AMZN", etc
        Depending on what the "source" is we might need to search for a "web source" (amzn, nf, hulu, etc)
        
        We also search for "editions" here, this info is typically made known in the filename so we can use some simple regex to extract it 
        (e.g. extended, Criterion, directors, etc)
    """
    logging.debug(f'[MiscellaneousDetails] Trying to identify miscellaneous details for torrent.')
    # ------ Specific Source info ------ #
    if "source_type" not in torrent_info:
        torrent_info["source_type"] = miscellaneous_identify_source_type(torrent_info["raw_file_name"], auto_mode, torrent_info["source"])

    # ------ WEB streaming service stuff here ------ #
    if torrent_info["source"] == "Web":
        # TODO check whether None needs to be set as `web_source`
        torrent_info["web_source"] = miscellaneous_identify_web_streaming_source(f'{working_folder}/parameters/streaming_services.json', torrent_info["raw_file_name"], guess_it_result)


    # --- Custom & extra info --- #
    # some torrents have 'extra' info in the title like 'repack', 'DV', 'UHD', 'Atmos', 'remux', etc
    # We simply use regex for this and will add any matches to the dict 'torrent_info', later when building the final title we add any matches (if they exist) into the title

    # repacks
    torrent_info["repack"] = miscellaneous_identify_repacks(torrent_info["raw_file_name"])

    # --- Bluray disc type --- #
    if torrent_info["source_type"] == "bluray_disc":
        torrent_info["bluray_disc_type"] = miscellaneous_identify_bluray_disc_type(torrent_info["screen_size"], torrent_info["upload_media"])

    # Bluray disc regions
    # Regions are read from new json file
    bluray_regions = json.load(open(f'{working_folder}/parameters/bluray_regions.json'))

    # Try to split the torrent title and match a few key words
    # End user can add their own 'key_words' that they might want to extract and add to the final torrent title
    key_words = {'remux': 'REMUX', 'hdr': torrent_info.get("hdr", "HDR"),  'uhd': 'UHD', 'hybrid': 'Hybrid', 'atmos': 'Atmos', 'ddpa' : 'Atmos'}
    
    hdr_hybrid_remux_keyword_search = str(torrent_info["raw_file_name"]).replace(" ", ".").replace("-", ".").split(".")

    for word in hdr_hybrid_remux_keyword_search:
        if str(word).lower() in key_words.keys():
            logging.info(f"extracted the key_word: {word.lower()} from the filename")
            if str(word).lower() == 'ddpa': # special case. TODO find a way to generalize and handle this
                torrent_info["atmos"] = key_words[str(word).lower()]
            else:
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
    torrent_info["edition"] = miscellaneous_identify_bluray_edition(torrent_info["upload_media"])

    # --------- Fix scene group tags --------- #
    # Whilst most scene group names are just capitalized but occasionally as you can see ^^ some are not (e.g. KOGi)
    # either way we don't want to be capitalizing everything (e.g. we want 'NTb' not 'NTB') so we still need a dict of scene groups and their proper capitalization
    if "release_group" in torrent_info:
        torrent_info["scene"], torrent_info["release_group"] = miscellaneous_perform_scene_group_capitalization(f'{working_folder}/parameters/scene_groups.json', torrent_info["release_group"])

    # --------- SD? --------- #
    res = re.sub("[^0-9]", "", torrent_info["screen_size"])
    if int(res) < 720:
        torrent_info["sd"] = 1


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
                if "uhd" in torrent_info:
                    torrent_info["source"] = f"{torrent_info['uhd']} Blu-ray"
                else:
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
        separator = json_config["title_separator"] or " "

        temp_load_torrent_info = tracker_torrent_name_style.replace("{", "").replace("}", "").split(" ")
        for item in temp_load_torrent_info:
            # Here is were we actual get the torrent_info response and add it to the "generate_format_string" dict we declared earlier
            generate_format_string[item] = torrent_info[item].replace(" ", separator) if item in torrent_info and torrent_info[item] is not None else ""

        formatted_title = ""  # This is the final torrent title, we add any info we get from "torrent_info" to it using the "for loop" below
        for key, value in generate_format_string.items():
            # ignore no matches (e.g. most TV Shows don't have the "year" added to its title so unless it was directly specified in the filename we also ignore it)
            if len(value) != 0:  
                formatted_title = f'{formatted_title}{"-" if key == "release_group" else separator}{value}'

        # Custom title translations specific to tracker
        # Certain terms might not be allowed in certain trackers. Such terms are configured in a separate config in the tracker template.
        # Eg: DD+ might not be allowed in certain trackers. Instead they'll use DDP
        # These translations are then applied here.
        if "torrent_title_translation" in json_config:
            torrent_title_translation = json_config["torrent_title_translation"]
            logging.info(f"Going to apply title translations to generated title: {formatted_title}")
            for key, val in torrent_title_translation.items():
                formatted_title = formatted_title.replace(key, val)

        logging.info(f"[Main] Torrent title after formatting and translations: {formatted_title}")
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


# ---------------------------------------------------------------------- #
#                  Set correct tracker API Key/Values                    #
# ---------------------------------------------------------------------- #
def choose_right_tracker_keys():
    required_items = config["Required"]
    optional_items = config["Optional"]

    # BLU requires the IMDB with the "tt" removed so we do that here, BHD will automatically put the "tt" back in... so we don't need to make an exception for that
    if "imdb" in torrent_info:
        torrent_info["imdb_with_tt"] = torrent_info["imdb"]
        if len(torrent_info["imdb"]) >= 2:
            if str(torrent_info["imdb"]).startswith("tt"):
                torrent_info["imdb"] = str(torrent_info["imdb"]).replace("tt", "")
            else:
                torrent_info["imdb_with_tt"] = f'tt{torrent_info["imdb"]}'
        else:
            torrent_info["imdb"] = "0"
            torrent_info["imdb_with_tt"] = "0"

    # torrent title
    tracker_settings[config["translation"]["torrent_title"]] = torrent_info["torrent_title"]

    # Save a few key values in a list that we'll use later to identify the resolution and type
    relevant_torrent_info_values = []
    for torrent_info_k in torrent_info:
        if torrent_info_k in ["source_type", "screen_size", "bluray_disc_type"]:
            relevant_torrent_info_values.append(torrent_info[torrent_info_k])
        
    logging.debug(f'The relevant torrent info values for resolution / source identification are {relevant_torrent_info_values}')

    # Filling in data for all the keys that have mapping/translations
    # Here we iterate over the translation mapping and for each translation key, we check the required and optional items for that value
    # once identified we handle it
    logging.info(f"[Main] Starting translations from torrent info to tracker settings.")
    is_hybrid_translation_needed = False

    for translation_key, translation_value in config["translation"].items():
        logging.debug(f"[Main] Trying to translate {translation_key} to {translation_value}")

        # ------------ required_items start ------------
        for required_key, required_value in required_items.items():
            # get the proper mapping, the elements that doesn't match can be ignored
            if str(required_key) == str(translation_value):
                logging.debug(f"[Main] Key {translation_key} mapped to required item {required_key} with value type as {required_value}")
                
                # the torrent file is always submitted as a file
                if required_value in ( "file", "file|base64", "file|array", "file|string|array"):
                    # adding support for base64 encoded files
                    # the actual encoding will be performed in `upload_to_site` method
                    if translation_key in torrent_info:
                        tracker_settings[config["translation"][translation_key]] = torrent_info[translation_key]
                    # Make sure you select the right .torrent file
                    if translation_key == "dot_torrent":
                        tracker_settings[config["translation"]["dot_torrent"]] = f'{working_folder}/temp_upload/{tracker}-{torrent_info["torrent_title"]}.torrent'
                
                # The reason why we keep this elif statement here is because the conditional right above is also technically a "string"
                # but its easier to keep mediainfo and description in text files until we need them so we have that small exception for them
                elif required_value == "string":
                    # BHD requires the key "live" (0 = Sent to drafts and 1 = Live on site)
                    if required_key == "live":
                        live = '1' if is_live_on_site == 'true' else '0'
                        logging.info(f"Upload live status: {'Live (Visible)' if is_live_on_site == 'true' else 'Draft (Hidden)'}")
                        tracker_settings[config["translation"][translation_key]] = live

                    # If the user supplied the "-anon" argument then we want to pass that along when uploading
                    elif translation_key == "anon" and args.anon:
                        logging.info("Uploading anonymously")
                        tracker_settings[config["translation"][translation_key]] = "1"

                    # Adding support for internal args
                    elif translation_key in ['doubleup', 'featured', 'freeleech', 'internal', 'sticky', 'tripleup', 'foreign', "3d"]:
                        tracker_settings[config["translation"][translation_key]] = "1" if getattr(args, translation_key) is True else "0"
                    
                    # We dump all the info from torrent_info in tracker_settings here
                    elif translation_key in torrent_info:
                        tracker_settings[config["translation"][translation_key]] = torrent_info[translation_key]
                    # This work as a sort of 'catch all', if we don't have the correct data in torrent_info, we just send a 0 so we can successfully post
                    else:
                        tracker_settings[config["translation"][translation_key]] = "0"

                elif required_value == "url":
                    # URLs can be set only to for certain media databases
                    url = tracker_settings[config["translation"][translation_key]] if config["translation"][translation_key] in tracker_settings else ""
                    if translation_key == "imdb":
                        url = f"https://www.imdb.com/title/{torrent_info['imdb_with_tt']}"
                    elif translation_key == "tmdb":
                        url = f"https://www.themoviedb.org/{'movie' if torrent_info['type'] == 'movie' else 'tv'}/{torrent_info['tmdb']}"
                    elif translation_key == "tvdb":
                        url = f"https://www.thetvdb.com/?tab=series&id={torrent_info['tvdb']}"
                    elif translation_key == "mal":
                        url = f"https://myanimelist.net/anime/{torrent_info['mal']}"
                    # This and condition is a patch for BIT-HDTV. For this tracker both imdb and tvmaze needs to be mapped to same key url, 
                    # depending on the type of the upload. For movies, it need to be imdb url, and for tv it needs to be tvmaze url.
                    # TODO check whether a much cleaner approach can be used here  
                    elif translation_key == "tvmaze" and torrent_info["type"] == "episode": 
                        url = f"https://www.tvmaze.com/shows/{torrent_info['tvmaze']}"
                    else:
                        logging.error(f"[Main] Invalid key for url translation provided -- Key {translation_key}")
                    tracker_settings[config["translation"][translation_key]] = url

                else:
                    logging.error(f"[Main] Invalid value type {required_value} configured for required item {required_key} with translation key {required_key}")
                
                # Set the category ID, this could be easily hardcoded in (1=movie & 2=tv) but I chose to use JSON data just in case a future tracker switches this up
                if translation_key == "type":
                    for key_cat, val_cat in config["Required"][required_key].items():
                        if torrent_info["type"] == val_cat:
                            tracker_settings[config["translation"][translation_key]] = key_cat
                        elif val_cat in torrent_info and torrent_info[val_cat] == "1":
                            # special case whether we can check for certain values in torrent info to decide the type
                            # eg: complete_season, individual_episodes etc
                            tracker_settings[config["translation"][translation_key]] = key_cat
                    
                    if config["translation"][translation_key] not in tracker_settings:
                        # this type of upload is not permitted in this tracker
                        logging.critical('[CategoryMapping] Unable to find a suitable "category/type" match for this file')
                        logging.error("[CategoryMapping] Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip to BLU is not allowed")
                        console.print(f'\nThis "Category" ([bold]{torrent_info["type"]}[/bold]) is not allowed on this tracker', style='Red underline', highlight=False)
                        return "STOP"

                if translation_key in ('source', 'resolution'):
                    return_value = identify_resolution_source(target_val=translation_key, config=config, relevant_torrent_info_values=relevant_torrent_info_values)
                    if return_value == "STOP":
                        return return_value
                    tracker_settings[config["translation"][translation_key]] = return_value

                if translation_key == "hybrid_type" and config["hybrid_type"] is not None and config["hybrid_type"]["required"]:
                    # to do hybrid translation we need values for source, type and resolution to be resolved before hand.
                    # we first check whether they have been resolved or not. 
                    # If those values have been resolved then we can just call the `get_hybrid_type` to resolve it.
                    # otherwise we mark the present of this hybrid type and do the mapping after all required and optional 
                    # value mapping have been completed.
                    if config["translation"]["source"] in tracker_settings and config["translation"]["resolution"] in tracker_settings and config["translation"]["type"] in tracker_settings:
                        tracker_settings[config["translation"][translation_key]] = get_hybrid_type(target_val=translation_key,
                            tracker_settings=tracker_settings, config=config, exit_program=True, torrent_info=torrent_info)
                        is_hybrid_translation_needed = False
                    else:
                        is_hybrid_translation_needed = True
        # ------------ required_items end ------------

        # ------------ optional_items start ------------
        # This mainly applies to BHD since they are the tracker with the most 'Optional' fields, 
        # BLU/ACM only have 'nfo_file' as an optional item which we take care of later
        for optional_key, optional_value in optional_items.items():
            if str(optional_key) == str(translation_value):
                logging.debug(f"[Main] Key {translation_key} mapped to optional item {optional_key} with value type as {optional_value}")
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
                elif optional_key == 'region' and 'region' in torrent_info:
                    # This will only run if you are uploading a bluray_disc
                    for region in optional_value:
                        if str(region).upper() == str(torrent_info["region"]).upper():
                            tracker_settings[optional_key] = region
                            break

                # -!-!- Tags -!-!- #
                elif optional_key == 'tags':  # (Only supported on BHD)
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

                elif optional_key == 'sd' and "sd" in torrent_info:
                    tracker_settings[optional_key] = 1
                
                # checking whether the optional key is for mediainfo or bdinfo
                # TODO make changes to save bdinfo to bdinfo and move the existing bdinfo metadata to someother key
                # for full disks the bdInfo is saved under the same key as mediainfo
                elif translation_key == "mediainfo":
                    logging.debug(f"Identified {optional_key} for tracker with {'FullDisk' if args.disc else 'File/Folder'} upload")
                    if args.disc:
                        logging.debug("Skipping mediainfo for tracker settings since upload is FullDisk.")
                    else:
                        logging.debug(f"Setting mediainfo from torrent_info to tracker_settings for optional_key {optional_key}")
                        tracker_settings[optional_key] = torrent_info.get("mediainfo", "0")
                        continue
                elif translation_key == "bdinfo":
                    logging.debug(f"Identified {optional_key} for tracker with {'FullDisk' if args.disc else 'File/Folder'} upload")
                    if args.disc:
                        logging.debug(f"Setting mediainfo from torrent_info to tracker_settings for optional_key {optional_key}")
                        tracker_settings[optional_key] = torrent_info.get("mediainfo", "0")
                        continue
                    else:
                        logging.debug("Skipping bdinfo for tracker settings since upload is NOT FullDisk.")
                else:
                    tracker_settings[optional_key] = torrent_info.get(translation_key, "")
        # ------------ optional_items end ------------

    # Adding default values from template to tracker settings
    for default_key, default_value in config["Default"].items():
        logging.debug(f'Adding default key `{default_key}` with value `{default_value}` to tracker settings')
        tracker_settings[default_key] = default_value

    # at this point we have finished iterating over the translation key items
    if is_hybrid_translation_needed:
        tracker_settings[config["translation"]["hybrid_type"]] = get_hybrid_type(target_val="hybrid_type",
            tracker_settings=tracker_settings, config=config, exit_program=False, torrent_info=torrent_info)


# ---------------------------------------------------------------------- #
#                             Upload that shit!                          #
# ---------------------------------------------------------------------- #
def upload_to_site(upload_to, tracker_api_key):
    logging.info("[TrackerUpload] Attempting to upload to: {}".format(upload_to))
    url = str(config["upload_form"]).format(api_key=tracker_api_key)
    url_masked = str(config["upload_form"]).format(api_key="REDACTED")
    payload = {}
    files = []
    display_files = {}

    logging.debug("::::::::::::::::::::::::::::: Tracker settings that will be used for creating payload :::::::::::::::::::::::::::::")
    logging.debug(f'\n{pformat(tracker_settings)}')

    # multiple authentication modes
    headers = None
    if config["technical_jargons"]["authentication_mode"] == "API_KEY":
        pass # headers = None
    elif config["technical_jargons"]["authentication_mode"] == "API_KEY_PAYLOAD":
        # api key needs to be added in payload. the key in payload for api key can be obtained from `auth_payload_key`
        payload[config["technical_jargons"]["auth_payload_key"]] = tracker_api_key
    elif config["technical_jargons"]["authentication_mode"] == "BEARER":
        headers = {'Authorization': f'Bearer {tracker_api_key}'}
        logging.info(f"[TrackerUpload] Using Bearer Token authentication method for tracker {upload_to}")
    elif config["technical_jargons"]["authentication_mode"] == "HEADER":
        if len(config["technical_jargons"]["header_key"]) > 0:
            headers = {config["technical_jargons"]["header_key"]: tracker_api_key}
            logging.info(f"[DupeCheck] Using Header based authentication method for tracker {upload_to}")
        else:
            logging.fatal(f'[DupeCheck] Header based authentication cannot be done without `header_key` for tracker {upload_to}.')
    # TODO add support for cookie based authentication
    elif config["technical_jargons"]["authentication_mode"] == "COOKIE":
        logging.fatal(f'[TrackerUpload] Cookie based authentication is not supported as for now.')

    for key, val in tracker_settings.items():
        # First check to see if its a required or optional key
        req_opt = 'Required' if key in config["Required"] else 'Optional' if key in config["Optional"] else "Default"

        # Now that we know if we are looking for a required or optional key we can try to add it into the payload
        if str(config[req_opt][key]) == "file":
            if os.path.isfile(tracker_settings[key]):
                post_file = f'{key}', open(tracker_settings[key], 'rb')
                files.append(post_file)
                display_files[key] = tracker_settings[key]
            else:
                logging.critical(f"[TrackerUpload] The file/path `{tracker_settings[key]}` for key {req_opt} does not exist!")
                continue
        elif str(config[req_opt][key]) == "file|array":
            if os.path.isfile(tracker_settings[key]):
                with open(tracker_settings[key], "r") as images_data:
                    for line in images_data.readlines():
                        post_file = f'{key}[]', open(line.strip(), 'rb') 
                        files.append(post_file)
                        display_files[key] = tracker_settings[key]
            else:
                logging.critical(f"[TrackerUpload] The file/path `{tracker_settings[key]}` for key {req_opt} does not exist!")
                continue
        elif str(config[req_opt][key]) == "file|string|array":
            """
                for file|array we read the contents of the file line by line, where each line becomes and element of the array or list
            """
            if os.path.isfile(tracker_settings[key]):
                logging.debug(f"[TrackerUpload] Setting file {tracker_settings[key]} as string array for key {key}")
                with open(tracker_settings[key], 'r') as file_contents:
                    screenshot_array = []
                    for line in file_contents.readlines():
                        screenshot_array.append(line.strip())
                    payload[f'{key}[]' if config["technical_jargons"]["payload_type"] == "MULTI-PART" else key] = screenshot_array
                    logging.debug(f"[TrackerUpload] String array data for key {key} :: {screenshot_array}")
            else:
                logging.critical(f"[TrackerUpload] The file/path `{tracker_settings[key]}` for key {req_opt} does not exist!")
                continue
        elif str(config[req_opt][key]) == "file|base64":
            # file encoded as base64 string
            if os.path.isfile(tracker_settings[key]):
                logging.debug(f"[TrackerUpload] Setting file|base64 for key {key}")
                with open(tracker_settings[key], 'rb') as binary_file:
                    binary_file_data = binary_file.read()
                    base64_encoded_data = base64.b64encode(binary_file_data)
                    base64_message = base64_encoded_data.decode('utf-8')
                    payload[key] = base64_message
            else:
                logging.critical(f"[TrackerUpload] The file/path `{tracker_settings[key]}` for key {req_opt} does not exist!")
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
                logging.info(f"[TrackerUpload] Optional key {key} will be added to payload")
            payload[key] = val

    if auto_mode == "false":
        # prompt the user to verify everything looks OK before uploading

        # ------- Show the user a table of the API KEY/VAL (TEXT) that we are about to send ------- #
        review_upload_settings_text_table = Table(title=f"\n\n\n\n[bold][deep_pink1]{upload_to} Upload data (Text):[/bold][/deep_pink1]", 
            show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim", show_lines=True)

        review_upload_settings_text_table.add_column("Key", justify="left")
        review_upload_settings_text_table.add_column("Value (TEXT)", justify="left")
        # Insert the data into the table, raw data (no paths)
        for payload_k, payload_v in sorted(payload.items()):
            # Add torrent_info data to each row
            review_upload_settings_text_table.add_row(f"[deep_pink1]{payload_k}[/deep_pink1]", f"[dodger_blue1]{payload_v}[/dodger_blue1]")
        console.print(review_upload_settings_text_table, justify="center")

        if len(display_files.items()) != 0:
            # Displaying FILES data if present
            # ------- Show the user a table of the API KEY/VAL (FILE) that we are about to send ------- #
            review_upload_settings_files_table = Table(title=f"\n\n\n\n[bold][green3]{upload_to} Upload data (FILES):[/green3][/bold]", 
                show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim", show_lines=True)

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
            logging.error(f"[TrackerUpload] User chose to cancel the upload to {tracker}")
            return

    logging.fatal("[TrackerUpload] URL: {url} \n Data: {data} \n Files: {files}".format(url=url_masked, data=payload, files=files))

    response = None
    if config["technical_jargons"]["payload_type"] == "JSON":
        response = requests.request("POST", url, json=payload, files=files, headers=headers)
    else:
        response = requests.request("POST", url, data=payload, files=files, headers=headers)
    
    logging.info(f"[TrackerUpload] POST Request: {url}")
    logging.info(f"[TrackerUpload] Response code: {response.status_code}")

    console.print(f'\nSite response: [blue]{response.text}[/blue]')
    logging.info(f'[TrackerUpload] {response.text}')

    if response.status_code in (200, 201):
        logging.info(f"[TrackerUpload] Upload response for {upload_to}: {response.text.encode('utf8')}")
        # Update discord channel
        if discord_url:
            requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f"content=Upload response: **{response.text.encode('utf8')}**")
        
        if "success" in response.json():
            if str(response.json()["success"]).lower() == "true":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
        elif "status" in response.json():
            if str(response.json()["status"]).lower() == "true" or str(response.json()["status"]).lower() == "success":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
        elif "success" in str(response.json()).lower():
            if str(response.json()["success"]).lower() == "true":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
        elif "status" in str(response.json()).lower():
            if str(response.json()["status"]).lower() == "true":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
        else:
            console.print('Upload to tracker failed.', style='bold red')
            logging.critical("[TrackerUpload] Something really went wrong when uploading to {} and we didn't even get a 'success' json key".format(upload_to))
    
    elif response.status_code == 404:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print('Upload failed', style='bold red')
        logging.critical(f"[TrackerUpload] 404 was returned on that upload, this is a problem with the site ({tracker})")
        logging.error("[TrackerUpload] Upload failed")

    elif response.status_code == 500:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The upload might have [red]failed[/], the site isn't returning the uploads status")
        # This is to deal with the 500 internal server error responses BLU has been recently returning
        logging.error(f"[TrackerUpload] HTTP response status code '{response.status_code}' was returned (500=Internal Server Error)")
        logging.info("[TrackerUpload] This doesn't mean the upload failed, instead the site simply isn't returning the upload status")

    elif response.status_code == 400:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print('Upload failed.', style='bold red')
        try:
            logging.critical(f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({tracker}). Error: Error {response.json()["error"] if "error" in response.json() else response.json()}')
        except:
            logging.critical(f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({tracker}).')
        logging.error("[TrackerUpload] Upload failed")

    else:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The status code isn't [green]200[/green] so something failed, upload may have failed")
        logging.error('[TrackerUpload] Status code is not 200, upload might have failed')


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#  **START** This is the first code that executes when we run the script, we log that info and we start a timer so we can keep track of total script runtime **START** #
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#
script_start_time = time.perf_counter()
starting_new_upload = f" {'-' * 24} Starting new upload {'-' * 24} "

logging.info(starting_new_upload)

if args.tripleup and args.doubleup:
    logging.error("[Main] User tried to pass tripleup and doubleup together. Stopping torrent upload process")
    console.print("You can not use the arg [deep_sky_blue1]-doubleup[/deep_sky_blue1] and [deep_sky_blue1]-tripleup[/deep_sky_blue1] together. Only one can be used at a time\n", style='bright_red')
    console.print("Exiting...\n", style='bright_red bold')
    sys.exit()

if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("torf").setLevel(logging.INFO)
    logging.getLogger("rebulk.rules").setLevel(logging.INFO)
    logging.getLogger("rebulk.rebulk").setLevel(logging.INFO)
    logging.getLogger("rebulk.processors").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.debug(f"Arguments provided by user: {args}")

"""
----------------------- Full Disk & BDInfo CLI Related Notes -----------------------
There is no way to use the `bdinfo_script` to create a bdinfocli docker container implementation inside a 
docker container unless docker in docker support with the docker socket / docker socket proxy is implemented. 
 
The docker socket approach is not considered due to the security risks associated with it.
Hence BDInfo usage inside container is prohibited by default.

To allow users to do Full Disks upload with the containeized approach a special docker image is provide that has bdinfo already packed inside.
This image has the env properties `IS_CONTAINERIZED` and `IS_FULL_DISK_SUPPORTED` set as `true`
Also this container has an alias `bdinfocli` that can be used to invoke the bdinfo utility.

If the above mentioned envs are true, we override the user configured `bdinfo_script` to the alias `bdinfocli`

Similarly, from inside the normal full disk un-supported images, if user tries to upload a Full Disk,
we stop upload process immediately with an error message.
"""
bdinfo_script = os.getenv('bdinfo_script')
if os.getenv("IS_CONTAINERIZED") == "true" and os.getenv("IS_FULL_DISK_SUPPORTED") == "true":
    logging.info("[Main] Full disk is supported inside this container. Setting overriding configured `bdinfo_script` to use alias `bdinfocli`")
    bdinfo_script = "bdinfocli"

if args.disc and os.getenv("IS_CONTAINERIZED") == "true" and not os.getenv("IS_FULL_DISK_SUPPORTED") == "true":
    logging.fatal("[Main] User tried to upload Full Disk from an unsupported image!. Stopping upload process.")
    console.print("\n[bold red on white] ---------------------------- :warning: Unsupported Operation :warning: ---------------------------- [/bold red on white]")
    console.print("You're trying to upload a [bold red]Full Disk[/bold red] to trackers.",  highlight=False)
    console.print("Full disk uploads are [bold red]NOT PERMITTED[/bold red] in this image.", highlight=False)
    console.print("If you wish to upload Full disks please consider the following")
    console.print("1. Run me on a bare metal or VM following the steps mentioned with bdinfo_script property in wiki")
    console.print("2. Use a FAT variant of my image that supports Full Disk Uploads [Recommended]")
    console.print("[bold red on white] ---------------------------- :warning: Unsupported Operation :warning: ---------------------------- [/bold red on white]")
    sys.exit(console.print("\nQuiting upload process since Full Disk uploads are not allowed in this image.\n", style="bold red", highlight=False))

# Set the value of args.path to a variable that we can overwrite with a path translation later (if needed)
user_supplied_paths = args.path

# Verify the script is in "auto_mode" and if needed map rtorrent download path to system path
if args.reupload:
    logging.info('[Main] Reuploading a match from autodl')

    # Firstly remove the underscore separator from the trackers the user provided in the autodl filter & make replace args.trackers with it
    args.trackers = str(args.trackers[0]).split('_')

    # set auto_mode equal to True for this upload (if its not already)
    # since we are reuploading autodl matches its probably safe to say this is all automated & no one will be available to approve or interact with any prompt
    if auto_mode == 'false':
        logging.info('[Main] Temporarily switching "auto_mode" to "true" for this autodl reupload')
        auto_mode = 'true'

    if str(os.getenv('translation_needed')).lower() == 'true':
        # Currently it is only possible for 1 path to be based from autodl but just in case & for futureproofing we will treat it as a list of multiple paths
        logging.info('[Main] Translating paths... ("translation_needed" flag set to True in config.env) ')

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
            logging.info(f'[Main] rtorrent path: {path}')
            logging.info(f'[Main] Translated path: {translated_path}')

# If a user has supplied a discord webhook URL we can send updates to that channel
if discord_url:
    requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content={starting_new_upload}')

# Verify we support the tracker specified
logging.debug(f"[Main] Trackers provided by user {args.trackers}")
upload_to_trackers = get_and_validate_configured_trackers(args.trackers, args.all_trackers, api_keys_dict, acronym_to_tracker.keys())

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
        logging.info("[Main] User canceled upload when asked to confirm sites to upload to")
        sys.exit(console.print("\nOK, quitting now..\n", style="bold red", highlight=False))

# The user has confirmed what sites to upload to at this point (or auto_mode is set to true)
# Get media file details now, check to see if we are running in "batch mode"

# TODO an issue with batch mode currently is that we have a lot of "assert" & sys.exit statements during the prep work we do for each upload, if one of these "assert/quit" statements
#  get triggered, then it will quit the entire script instead of just moving on to the next file in the list 'upload_queue'

# ---------- Batch mode prep ---------- #
if args.batch:
    if len(args.path) > 1:
        logging.critical("[Main] The arg '-batch' can not be run with multiple '-path' args")
        logging.info("[Main] The arg '-batch' should be used to upload all the files in 1 folder that you specify with the '-path' arg")
        console.print("You can not use the arg [deep_sky_blue1]-batch[/deep_sky_blue1] while supplying multiple [deep_sky_blue1]-path[/deep_sky_blue1] args\n", style='bright_red')
        console.print("Exiting...\n", style='bright_red bold')
        sys.exit()
    elif not os.path.isdir(args.path[0]):
        # Since args.path is required now, we don't need to check if len(args.path) == 0 since that's impossible
        # instead we check to see if its a folder, if not then
        logging.critical("[Main]  The arg '-batch' can not be run an a single video file")
        logging.info("[Main]  The arg '-batch' should be used to upload all the files in 1 folder that you specify with the '-path' arg")
        console.print("We can not [deep_sky_blue1]-batch[/deep_sky_blue1] upload a single video file, [deep_sky_blue1]-batch[/deep_sky_blue1] is supposed to be used on a "
            "single folder containing multiple files you want to individually upload\n", style='bright_red')
        console.print("Exiting...\n", style='bright_red bold')
        sys.exit()


# all files we upload (even if its 1) get added to this list
upload_queue = []

if args.batch:
    logging.info("[Main] Running in batch mode")
    logging.info(f"[Main] Uploading all the items in the folder: {args.path}")
    # # This should be OK to upload, we've caught all the obvious issues above ^^ so if this is able to run we should be alright
    # for arg_file in glob.glob(f'{args.path[0]}/*'):
    #     # Since we are in batch mode, we upload every file/folder we find in the path the user specified
    #     upload_queue.append(arg_file)  # append each item to the list 'upload_queue' now
    # logging.debug(f'[Main] Upload queue for batch mode {upload_queue}')
    dirlist = [args.path[0]]
    for (dirpath, dirnames, filenames) in os.walk(dirlist.pop()):
        dirlist.extend(dirnames)
        # if filenames.endsWith(".mkv") or filenames.endsWith(".mp4"):
        upload_queue.extend(
            filter(lambda file_name: file_name.endswith(".mkv") or file_name.endswith(".mp4"), 
                map(lambda path_and_file: os.path.join(*path_and_file), zip([dirpath] * len(filenames), filenames))))
    logging.info(f'[Main] Upload queue for batch mode {upload_queue}')
else:
    logging.info("[Main] Running in regular '-path' mode, starting upload now")
    # This means the ran the script normally and specified a direct path to some media (or multiple media items, in which case we append it like normal to the list 'upload_queue')
    for arg_file in user_supplied_paths:
        upload_queue.append(arg_file)

logging.debug(f"[Main] Upload queue: {upload_queue}")

# Now for each file we've been supplied (batch more or just the user manually specifying multiple files) we create a loop here that uploads each of them until none are left
for file in upload_queue:
    # Remove all old temp_files & data from the previous upload
    delete_leftover_files(working_folder)
    torrent_info.clear()

    # TODO these are some hardcoded values to be handled at a later point in time
    # setting this to 0 is fine. But need to add support for these eventually.
    torrent_info["3d"] = "0"
    torrent_info["foregin"] = "0"

    # File we're uploading
    console.print(f'Uploading File/Folder: [bold][blue]{file}[/blue][/bold]')

    rar_file_validation_response = check_for_dir_and_extract_rars(file)
    if not rar_file_validation_response[0]:
        # Skip this entire 'file upload' & move onto the next (if exists)
        continue
    torrent_info["upload_media"] = rar_file_validation_response[1]

    # Performing guessit on the rawfile name and reusing the result instead of calling guessit over and over again
    guess_it_result = perform_guessit_on_filename(torrent_info["upload_media"])
    
    # -------- Basic info --------
    # So now we can start collecting info about the file/folder that was supplied to us (Step 1)
    if identify_type_and_basic_info(torrent_info["upload_media"], guess_it_result) == 'skip_to_next_file':
        # If there is an issue with the file & we can't upload we use this check to skip the current file & move on to the next (if exists)
        logging.debug(f"[Main] Skipping {torrent_info['upload_media']} because type and basic information cannot be identified.")
        continue

    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content=Uploading: **{torrent_info["upload_media"]}**')

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

    movie_db_providers = ['imdb', 'tmdb', 'tvmaze']

    # -------- Get TMDB & IMDB ID --------
    # If the TMDB/IMDB was not supplied then we need to search TMDB for it using the title & year
    for media_id_key, media_id_val in {"tmdb": args.tmdb, "imdb": args.imdb, "tvmaze": args.tvmaze}.items():
        if media_id_val is not None and len(media_id_val[0]) > 1:  # we include ' > 1 ' to prevent blank ID's and issues later
            # We have one more check here to verify that the "tt" is included for the IMDB ID (TMDB won't accept it if it doesnt)
            if media_id_key == 'imdb' and not str(media_id_val[0]).lower().startswith('tt'):
                torrent_info[media_id_key] = f'tt{media_id_val[0]}'
            else:
                torrent_info[media_id_key] = media_id_val[0]

    if all(x in torrent_info for x in movie_db_providers):
        # This means both the TMDB & IMDB ID are already in the torrent_info dict
        logging.info("[Main] TMDB, TVmaze & IMDB ID have been supplied by the user, so no need to make any TMDB API request")
    elif any(x in torrent_info for x in ['imdb', 'tmdb', 'tvmaze']):
        # This means we can skip the search via title/year and instead use whichever ID to get the other (tmdb -> imdb and vice versa)
        ids_present = list(filter(lambda id : id in torrent_info, movie_db_providers))
        ids_missing = [id for id in movie_db_providers if id not in ids_present]

        logging.info(f"[Main] We have '{ids_present}' with us currently.")
        logging.info(f"[Main] We are missing '{ids_missing}' starting External Database API requests now")
        # highest priority is given to imdb id.
        # if imdb id is provided by the user, then we use it to figure our the other two ids.
        # else we go for tmdb id and then tvmaze id
        if "imdb" in ids_present:
            # imdb id is available. 
            torrent_info["tmdb"] = metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tmdb", content_type=torrent_info["type"])
            if torrent_info["type"] == "episode":
                torrent_info["tvmaze"] = metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tvmaze", content_type=torrent_info["type"])
            else:
                torrent_info["tvmaze"] = "0"
        elif "tmdb" in ids_present:
            torrent_info["imdb"] = metadata_get_external_id(id_site="tmdb", id_value=torrent_info["tmdb"], external_site="imdb", content_type=torrent_info["type"])
            # we got value for imdb id, now we can use that to find out the tvmaze id
            if torrent_info["type"] == "episode":
                torrent_info["tvmaze"] = metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tvmaze", content_type=torrent_info["type"])
            else:
                torrent_info["tvmaze"] = "0"
        elif "tvmaze" in ids_present:
            if torrent_info["type"] == "episode":
                # we get the imdb id from tvmaze
                torrent_info["imdb"] = metadata_get_external_id(id_site="tvmaze", id_value=torrent_info["tvmaze"], external_site="imdb", content_type=torrent_info["type"])
                # and use the imdb id to find out the tmdb id
                torrent_info["tmdb"] = metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tmdb", content_type=torrent_info["type"])
            else:
                logging.fatal(f"[Main] TVMaze id provided for a non TV show. trying to identify 'TMDB' & 'IMDB' ID via title & year")
                # this method searchs and gets all three ids ` 'imdb', 'tmdb', 'tvmaze' `
                metadata_result = metadata_search_tmdb_for_id(query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"], auto_mode=auto_mode)
                torrent_info["tmdb"] = metadata_result["tmdb"]
                torrent_info["imdb"] = metadata_result["imdb"]
                torrent_info["tvmaze"] = metadata_result["tvmaze"]
        # there will not be an else case for the above if else ladder.
    else:
        logging.info("[Main] We are missing the 'TMDB', 'TVMAZE' & 'IMDB' ID, trying to identify it via title & year")
        # this method searchs and gets all three ids ` 'imdb', 'tmdb', 'tvmaze' `
        metadata_result = metadata_search_tmdb_for_id(query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"], auto_mode=auto_mode)
        torrent_info["tmdb"] = metadata_result["tmdb"]
        torrent_info["imdb"] = metadata_result["imdb"]
        torrent_info["tvmaze"] = metadata_result["tvmaze"]

    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
                data=f'content='f'IMDB: **{torrent_info["imdb"]}**  |  TMDB: **{torrent_info["tmdb"]}**')

    # -------- Use official info from TMDB --------
    title, year, tvdb, mal = metadata_compare_tmdb_data_local(torrent_info)
    torrent_info["title"] = title
    if year is not None:
        torrent_info["year"] = year
    # TODO try to move the tvdb and mal identification along with `metadata_get_external_id`
    torrent_info["tvdb"] = tvdb
    torrent_info["mal"] = mal

    # -------- User input edition --------
    # Support for user adding in custom edition if its not obvious from filename
    if args.edition:
        user_input_edition = str(args.edition[0])
        logging.info(f"[Main] User specified edition: {user_input_edition}")
        console.print(f"\nUsing the user supplied edition: [medium_spring_green]{user_input_edition}[/medium_spring_green]")
        torrent_info["edition"] = user_input_edition

    if auto_mode == "false" and Confirm.ask("Do you want to add custom texts to torrent description?", default=False):
        logging.debug(f'[Main] User decided to add custom text to torrent description. Handing control to custom_user_input module')
        torrent_info["custom_user_inputs"] = collect_custom_messages_from_user(f'{working_folder}/parameters/custom_text_components.json')
    else:
        logging.debug(f'[Main] User decided not to add custom text to torrent description or running in auto_mode')

    # -------- Dupe check for single tracker uploads --------
    # If user has provided only one Tracker to upload to, then we do dupe check prior to taking screenshots. [if dupe_check is enabled]
    # If there are duplicates in the tracker, then we do not waste time taking and uploading screenshots.
    if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) == 1:
        tracker = upload_to_trackers[0]
        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]

        console.line(count=2)
        console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')

        dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
        # If dupes are present and user decided to stop upload, for single tracker uploads we stop operation immediately
        # True == dupe_found
        # False == no_dupes/continue upload
        if dupe_check_response :
            logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
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

    if os.path.exists(f'{working_folder}/temp_upload/bbcode_images_nothumb.txt'):
        torrent_info["bbcode_images_nothumb"] = f'{working_folder}/temp_upload/bbcode_images_nothumb.txt'

    if os.path.exists(f'{working_folder}/temp_upload/bbcode_images_thumb_nothumb.txt'):
        torrent_info["bbcode_images_thumb_nothumb"] = f'{working_folder}/temp_upload/bbcode_images_thumb_nothumb.txt'
    
    if os.path.exists(f'{working_folder}/temp_upload/url_images.txt'):
         torrent_info["url_images"] = f'{working_folder}/temp_upload/url_images.txt'

    if os.path.exists(f'{working_folder}/temp_upload/image_paths.txt'):
         torrent_info["data_images"] = f'{working_folder}/temp_upload/image_paths.txt'

    # At this point the only stuff that remains to be done is site specific so we can start a loop here for each site we are uploading to
    logging.info("[Main] Now starting tracker specific tasks")
    for tracker in upload_to_trackers:
        torrent_info["shameless_self_promotion"] = f'Uploaded with {"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"} using GG-BOT Upload Assistant'
        
        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]
        logging.info(f"[Main] Trying to upload to: {tracker}")

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

        # (Theory) BHD has a different bbcode parser then BLU/ACM so the line break is different for each site
        # this is why we set it in each sites *.json file then retrieve it here in this 'for loop' since its different for each site
        bbcode_line_break = config['bbcode_line_break']

        # -------- Add custom descriptions to description.txt --------
        write_cutsom_user_inputs_to_description(torrent_info=torrent_info, 
            description_file_path=f'{working_folder}/temp_upload/description.txt', config=config, 
            tracker=tracker, bbcode_line_break=bbcode_line_break)

        # -------- Add bbcode images to description.txt --------
        add_bbcode_images_to_description(torrent_info=torrent_info, config=config, 
            description_file_path=f'{working_folder}/temp_upload/description.txt', bbcode_line_break=bbcode_line_break)

        # -------- Add custom uploader signature to description.txt --------
        write_uploader_signature_to_description(description_file_path=f'{working_folder}/temp_upload/description.txt',
            tracker=tracker, bbcode_line_break=bbcode_line_break)

        # Add the finished file to the 'torrent_info' dict
        torrent_info["description"] = f'{working_folder}/temp_upload/description.txt'

        # -------- Check for Dupes Multiple Trackers --------
        # when the user has configured multiple trackers to upload to
        # we take the screenshots and uploads them, then do dupe check for the trackers.
        # dupe check need not be performed if user provided only one tracker.
        # in cases where only one tracker is provided, dupe check will be performed prior to taking screenshots.
        if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) > 1:
            console.line(count=2)
            console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')
            # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
            dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
            # True == dupe_found
            # False == no_dupes/continue upload
            if dupe_check_response:
                logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
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
            source=config["source"],
            working_folder=working_folder,
            use_mktorrent=args.use_mktorrent,
            tracker=tracker,
            torrent_title=torrent_info["torrent_title"],
            callback=generate_callback
        )

        # -------- Assign specific tracker keys --------
        # This function takes the info we have the dict torrent_info and associates with the right key/values needed for us to use X trackers API
        # if for some reason the upload cannot be performed to the specific tracker, the method returns "STOP"
        if choose_right_tracker_keys() == "STOP":
            continue

        logging.debug(f"::::::::::::::::::::::::::::: Final torrent_info with all data filled :::::::::::::::::::::::::::::")
        logging.debug(f'\n{pformat(torrent_info)}')
        # -------- Upload everything! --------
        # 1.0 everything we do in this for loop isn't persistent, its specific to each site that you upload to
        # 1.1 things like screenshots, TMDB/IMDB ID's can & are reused for each site you upload to
        # 2.0 we take all the info we generated outside of this loop (mediainfo, description, etc) and combine it with tracker specific info and upload it all now
        upload_to_site(upload_to=tracker, tracker_api_key=temp_tracker_api_key)

        # Tracker Settings
        console.print("\n\n")
        tracker_settings_table = Table(show_header=True, title='[bold][deep_pink1]Tracker Settings[/bold][/deep_pink1]', header_style="bold cyan")
        tracker_settings_table.add_column("Key", justify="left")
        tracker_settings_table.add_column("Value", justify="left")

        for tracker_settings_key, tracker_settings_value in sorted(tracker_settings.items()):
            # Add torrent_info data to each row
            tracker_settings_table.add_row(f"[purple][bold]{tracker_settings_key}[/bold][/purple]", str(tracker_settings_value))
        console.print(tracker_settings_table, justify="center")

    # -------- Post Processing --------
    # After we upload the media we can move the .torrent & media files to a place the user specifies
    # This isn't tracker specific so its outside of that ^^ 'for loop'

    move_locations = {"torrent": f"{os.getenv('dot_torrent_move_location')}", "media": f"{os.getenv('media_move_location')}"}
    logging.debug(f"[Main] Move locations configured by user :: {move_locations}")

    for move_location_key, move_location_value in move_locations.items():
        # If the user supplied a path & it exists we proceed
        if len(move_location_value) == 0:
            logging.debug(f'[Main] Move location not configured for {move_location_key}')
            continue
        if os.path.exists(move_location_value):
            logging.info(f"[Main] The move path {move_location_value} exists")

            if move_location_key == 'torrent':
                sub_folder = "/"
                if os.getenv("enable_type_base_move") == "true":
                    sub_folder = sub_folder + torrent_info["type"] + "/"
                    os.makedirs(os.path.dirname(move_locations["torrent"] + sub_folder), exist_ok=True)
                # The user might have upload to a few sites so we need to move all files that end with .torrent to the new location
                list_dot_torrent_files = glob.glob(f"{working_folder}/temp_upload/*.torrent")
                for dot_torrent_file in list_dot_torrent_files:
                    # Move each .torrent file we find into the directory the user specified
                    logging.debug(f'[Main] Moving {dot_torrent_file} to {move_locations["torrent"] + sub_folder}')
                    try:
                        shutil.copy(dot_torrent_file, move_locations["torrent"] + sub_folder)
                    except Exception as e:
                        logging.exception(f'[Main] Cannot copy torrent {dot_torrent_file} to location {move_locations["torrent"] + sub_folder}')

            # Media files are moved instead of copied so we need to make sure they don't already exist in the path the user provides
            if move_location_key == 'media':
                if str(f"{Path(torrent_info['upload_media']).parent}/") == move_location_value:
                    console.print(f'\nError, {torrent_info["upload_media"]} is already in the move location you specified: "{move_location_value}"\n', style="red", highlight=False)
                    logging.error(f"[Main] {torrent_info['upload_media']} is already in {move_location_value}, Not moving the media")
                else:
                    logging.info(f"[Main] Moving {torrent_info['upload_media']} to {move_location_value}")
                    try:
                        shutil.move(torrent_info["upload_media"], move_location_value)
                    except Exception as e:
                        logging.exception(f"[Main] Cannot copy media {torrent_info['upload_media']} to location {move_location_value}")
        else:
            logging.error(f"[Main] Move path doesn't exist for {move_location_key} as {move_location_value}")

    # Torrent Info
    console.print("\n\n")
    torrent_info_table = Table(show_header=True, title='[bold][deep_pink1]Extracted Torrent Metadata[/bold][/deep_pink1]', header_style="bold cyan")
    torrent_info_table.add_column("Key", justify="left")
    torrent_info_table.add_column("Value", justify="left")

    for torrent_info_key, torrent_info_value in sorted(torrent_info.items()):
        # Add torrent_info data to each row
        torrent_info_table.add_row("[purple][bold]{}[/bold][/purple]".format(torrent_info_key), str(torrent_info_value))
    
    console.print(torrent_info_table, justify="center")

    script_end_time = time.perf_counter()
    total_run_time = f'{script_end_time - script_start_time:0.4f}'
    logging.info(f"[Main] Total runtime is {total_run_time} seconds")
    # Update discord channel
    if discord_url:
        requests.request("POST", discord_url, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f'content='f'Total runtime: **{total_run_time} seconds**')
