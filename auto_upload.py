#!/usr/bin/env python3

# default included packages
import os
import re
import sys
import glob
import time
import json
import base64
import logging
import argparse
import shutil
import bencoding
from pprint import pformat

# These packages need to be installed
import requests
from dotenv import load_dotenv
from pymediainfo import MediaInfo

# Rich is used for printing text & interacting with user input
from rich import box
from rich.table import Table
from rich.console import Console
from rich.traceback import install
from rich.prompt import Prompt, Confirm

# Search for **START** to get to the execution entry point of the upload assistant.

# utility methods
# Method that will read and accept text components for torrent description
# This is used to take screenshots and eventually upload them to either imgbox, imgbb, ptpimg or freeimage
from utilities.utils_user_input import collect_custom_messages_from_user
from utilities.utils_screenshots import take_upload_screens
# Method that will search for dupes in trackers.
import utilities.utils_miscellaneous as miscellaneous_utilities
import utilities.utils_translation as translation_utilities
import utilities.utils_metadata as metadata_utilities
import utilities.utils_torrent as torrent_utilities
import utilities.utils_bdinfo as bdinfo_utilities
import utilities.utils_basic as basic_utilities
import utilities.utils_dupes as dupe_utilities
import utilities.utils as utils

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
utils.validate_env_file(f'{working_folder}/samples/assistant/config.env')

# Used to correctly select json file
# the value in this dictionay must correspond to the file name of the site template
acronym_to_tracker = json.load(open(f'{working_folder}/parameters/tracker/acronyms.json'))

# the `prepare_tracker_api_keys_dict` prepares the api_keys_dict and also does mandatory property validations
api_keys_dict = utils.prepare_and_validate_tracker_api_keys_dict(f'{working_folder}/parameters/tracker/api_keys.json')

# Import 'auto_mode' status
if str(os.getenv('auto_mode')).lower() not in ['true', 'false']:
    logging.error('[Main] `auto_mode` is not set to `true/false` in `config.env`. Defaulting to `false`')
auto_mode = str(os.getenv('auto_mode', 'false')).lower()

# Setup args
parser = argparse.ArgumentParser()

# Required Arguments [Mandatory]
required_args = parser.add_argument_group('Required Arguments')
required_args.add_argument('-p', '--path', nargs='*', required=True, help="Use this to provide path(s) to file/folder")

# Commonly used args:
common_args = parser.add_argument_group('Commonly Used Arguments')
common_args.add_argument('-t', '--trackers', nargs='*', help="Tracker(s) to upload to. Space-separates if multiple (no commas)")
common_args.add_argument('-a', '--all_trackers', action='store_true',help="Select all trackers that can be uploaded to")
common_args.add_argument('-tmdb', nargs=1, help="Use this to manually provide the TMDB ID")
common_args.add_argument('-imdb', nargs=1, help="Use this to manually provide the IMDB ID")
common_args.add_argument('-tvmaze', nargs=1, help="Use this to manually provide the TVmaze ID")
common_args.add_argument('-mal', nargs=1, help="Use this to manually provide the MAL ID. If uploader detects any MAL id during search, this will be ignored.")
common_args.add_argument('-anon', action='store_true',help="Tf you want your upload to be anonymous (no other info needed, just input '-anon'")

# Less commonly used args (Not essential for most)
uncommon_args = parser.add_argument_group('Less Common Arguments')
uncommon_args.add_argument('-title', nargs=1, help="Custom title provided by the user")
uncommon_args.add_argument('-type', nargs=1, help="Use to manually specify 'movie' or 'tv'")
uncommon_args.add_argument('-reupload', nargs='*', help="This is used in conjunction with autodl to automatically re-upload any filter matches")
uncommon_args.add_argument('-batch', action='store_true',help="Pass this arg if you want to upload all the files/folder within the folder you specify with the '-p' arg")
uncommon_args.add_argument('-disc', action='store_true',help="If you are uploading a raw dvd/bluray disc you need to pass this arg")
uncommon_args.add_argument('-e', '--edition', nargs='*',help="Manually provide an 'edition' (e.g. Criterion Collection, Extended, Remastered, etc)")
uncommon_args.add_argument('-nfo', nargs=1, help="Use this to provide the path to an nfo file you want to upload")
uncommon_args.add_argument('-d', '--debug', action='store_true',help="Used for debugging. Writes debug lines to log file")
uncommon_args.add_argument('-mkt', '--use_mktorrent', action='store_true',help="Use mktorrent instead of torf (Latest git version only)")
uncommon_args.add_argument('-fpm', '--force_pymediainfo', action='store_true',help="Force use PyMediaInfo to extract video codec over regex extraction from file name")
uncommon_args.add_argument('-ss', '--skip_screenshots', action='store_true',help="Skip screenshot generation and upload for a run (overrides config.env)")
uncommon_args.add_argument('-r', '--resume', action='store_true', help="Resume previously unfinished upload.")
uncommon_args.add_argument('-3d', action='store_true',help="Mark the upload as 3D content")
uncommon_args.add_argument('-foreign', action='store_true',help="Mark the upload as foreign content [Non-English]")
uncommon_args.add_argument('-amf', '--allow_multiple_files', action='store_true',help="Override the default behavior and allow multiple files to be added in one torrent")

# args for Internal uploads
internal_args = parser.add_argument_group('Internal Upload Arguments')
internal_args.add_argument('-internal', action='store_true',help="(Internal) Used to mark an upload as 'Internal'")
internal_args.add_argument('-freeleech', action='store_true',help="(Internal) Used to give a new upload freeleech")
internal_args.add_argument('-featured', action='store_true', help="(Internal) feature a new upload")
internal_args.add_argument('-doubleup', action='store_true',help="(Internal) Give a new upload 'double up' status")
internal_args.add_argument('-tripleup', action='store_true',help="(Internal) Give a new upload 'triple up' status [XBTIT Exclusive]")
internal_args.add_argument('-sticky', action='store_true', help="(Internal) Pin the new upload")

args = parser.parse_args()
DIR = os.getenv('DIR')

# ---------------------------------------------------------------------- #
#                          Dupe Check in Tracker                         #
# ---------------------------------------------------------------------- #
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

    # If the user provides this arg with the title right after in double quotes then we automatically use that
    # If the user does not manually provide the title (Most common) then we pull the renaming template from *.json & use all the info we gathered earlier to generate a title
    # -------- format the torrent title --------
    torrent_info["torrent_title"] = str(args.title[0]) if args.title else translation_utilities.format_title(config, torrent_info)


    # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
    try:
        return dupe_utilities.search_for_dupes_api(
            acronym_to_tracker[str(tracker).lower()],
            imdb=torrent_info["imdb"],
            tmdb=torrent_info["tmdb"],
            tvmaze=torrent_info["tvmaze"],
            torrent_info=torrent_info,
            tracker_api=temp_tracker_api_key,
            debug=args.debug,
            working_folder=working_folder,
            auto_mode=os.getenv('auto_mode')
        )
    except Exception as e:
        logging.exception(f'[Main] Error occured while performing dupe check for tracker {tracker}. Error: {e}')
        console.print("[bold red]Unexpected error occured while performing dupe check. Assuming dupe exists on tracker and skipping[/bold red]")
        return True  # marking that dupes are present in the tracker


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
    console.rule("Analyzing & Identifying Video", style='red', align='center')
    console.line(count=1)

    # ------------ Save obvious info we are almost guaranteed to get from guessit into torrent_info dict ------------ #
    # But we can immediately assign some values now like Title & Year
    if 'title' not in guess_it_result:
        return 'skip_to_next_file'
        raise AssertionError(
            "Guessit could not even extract the title, something is really wrong with this filename.")

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

    if utils.has_user_provided_type(args.type):
        torrent_info["type"] = torrent_info["type"] = 'episode' if args.type[0] == 'tv' else 'movie'
    else:
        keys_we_need_torrent_info.append('type')

    keys_we_need_but_missing_torrent_info = []
    # We can (need to) have some other information in the final torrent title like 'editions', 'hdr', etc
    # All of that is important but not essential right now so we will try to extract that info later in the script
    logging.debug(
        f"Attempting to detect the following keys from guessit :: {keys_we_need_torrent_info}")
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

    # Deal with PDTV & SDTV sources
    # TODO move this to a utility class and integrate with auto reuploader
    if "source" in torrent_info:
        if torrent_info["source"] == 'Digital TV':
            torrent_info["source"] = 'PDTV'
        elif torrent_info["source"] == 'TV':
            torrent_info["source"] = 'SDTV'

    torrent_info["release_group"] = utils.sanitize_release_group_from_guessit(torrent_info)

    if "type" not in torrent_info:
        raise AssertionError(
            "'type' is not set in the guessit output, something is seriously wrong with this filename")

    # ------------ Format Season & Episode (Goal is 'S01E01' type format) ------------ #
    # Depending on if this is a tv show or movie we have some other 'required' keys that we need (season/episode)
    # guessit uses 'episode' for all tv related content (including seasons)
    if torrent_info["type"] == "episode":
        episode_basic_details = basic_utilities.basic_get_episode_basic_details(
            guess_it_result)
        if episode_basic_details == 'skip_to_next_file':
            return 'skip_to_next_file'
        s00e00, season_number, episode_number, complete_season, individual_episodes, daily_episodes = episode_basic_details
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
            bdinfo_utilities.bdinfo_validate_bdinfo_script_for_bare_metal(bdinfo_script)
            # validating presence of BDMV/STREAM/
            bdinfo_utilities.bdinfo_validate_presence_of_bdmv_stream(torrent_info["upload_media"])

            raw_video_file, largest_playlist = bdinfo_utilities.bdinfo_get_largest_playlist(bdinfo_script, auto_mode, torrent_info["upload_media"])

            torrent_info["raw_video_file"] = raw_video_file
            torrent_info["largest_playlist"] = largest_playlist
        else:
            raw_video_file = basic_utilities.basic_get_raw_video_file(
                torrent_info['upload_media'])
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
    keys_we_need_but_missing_torrent_info_list = ['video_codec', 'audio_codec']  # for disc we don't need mediainfo
    if args.disc:
        bdinfo_start_time = time.perf_counter()
        logging.debug(f"Generating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}")
        console.print(f"\nGenerating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}\n", style='bold blue')
        torrent_info["mediainfo"] = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}mediainfo.txt'
        torrent_info["bdinfo"] = bdinfo_utilities.bdinfo_generate_and_parse_bdinfo(bdinfo_script, torrent_info, args.debug)  # TODO handle non-happy paths
        logging.debug("::::::::::::::::::::::::::::: Parsed BDInfo output :::::::::::::::::::::::::::::")
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
        logging.error(
            "Unable to automatically extract all the required info from the FILENAME")
        logging.error(
            f"We are missing this info: {keys_we_need_but_missing_torrent_info}")
        # Show the user what is missing & the next steps
        console.print(
            f"[bold red underline]Unable to automatically detect the following info from the FILENAME:[/bold red underline] [green]{keys_we_need_but_missing_torrent_info}[/green]")

    # We do some extra processing for the audio & video codecs since they are pretty important for the upload process & accuracy so they get appended each time
    # ['mediainfo', 'video_codec', 'audio_codec'] or ['video_codec', 'audio_codec'] for disks
    for identify_me in keys_we_need_but_missing_torrent_info_list:
        if identify_me not in keys_we_need_but_missing_torrent_info:
            keys_we_need_but_missing_torrent_info.append(identify_me)

    # parsing mediainfo, this will be reused for further processing.
    # only when the required data is mediainfo, this will be computed again, but as `text` format to write to file.
    parse_me = torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"]
    logging.debug(f'[Main] Torrent info just before MediaInfo generation. \n {pformat(torrent_info)}')
    media_info_result = basic_utilities.basic_get_mediainfo(parse_me)

    if args.disc:
        # for full disk uploads the bdinfo summary itself will be set as the `mediainfo_summary`
        logging.info(
            "[Main] Full Disk Upload. Setting bdinfo summary as mediainfo summary")
        with open(f'{working_folder}/temp_upload/{torrent_info["working_folder"]}mediainfo.txt', 'r') as summary:
            bdInfo_summary = summary.read()
            torrent_info["mediainfo_summary"] = bdInfo_summary
    else:
        # certain release groups will add IMDB, TMDB and TVDB id in the general section of mediainfo. If one such id is present then we can use it and
        # consider it the same as being provided by the user (no need to search)
        # PS: We don't use the tvdb id obtained here. (Might be deprecated)
        mediainfo_summary, tmdb, imdb, _ = basic_utilities.basic_get_mediainfo_summary(media_info_result.to_data())
        torrent_info["mediainfo_summary"] = mediainfo_summary
        if tmdb != "0":
            # we will get movie/12345 or tv/12345 => we only need 12345 part.
            tmdb = tmdb[tmdb.find("/") + 1:] if tmdb.find("/") >= 0 else tmdb
            args.tmdb = [tmdb]
            logging.info(f"[Main] Obtained TMDB Id from mediainfo summary. Proceeding with {args.tmdb}")
        if imdb != "0":
            args.imdb = [imdb]
            logging.info(f"[Main] Obtained IMDB Id from mediainfo summary. Proceeding with {args.imdb}")

    #  Now we'll try to use regex, mediainfo, ffprobe etc to try and auto get that required info
    skip = False
    for missing_val in keys_we_need_but_missing_torrent_info:
        # Save the analyze_video_file() return result into the 'torrent_info' dict
        torrent_info[missing_val] = analyze_video_file(
            missing_value=missing_val, media_info=media_info_result)
        if torrent_info[missing_val] == 'skip_to_next_file':
            skip = True
            continue
    if skip:
        return 'skip_to_next_file'
    logging.debug(
        "::::::::::::::::::::::::::::: Torrent Information collected so far :::::::::::::::::::::::::::::")
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

    codec_result_table = Table(
        box=box.SQUARE, title='Basic media summary', title_style='bold #be58bf')

    for column_display_value in columns_we_want.values():
        if len(column_display_value) != 0:
            logging.debug(
                f"Adding column {column_display_value} to the torrent details result table")
            codec_result_table.add_column(
                f"{column_display_value}", justify='center', style='#38ACEC')

    basic_info = []
    # add the actual data now
    for column_query_key, column_display_value in columns_we_want.items():
        if len(column_display_value) != 0:
            torrent_info_key_failsafe = (torrent_info[column_query_key] if column_query_key !=
                                         'type' else presentable_type) if column_query_key in torrent_info else None
            logging.debug(
                f"Getting value for {column_query_key} with display {column_display_value} as {torrent_info_key_failsafe} for the torrent details result table")
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
        return basic_utilities.basic_get_missing_mediainfo(torrent_info, parse_me, working_folder)

    # ------------------- Source ------------------- #
    if missing_value == "source":
        try:
            source, source_type = basic_utilities.basic_get_missing_source(torrent_info, args.disc, auto_mode, missing_value)
        except:
            return 'skip_to_next_file'
        torrent_info["source"] = source
        torrent_info["source_type"] = source_type
        return source

    # ---------------- Video Resolution ---------------- #
    if missing_value == "screen_size":
        return basic_utilities.basic_get_missing_screen_size(torrent_info, args.disc, media_info_video_track, auto_mode, missing_value)

    # ---------------- Audio Channels ---------------- #
    if missing_value == "audio_channels":
        return basic_utilities.basic_get_missing_audio_channels(torrent_info, args.disc, auto_mode, parse_me, media_info_audio_track, missing_value)

    # ---------------- Audio Codec ---------------- #
    if missing_value == "audio_codec":
        missing_audio_codec = basic_utilities.basic_get_missing_audio_codec(torrent_info=torrent_info, is_disc=args.disc, auto_mode=auto_mode,
                                                                           audio_codec_file_path=f'{working_folder}/parameters/audio_codecs.json',
                                                                           media_info_audio_track=media_info_audio_track, parse_me=parse_me,
                                                                           missing_value=missing_value)
        if missing_audio_codec == 'skip_to_next_file':
            return 'skip_to_next_file'
        audio_codec, atmos = missing_audio_codec

        if atmos is not None:
            torrent_info["atmos"] = atmos
        if audio_codec is not None:
            return audio_codec

    # ---------------- Video Codec ---------------- #
    # I'm pretty confident that a video_codec will be selected automatically each time, unless mediainfo fails catastrophically we should always
    # have a codec we can return. User input isn't needed here
    if missing_value == "video_codec":
        dv, hdr, video_codec = basic_utilities.basic_get_missing_video_codec(
            torrent_info=torrent_info,
            is_disc=args.disc, auto_mode=auto_mode,
            media_info_video_track=media_info_video_track,
            force_pymediainfo=args.force_pymediainfo
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
    logging.debug('[MiscellaneousDetails] Trying to identify miscellaneous details for torrent.')
    # ------ Specific Source info ------ #
    if "source_type" not in torrent_info:
        torrent_info["source_type"] = miscellaneous_utilities.miscellaneous_identify_source_type(torrent_info["raw_file_name"], auto_mode, torrent_info["source"])

    if torrent_info["source_type"] == 'skip_to_next_file':
        return 'skip_to_next_file'
    # ------ WEB streaming service stuff here ------ #
    if torrent_info["source"] == "Web":
        # TODO check whether None needs to be set as `web_source`
        torrent_info["web_source"] = miscellaneous_utilities.miscellaneous_identify_web_streaming_source(
            f'{working_folder}/parameters/streaming_services.json', torrent_info["raw_file_name"], guess_it_result)

    # --- Custom & extra info --- #
    # some torrents have 'extra' info in the title like 'repack', 'DV', 'UHD', 'Atmos', 'remux', etc
    # We simply use regex for this and will add any matches to the dict 'torrent_info', later when building the final title we add any matches (if they exist) into the title

    # repacks
    torrent_info["repack"] = miscellaneous_utilities.miscellaneous_identify_repacks(torrent_info["raw_file_name"])

    # --- Bluray disc type --- #
    if torrent_info["source_type"] == "bluray_disc":
        torrent_info["bluray_disc_type"] = miscellaneous_utilities.miscellaneous_identify_bluray_disc_type(
            torrent_info["screen_size"], torrent_info["upload_media"])

    # Bluray disc regions
    # Regions are read from new json file
    bluray_regions = json.load(open(f'{working_folder}/parameters/bluray_regions.json'))

    # Try to split the torrent title and match a few key words
    # End user can add their own 'key_words' that they might want to extract and add to the final torrent title
    key_words = {'remux': 'REMUX', 'hdr': torrent_info.get("hdr", "HDR"),  'uhd': 'UHD', 'hybrid': 'Hybrid', 'atmos': 'Atmos', 'ddpa': 'Atmos'}

    hdr_hybrid_remux_keyword_search = str(torrent_info["raw_file_name"]).lower().replace(" ", ".").replace("-", ".").split(".")

    for word in hdr_hybrid_remux_keyword_search:
        word = str(word)
        if word in key_words.keys():
            logging.info(f"extracted the key_word: {word} from the filename")
            # special case. TODO find a way to generalize and handle this
            if word == 'ddpa':
                torrent_info["atmos"] = key_words[word]
            else:
                torrent_info[word] = key_words[word]

        # Bluray region source
        if "disc" in torrent_info["source_type"]:
            # This is either a bluray or dvd disc, these usually have the source region in the filename, try to extract it now
            if word.upper() in bluray_regions.keys():
                torrent_info["region"] = word.upper()

        # Dolby vision (filename detection)
        # we only need to do this if user is having an older verison of mediainfo, which can't detect dv
        if "dv" not in torrent_info or torrent_info["dv"] is None or len(torrent_info["dv"]) < 1:
            if any(x == word for x in ['dv', 'dovi']):
                logging.info("Detected Dolby Vision from the filename")
                torrent_info["dv"] = "DV"

    # trying to check whether Do-Vi exists in the title, again needed only for older versions of mediainfo
    if "dv" not in torrent_info or torrent_info["dv"] is None or len(torrent_info["dv"]) < 1:
        if 'do'in hdr_hybrid_remux_keyword_search and 'vi' in hdr_hybrid_remux_keyword_search:
            torrent_info["dv"] = "DV"
            logging.info("Adding Do-Vi from file name. Marking existing of Dolby Vision")

    # use regex (sourced and slightly modified from official radarr repo) to find torrent editions (Extended, Criterion, Theatrical, etc)
    # https://github.com/Radarr/Radarr/blob/5799b3dc4724dcc6f5f016e8ce4f57cc1939682b/src/NzbDrone.Core/Parser/Parser.cs#L21
    torrent_info["edition"] = miscellaneous_utilities.miscellaneous_identify_bluray_edition(
        torrent_info["upload_media"])

    # --------- Fix scene group tags --------- #
    # Whilst most scene group names are just capitalized but occasionally as you can see ^^ some are not (e.g. KOGi)
    # either way we don't want to be capitalizing everything (e.g. we want 'NTb' not 'NTB') so we still need a dict of scene groups and their proper capitalization
    if "release_group" in torrent_info:
        torrent_info["scene"], torrent_info["release_group"] = miscellaneous_utilities.miscellaneous_perform_scene_group_capitalization(
            f'{working_folder}/parameters/scene_groups.json', torrent_info["release_group"])

    # --------- SD? --------- #
    res = re.sub("[^0-9]", "", torrent_info["screen_size"])
    if int(res) < 720:
        torrent_info["sd"] = 1


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
        pass  # headers = None
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
        logging.fatal('[TrackerUpload] Cookie based authentication is not supported as for now.')

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
                logging.debug(f"[TrackerUpload] Setting file {tracker_settings[key]} as string array for key '{key}'")
                with open(tracker_settings[key], 'r') as file_contents:
                    screenshot_array = []
                    for line in file_contents.readlines():
                        screenshot_array.append(line.strip())
                    payload[f'{key}[]' if config["technical_jargons"]["payload_type"] == "MULTI-PART" else key] = screenshot_array
                    logging.debug(f"[TrackerUpload] String array data for key {key} :: {screenshot_array}")
            else:
                logging.critical(f"[TrackerUpload] The file/path `{tracker_settings[key]}` for key '{req_opt}' does not exist!")
                continue
        elif str(config[req_opt][key]) == "string|array":
            """
                for string|array we split the data with by new line, where each line becomes and element of the array or list
            """
            logging.debug(f"[TrackerUpload] Setting data {tracker_settings[key]} as string array for key '{key}'")
            screenshot_array = []
            for line in tracker_settings[key].split("\n"):
                if len(line.strip()) > 0:
                    screenshot_array.append(line.strip())
            payload[f'{key}[]' if config["technical_jargons"]["payload_type"] == "MULTI-PART" else key] = screenshot_array
            logging.debug(f"[TrackerUpload] String array data for key '{key}' :: {screenshot_array}")

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
        review_upload_settings_text_table = Table(
            title=f"\n\n\n\n[bold][deep_pink1]{upload_to} Upload data (Text):[/bold][/deep_pink1]",
            show_header=True,
            header_style="bold cyan",
            box=box.HEAVY,
            border_style="dim",
            show_lines=True
        )

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
            review_upload_settings_files_table = Table(
                title=f"\n\n\n\n[bold][green3]{upload_to} Upload data (FILES):[/green3][/bold]",
                show_header=True,
                header_style="bold cyan",
                box=box.HEAVY,
                border_style="dim",
                show_lines=True
            )

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
            return False

    logging.fatal(f"[TrackerUpload] URL: {url_masked} \n Data: {payload} \n Files: {files}")

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
        if "success" in response.json():
            if str(response.json()["success"]).lower() == "true":
                url_location = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}torrent_id.txt'
                with open(url_location, 'w+') as f:
                    f.write(response.json()['data'].split('/')[-1].split('.')[0])
                logging.info(f"[TrackerUpload] Upload to {upload_to} was a success!")
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
        elif "status" in response.json():
            if str(response.json()["status"]).lower() == "true" or str(response.json()["status"]).lower() == "success":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
                return False
        elif "success" in str(response.json()).lower():
            if str(response.json()["success"]).lower() == "true":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
                return False
        elif "status" in str(response.json()).lower():
            if str(response.json()["status"]).lower() == "true":
                logging.info("[TrackerUpload] Upload to {} was a success!".format(upload_to))
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical("[TrackerUpload] Upload to {} failed".format(upload_to))
                return False
        else:
            console.print('Upload to tracker failed.', style='bold red')
            logging.critical("[TrackerUpload] Something really went wrong when uploading to {} and we didn't even get a 'success' json key".format(upload_to))
        return False

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
            logging.critical(
                f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({tracker}). Error: Error {response.json()["error"] if "error" in response.json() else response.json()}')
        except Exception:
            logging.critical(f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({tracker}).')
        logging.error("[TrackerUpload] Upload failed")

    else:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The status code isn't [green]200[/green] so something failed, upload may have failed")
        logging.error('[TrackerUpload] Status code is not 200, upload might have failed')
    return False


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#  **START** This is the first code that executes when we run the script, we log that info and we start a timer so we can keep track of total script runtime **START** #
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------#

script_start_time = time.perf_counter()
starting_new_upload = f" {'-' * 24} Starting new upload {'-' * 24} "

console.line(count=2)
utils.display_banner("  Upload  Assistant  ")
console.line(count=1)

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
    sys.exit(console.print("\nQuiting upload process since Full Disk uploads are not allowed in this image.\n",style="bold red", highlight=False))

torrent_client = utils.get_torrent_client_if_needed()

# Set the value of args.path to a variable that we can overwrite with a path translation later (if needed)
user_supplied_paths = args.path

# Verify we support the tracker specified
logging.debug(f"[Main] Trackers provided by user {args.trackers}")
upload_to_trackers = utils.get_and_validate_configured_trackers(args.trackers, args.all_trackers, api_keys_dict, acronym_to_tracker.keys())

# Show the user what sites we will upload to
console.line(count=2)
console.rule("Target Trackers", style='red', align='center')
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

# TODO an issue with batch mode currently is that we have a lot of "assert" & sys.exit statements during the prep work we do for each upload,
# if one of these "assert/quit" statements get triggered, then it will quit the entire script instead of just moving on to the next file in the list 'upload_queue'
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

logging.debug(f"[Main] Upload queue: {upload_queue}")
def processDot(torrent):
    try:
        f = open(torrent, "rb")
        raw_torrent = f.read()
        f.close()
        torrent_header = bencoding.decode(raw_torrent)
        dot = {"name":torrent_header[b'info'][b'name'].decode("utf-8"), 'files': [torrent_header[b'info'][b'name'].decode("utf-8")]}
        if b'files' in torrent_header[b'info']:
            #print('tem files')
            dot['files'] = []
            for file in torrent_header[b'info'][b'files']:
                #print(file)
                dot['files'].append(dot['name']+'/'+file[b'path'][0].decode("utf-8"))    
        for file in dot['files']:
            if not os.path.isfile(DIR + file):
                return False, dot['name']
        return True, DIR + dot['name']
    except Exception as e:
        print(e)
        return False, ''
        pass

# Now for each file we've been supplied (batch more or just the user manually specifying multiple files) we create a loop here that uploads each of them until none are left
upload_queue.sort()
for torrent in upload_queue:
    status , file = processDot(torrent)
    if not status:
        shutil.move(torrent,f"missing/{torrent.split('/')[-1]}")
        continue    
    
    
    # Remove all old temp_files & data from the previous upload
    torrent_info.clear()
    # the working_folder will container a hash value with succeeding /
    torrent_info["working_folder"] = utils.delete_leftover_files(working_folder, resume=args.resume, file=file)

    # TODO these are some hardcoded values to be handled at a later point in time
    # setting this to 0 is fine. But need to add support for these eventually.
    torrent_info["3d"] = "0"
    torrent_info["foregin"] = "0"

    # File we're uploading
    console.print(f'Uploading File/Folder: [bold][blue]{file}[/blue][/bold]')

    rar_file_validation_response = utils.check_for_dir_and_extract_rars(file)
    if not rar_file_validation_response[0]:
        # Skip this entire 'file upload' & move onto the next (if exists)
        continue
    torrent_info["upload_media"] = rar_file_validation_response[1]
    # Performing guessit on the rawfile name and reusing the result instead of calling guessit over and over again
    guess_it_result = utils.perform_guessit_on_filename(torrent_info["upload_media"])

    # -------- Basic info --------
    # So now we can start collecting info about the file/folder that was supplied to us (Step 1)
    if identify_type_and_basic_info(torrent_info["upload_media"], guess_it_result) == 'skip_to_next_file':
        # If there is an issue with the file & we can't upload we use this check to skip the current file & move on to the next (if exists)
        logging.debug(f"[Main] Skipping {torrent_info['upload_media']} because type and basic information cannot be identified.")
        shutil.move(torrent,f"error/{torrent.split('/')[-1]}")
        continue

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
    skip = identify_miscellaneous_details(guess_it_result)
    if skip == 'skip_to_next_file':
        shutil.move(torrent,f"error/{torrent.split('/')[-1]}")
        continue
    # tmdb, imdb and tvmaze in torrent_info will be filled by this method
    metadata_utilities.fill_database_ids(torrent_info, args.tmdb, args.imdb, args.tvmaze, auto_mode)
    if not 'tmdb' in torrent_info:
        print('No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID')
        shutil.move(torrent,f"error/{torrent.split('/')[-1]}")
        continue
    # -------- Use official info from TMDB --------
    title, year, tvdb, mal = metadata_utilities.metadata_compare_tmdb_data_local(torrent_info)

    # using user provided MAL if uploader was not able to find out one
    if mal == "0":
        # uploader couldn't identify any mal id
        if args.mal is not None and len(args.mal[0]) > 1:
            # user has provided a mal id manually. Since we were not able to identify one, we'll use the id provided by the user.
                logging.info(f"[Main] Using user provided mal id '{args.mal[0]}'")
                mal = args.mal[0]

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
        logging.debug('[Main] User decided to add custom text to torrent description. Handing control to custom_user_input module')
        torrent_info["custom_user_inputs"] = collect_custom_messages_from_user(f'{working_folder}/parameters/custom_text_components.json')
    else:
        logging.debug('[Main] User decided not to add custom text to torrent description or running in auto_mode')

    # Fix some default naming styles
    translation_utilities.fix_default_naming_styles(torrent_info)

    # -------- Dupe check for single tracker uploads --------
    # If user has provided only one Tracker to upload to, then we do dupe check prior to taking screenshots. [if dupe_check is enabled]
    # If there are duplicates in the tracker, then we do not waste time taking and uploading screenshots.
    if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) == 1:
        tracker = upload_to_trackers[0]
        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]

        console.line(count=2)
        console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')
        logging.debug(f"[Main] Dumping torrent_info contents to log before dupe check: \n{pformat(torrent_info)}")
        dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
        # If dupes are present and user decided to stop upload, for single tracker uploads we stop operation immediately
        # True == dupe_found
        # False == no_dupes/continue upload
        if dupe_check_response:
            logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
            if auto_mode == "true":
                shutil.move(torrent,f"dupe/{torrent.split('/')[-1]}")
                continue
            else:
                sys.exit(console.print("\nOK, quitting now..\n",style="bold red", highlight=False))

    # -------- Take / Upload Screenshots --------
    media_info_duration = MediaInfo.parse(torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"]).tracks[1]
    torrent_info["duration"] = str(media_info_duration.duration).split(".", 1)[0]
    # This is used to evenly space out timestamps for screenshots
    # Call function to actually take screenshots & upload them (different file)
    take_upload_screens(
        duration=torrent_info["duration"],
        upload_media_import=torrent_info["raw_video_file"] if "raw_video_file" in torrent_info else torrent_info["upload_media"],
        torrent_title_import=torrent_info["title"],
        base_path=working_folder,
        hash_prefix=torrent_info["working_folder"],
        skip_screenshots=args.skip_screenshots
    )

    screenshots_data = json.load(open(f"{working_folder}/temp_upload/{torrent_info['working_folder']}screenshots/screenshots_data.json"))
    torrent_info["bbcode_images"] = screenshots_data["bbcode_images"]
    torrent_info["bbcode_images_nothumb"] = screenshots_data["bbcode_images_nothumb"]
    torrent_info["bbcode_thumb_nothumb"] = screenshots_data["bbcode_thumb_nothumb"]
    torrent_info["url_images"] = screenshots_data["url_images"]
    torrent_info["data_images"] = screenshots_data["data_images"]

    # At this point the only stuff that remains to be done is site specific so we can start a loop here for each site we are uploading to
    logging.info("[Main] Now starting tracker specific tasks")
    for tracker in upload_to_trackers:
        torrent_info["shameless_self_promotion"] = f'Uploaded with {"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"} using GG-BOT Upload Assistant'

        temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]
        logging.info(f"[Main] Trying to upload to: {tracker}")

        # Create a new dictionary that we store the exact keys/vals that the site is expecting
        tracker_settings = {}
        tracker_settings.clear()

        # Open the correct .json file since we now need things like announce URL, API Keys, and API info
        with open("{}/site_templates/".format(working_folder) + str(acronym_to_tracker.get(str(tracker).lower())) + ".json", "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        # If the user provides this arg with the title right after in double quotes then we automatically use that
        # If the user does not manually provide the title (Most common) then we pull the renaming template from *.json & use all the info we gathered earlier to generate a title
        # -------- format the torrent title --------
        torrent_info["torrent_title"] = str(args.title[0]) if args.title else translation_utilities.format_title(config, torrent_info)

        # (Theory) BHD has a different bbcode parser then BLU/ACM so the line break is different for each site
        # this is why we set it in each sites *.json file then retrieve it here in this 'for loop' since its different for each site
        bbcode_line_break = config['bbcode_line_break']

        # -------- Add custom descriptions to description.txt --------
        utils.write_cutsom_user_inputs_to_description(
            torrent_info=torrent_info,
            description_file_path=f'{working_folder}/temp_upload/{torrent_info["working_folder"]}description.txt',
            config=config,
            tracker=tracker,
            bbcode_line_break=bbcode_line_break,
            debug=args.debug
        )

        # -------- Add bbcode images to description.txt --------
        utils.add_bbcode_images_to_description(
            torrent_info=torrent_info,
            config=config,
            description_file_path=f'{working_folder}/temp_upload/{torrent_info["working_folder"]}description.txt',
            bbcode_line_break=bbcode_line_break
        )

        # -------- Add custom uploader signature to description.txt --------
        utils.write_uploader_signature_to_description(
            description_file_path=f'{working_folder}/temp_upload/{torrent_info["working_folder"]}description.txt',
            tracker=tracker,
            bbcode_line_break=bbcode_line_break
        )

        # Add the finished file to the 'torrent_info' dict
        torrent_info["description"] = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}description.txt'

        # -------- Check for Dupes Multiple Trackers --------
        # when the user has configured multiple trackers to upload to
        # we take the screenshots and uploads them, then do dupe check for the trackers.
        # dupe check need not be performed if user provided only one tracker.
        # in cases where only one tracker is provided, dupe check will be performed prior to taking screenshots.
        if os.getenv('check_dupes') == 'true' and len(upload_to_trackers) > 1:
            console.line(count=2)
            console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')
            logging.debug(f"[Main] Dumping torrent_info contents to log before dupe check: \n{pformat(torrent_info)}")
            # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
            dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
            # True == dupe_found
            # False == no_dupes/continue upload
            if dupe_check_response:
                logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
                # If dupe was found & the script is auto_mode OR if the user responds with 'n' for the 'dupe found, continue?' prompt
                #  we will essentially stop the current 'for loops' iteration & jump back to the beginning to start next cycle (if exists else quits)
                shutil.move(torrent,f"dupe/{torrent.split('/')[-1]}")
                continue

        # -------- Generate .torrent file --------
        console.print(f'\n[bold]Generating .torrent file for [chartreuse1]{tracker}[/chartreuse1][/bold]')
        logging.debug(f'[Main] Torrent info just before dot torrent creation. \n {pformat(torrent_info)}')
        # If the type is a movie, then we only include the `raw_video_file` for torrent file creation.
        # If type is an episode, then we'll create torrent file for the the `upload_media` which could be an single episode or a season folder
        if args.allow_multiple_files == False and torrent_info["type"] == "movie" and "raw_video_file" in torrent_info:
            torrent_media = torrent_info["raw_video_file"]
        else:
            torrent_media = torrent_info["upload_media"]

        generated = torrent_utilities.generate_dot_torrent(
            media=torrent_media,
            announce=list(os.getenv(f"{str(tracker).upper()}_ANNOUNCE_URL").split(" ")),
            source=config["source"],
            working_folder=working_folder,
            hash_prefix=torrent_info["working_folder"],
            use_mktorrent=args.use_mktorrent,
            tracker=tracker,
            torrent_title=torrent_info["torrent_title"],
            torrent=torrent
        )
        if generated == 'skip_to_next_file':
            shutil.move(torrent,f"error/{torrent.split('/')[-1]}")
            continue

        # -------- Assign specific tracker keys --------
        # This function takes the info we have the dict torrent_info and associates with the right key/values needed for us to use X trackers API
        # if for some reason the upload cannot be performed to the specific tracker, the method returns "STOP"
        if translation_utilities.choose_right_tracker_keys(config, tracker_settings, tracker, torrent_info, args, working_folder) == "STOP":
            shutil.move(torrent,f"error/{torrent.split('/')[-1]}")
            continue

        logging.debug("::::::::::::::::::::::::::::: Final torrent_info with all data filled :::::::::::::::::::::::::::::")
        logging.debug(f'\n{pformat(torrent_info)}')
        # -------- Upload everything! --------
        # 1.0 everything we do in this for loop isn't persistent, its specific to each site that you upload to
        # 1.1 things like screenshots, TMDB/IMDB ID's can & are reused for each site you upload to
        # 2.0 we take all the info we generated outside of this loop (mediainfo, description, etc) and combine it with tracker specific info and upload it all now
        torrent_info[f"{tracker}_upload_status"] = upload_to_site(upload_to=tracker, tracker_api_key=temp_tracker_api_key)

        # Tracker Settings
        console.print("\n\n")
        tracker_settings_table = Table(show_header=True, title='[bold][deep_pink1]Tracker Settings[/bold][/deep_pink1]', header_style="bold cyan")
        tracker_settings_table.add_column("Key", justify="left")
        tracker_settings_table.add_column("Value", justify="left")

        for tracker_settings_key, tracker_settings_value in sorted(tracker_settings.items()):
            # Add torrent_info data to each row
            tracker_settings_table.add_row(f"[purple][bold]{tracker_settings_key}[/bold][/purple]", str(tracker_settings_value))
        console.print(tracker_settings_table, justify="center")

    # Torrent Info
    console.print("\n\n")
    torrent_info_table = Table(show_header=True, title='[bold][deep_pink1]Extracted Torrent Metadata[/bold][/deep_pink1]', header_style="bold cyan")
    torrent_info_table.add_column("Key", justify="left")
    torrent_info_table.add_column("Value", justify="left")

    for torrent_info_key, torrent_info_value in sorted(torrent_info.items()):
        # Add torrent_info data to each row
        torrent_info_table.add_row("[purple][bold]{}[/bold][/purple]".format(torrent_info_key), str(torrent_info_value))

    console.print(torrent_info_table, justify="center")

    # -------- Post Processing --------
    console.line(count=2)
    console.rule("Post Processing", style='red', align='center')
    console.line(count=1)

    #torrent_info["post_processing_complete"] = False
    #for tracker in upload_to_trackers:
    #    if torrent_info["post_processing_complete"] == True:
    #        break  # this flag is used for watch folder post processing. we need to move only once
    #    utils.perform_post_processing(torrent_info, torrent_client, working_folder, tracker, args.allow_multiple_files)
    shutil.move(torrent,f"lancados/{torrent.split('/')[-1]}")
    try:
        print(torrent_info["working_folder"])
        shutil.move(f'{working_folder}/temp_upload/{torrent_info["working_folder"]}',f'{working_folder}/cache/{torrent_info["working_folder"]}')
    except:
        pass
    script_end_time = time.perf_counter()
    total_run_time = f'{script_end_time - script_start_time:0.4f}'
    logging.info(f"[Main] Total runtime is {total_run_time} seconds")
