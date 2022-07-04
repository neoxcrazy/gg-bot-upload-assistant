#!/usr/bin/env python3

# default included packages
import os
import re
import glob
import json
import base64
import logging
import schedule
import argparse

from pprint import pformat
from datetime import datetime

# These packages need to be installed
import requests
from dotenv import load_dotenv
from pymediainfo import MediaInfo

# Rich is used for printing text & interacting with user input
from rich import box
from rich.table import Table
from rich.console import Console
from rich.traceback import install

# utility methods
# Method that will search for dupes in trackers.
# This is used to take screenshots and eventually upload them to either imgbox, imgbb, ptpimg or freeimage
from utilities.utils_screenshots import take_upload_screens
from utilities.utils_dupes import search_for_dupes_api
# Method that will search for dupes in trackers.
import utilities.utils_miscellaneous as miscellaneous_utilities
import utilities.utils_translation as translation_utilities
import utilities.utils_reupload as reupload_utilities
import utilities.utils_metadata as metadata_utilities
import utilities.utils_torrent as torrent_utilities
import utilities.utils_basic as basic_utilities
import utilities.utils as utils

# processing modules
from modules.cache import CacheFactory, CacheVendor
from modules.torrent_client import Clients, TorrentClientFactory

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
logging.basicConfig(filename='{}/reupload_script.log'.format(working_folder), filemode="w", level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')

# Load the .env file that stores info like the tracker/image host API Keys & other info needed to upload
load_dotenv(f'{working_folder}/reupload.config.env')

# Getting the keys present in the config.env.sample
# These keys are then used to compare with the env variable keys provided during runtime.
# Presently we just displays any missing keys, TODO in the future do something more useful with this information
utils.validate_env_file(f'{working_folder}/samples/reuploader/reupload.config.env')

# Used to correctly select json file
# the value in this dictionay must correspond to the file name of the site template
acronym_to_tracker = json.load(open(f'{working_folder}/parameters/tracker/acronyms.json'))

auto_mode = 'true'

# Setup args
parser = argparse.ArgumentParser()

common_args = parser.add_argument_group('Commonly Used Arguments')
common_args.add_argument('-t', '--trackers', nargs='*', help="Tracker(s) to upload to. Space-separates if multiple (no commas)")
common_args.add_argument('-a', '--all_trackers', action='store_true', help="Select all trackers that can be uploaded to")
common_args.add_argument('-anon', action='store_true', help="Tf you want your upload to be anonymous (no other info needed, just input '-anon'")

uncommon_args = parser.add_argument_group('Less Common Arguments')
uncommon_args.add_argument('-d', '--debug', action='store_true', help="Used for debugging. Writes debug lines to log file")
uncommon_args.add_argument('-mkt', '--use_mktorrent', action='store_true', help="Use mktorrent instead of torf (Latest git version only)")
uncommon_args.add_argument('-fpm', '--force_pymediainfo', action='store_true', help="Force use PyMediaInfo to extract video codec over regex extraction from file name")
uncommon_args.add_argument('-ss', '--skip_screenshots', action='store_true', help="Skip screenshot generation and upload for a run (overrides config.env)")
uncommon_args.add_argument('-disc', action='store_true',help="Unsupported for AutoReuploader. Added for compatibility with upload assistant")

# args for Internal uploads
internal_args = parser.add_argument_group('Internal Upload Arguments')
internal_args.add_argument('-internal', action='store_true', help="(Internal) Used to mark an upload as 'Internal'")
internal_args.add_argument('-freeleech', action='store_true', help="(Internal) Used to give a new upload freeleech")
internal_args.add_argument('-featured', action='store_true', help="(Internal) feature a new upload")
internal_args.add_argument('-doubleup', action='store_true', help="(Internal) Give a new upload 'double up' status")
internal_args.add_argument('-tripleup', action='store_true', help="(Internal) Give a new upload 'triple up' status [XBTIT Exclusive]")
internal_args.add_argument('-sticky', action='store_true', help="(Internal) Pin the new upload")

args = parser.parse_args()

# ---------------------------------------------------------------------------------#
#  **START** This is the first code that executes when we run the script **START** #
# ---------------------------------------------------------------------------------#
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("torf").setLevel(logging.INFO)
    logging.getLogger("rebulk.rules").setLevel(logging.INFO)
    logging.getLogger("rebulk.rebulk").setLevel(logging.INFO)
    logging.getLogger("rebulk.processors").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.debug(f"Arguments provided by user for reupload: {args}")

# the `prepare_tracker_api_keys_dict` prepares the api_keys_dict and also does mandatory property validations
api_keys_dict = utils.prepare_and_validate_tracker_api_keys_dict('./parameters/tracker/api_keys.json')

# getting the list of trackers that the user wants to upload to.
# If there are any configuration errors for a particular tracker, then they'll not be used
upload_to_trackers = utils.get_and_validate_configured_trackers(args.trackers, args.all_trackers, api_keys_dict, acronym_to_tracker.keys())

console.line(count=2)
utils.display_banner("  Auto  ReUploader  ")
console.line(count=1)

console.line(count=2)
console.rule("Establishing Connections", style='red', align='center')
console.line(count=1)

logging.info("[Main] Going to establish connection to the torrent client configured")
# getting an instance of the torrent client factory
torrent_client_factory = TorrentClientFactory()
# creating the torrent client using the factory based on the users configuration
torrent_client = torrent_client_factory.create(Clients[os.getenv('client')])
# checking whether the torrent client connection has been created successfully or not
torrent_client.hello()
logging.info(f"[Main] Successfully established connection to the torrent client {os.getenv('client')}")


logging.info("[Main] Going to establish connection to the cache server configured")
# creating an instance of cache based on the users configuration
# TODO if user hasn't provided any configuration then we need to use some other means to keep track
# of these metadata
# getting an instance of the torrent client factory
cache_client_factory = CacheFactory()
# creating the torrent client using the factory based on the users configuration
cache = cache_client_factory.create(CacheVendor[os.getenv('cache_type')])
# checking whether the cache connection has been created successfully or not
cache.hello()
logging.info("[Main] Successfully established connection to the cache server configured")
# now that we have verified that the client and cache connections have been created successfully
# we can start the reupload job
# At the end of this file xD


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

    # -------- format the torrent title --------
    torrent_info["torrent_title"] = translation_utilities.format_title(config, torrent_info)

    # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
    try:
        return search_for_dupes_api(
            acronym_to_tracker[str(tracker).lower()],
            imdb=torrent_info["imdb"],
            tmdb=torrent_info["tmdb"],
            tvmaze=torrent_info["tvmaze"],
            torrent_info=torrent_info,
            tracker_api=temp_tracker_api_key,
            debug=args.debug,
            working_folder=working_folder,
            auto_mode=auto_mode
        )
    except Exception as e:
        logging.exception(f'[Main] Error occured while performing dupe check for tracker {tracker}. Error: {e}')
        console.print("[bold red]Unexpected error occured while performing dupe check. Assuming dupe exists on tracker and skipping[/bold red]")
        return True  # marking that dupes are present in the tracker


# ---------------------------------------------------------------------- #
#                             Upload that shit!                          #
# ---------------------------------------------------------------------- #
def upload_to_site(upload_to, tracker_api_key, config, tracker_settings):
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
                logging.info(f"[TrackerUpload] Upload to {upload_to} was a success!")
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True, response.json()
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical(f"[TrackerUpload] Upload to {upload_to} failed")
                return False, response.json()
        elif "status" in response.json():
            if str(response.json()["status"]).lower() == "true" or str(response.json()["status"]).lower() == "success":
                logging.info(f"[TrackerUpload] Upload to {upload_to} was a success!")
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True, response.json()
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical(f"[TrackerUpload] Upload to {upload_to} failed")
                return False, response.json()
        elif "success" in str(response.json()).lower():
            if str(response.json()["success"]).lower() == "true":
                logging.info(f"[TrackerUpload] Upload to {upload_to} was a success!")
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True, response.json()
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical(f"[TrackerUpload] Upload to {upload_to} failed")
                return False, response.json()
        elif "status" in str(response.json()).lower():
            if str(response.json()["status"]).lower() == "true":
                logging.info(f"[TrackerUpload] Upload to {upload_to} was a success!")
                console.line(count=2)
                console.rule(f"\n :thumbsup: Successfully uploaded to {upload_to} :balloon: \n", style='bold green1', align='center')
                return True, response.json()
            else:
                console.print('Upload to tracker failed.', style='bold red')
                logging.critical(f"[TrackerUpload] Upload to {upload_to} failed")
                return False, response.json()
        else:
            console.print('Upload to tracker failed.', style='bold red')
            logging.critical(f"[TrackerUpload] Something really went wrong when uploading to {upload_to} and we didn't even get a 'success' json key")
            return False, response.json()

    elif response.status_code == 404:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print('Upload failed', style='bold red')
        logging.critical(f"[TrackerUpload] 404 was returned on that upload, this is a problem with the site ({upload_to})")
        logging.error("[TrackerUpload] Upload failed")
        return False, response.status_code

    elif response.status_code == 500:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The upload might have [red]failed[/], the site isn't returning the uploads status")
        # This is to deal with the 500 internal server error responses BLU has been recently returning
        logging.error(f"[TrackerUpload] HTTP response status code '{response.status_code}' was returned (500=Internal Server Error)")
        logging.info("[TrackerUpload] This doesn't mean the upload failed, instead the site simply isn't returning the upload status")
        return False, response.status_code

    elif response.status_code == 400:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print('Upload failed.', style='bold red')
        try:
            logging.critical(
                f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({upload_to}). Error: Error {response.json()["error"] if "error" in response.json() else response.json()}')
        except Exception:
            logging.critical(f'[TrackerUpload] 400 was returned on that upload, this is a problem with the site ({upload_to}).')
        logging.error("[TrackerUpload] Upload failed")
        return False, response.status_code

    else:
        console.print(f'[bold]HTTP response status code: [red]{response.status_code}[/red][/bold]')
        console.print("The status code isn't [green]200[/green] so something failed, upload may have failed")
        logging.error('[TrackerUpload] Status code is not 200, upload might have failed')
        return False, "Unknown Error"
# -------------- END of upload_to_site --------------


# ---------------------------------------------------------------------- #
#                          Analysing basic details!                      #
# ---------------------------------------------------------------------- #
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
    keys_we_need_torrent_info = ['screen_size', 'source', 'audio_channels', 'type']

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

    torrent_info["release_group"] = utils.sanitize_release_group_from_guessit(torrent_info)

    if "type" not in torrent_info:
        raise AssertionError("'type' is not set in the guessit output, something is seriously wrong with this filename")

    # ------------ Format Season & Episode (Goal is 'S01E01' type format) ------------ #
    # Depending on if this is a tv show or movie we have some other 'required' keys that we need (season/episode)
    # guessit uses 'episode' for all tv related content (including seasons)
    if torrent_info["type"] == "episode":
        s00e00, season_number, episode_number, complete_season, individual_episodes, daily_episodes = basic_utilities.basic_get_episode_basic_details(guess_it_result)
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
        # if args.disc: TODO uncomment this for full disk auto uploads
        #     # validating presence of bdinfo script for bare metal
        #     bdinfo_validate_bdinfo_script_for_bare_metal(bdinfo_script)
        #     # validating presence of BDMV/STREAM/
        #     bdinfo_validate_presence_of_bdmv_stream(torrent_info["upload_media"])

        #     raw_video_file, largest_playlist = bdinfo_get_largest_playlist(bdinfo_script, auto_mode, torrent_info["upload_media"])

        #     torrent_info["raw_video_file"] = raw_video_file
        #     torrent_info["largest_playlist"] = largest_playlist
        # else:
        raw_video_file = basic_utilities.basic_get_raw_video_file(torrent_info['upload_media'])
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
    # if args.disc: TODO uncomment this for full disk auto uploads
    #     bdinfo_start_time = time.perf_counter()
    #     logging.debug(f"Generating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}")
    #     console.print(f"\nGenerating and parsing the BDInfo for playlist {torrent_info['largest_playlist']}\n", style='bold blue')
    #     torrent_info["mediainfo"] = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}mediainfo.txt'
    #     torrent_info["bdinfo"] = bdinfo_generate_and_parse_bdinfo(bdinfo_script, working_folder, torrent_info) # TODO handle non-happy paths
    #     logging.debug(f"::::::::::::::::::::::::::::: Parsed BDInfo output :::::::::::::::::::::::::::::")
    #     logging.debug(f"\n{pformat(torrent_info['bdinfo'])}")
    #     bdinfo_end_time = time.perf_counter()
    #     logging.debug(f"Time taken for full bdinfo parsing :: {(bdinfo_end_time - bdinfo_start_time)}")
    # else:

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
    media_info_result = basic_utilities.basic_get_mediainfo(parse_me)

    # if args.disc: TODO uncomment this for full disk auto uploads
    #     # for full disk uploads the bdinfo summary itself will be set as the `mediainfo_summary`
    #     logging.info("[Main] Full Disk Upload. Setting bdinfo summary as mediainfo summary")
    #     with open(f'{working_folder}/temp_upload/{torrent_info["working_folder"]}mediainfo.txt', 'r') as summary:
    #         bdInfo_summary = summary.read()
    #         torrent_info["mediainfo_summary"] = bdInfo_summary
    # else:
    mediainfo_summary, tmdb, imdb, _ = basic_utilities.basic_get_mediainfo_summary(media_info_result.to_data())
    torrent_info["mediainfo_summary"] = mediainfo_summary
    if tmdb != "0":
        # we will get movie/12345 or tv/12345 => we only need 12345 part.
        tmdb = tmdb[tmdb.find("/") + 1:] if tmdb.find("/") >= 0 else tmdb
        torrent_info['tmdb'] = tmdb
        logging.info(f"[Main] Obtained TMDB Id from mediainfo summary. Proceeding with {torrent_info['tmdb']}")
    if imdb != "0":
        torrent_info['imdb'] = imdb
        logging.info(f"[Main] Obtained IMDB Id from mediainfo summary. Proceeding with {torrent_info['imdb']}")

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
            torrent_info_key_failsafe = (torrent_info[column_query_key] if column_query_key !='type' else presentable_type) if column_query_key in torrent_info else None
            logging.debug(f"Getting value for {column_query_key} with display {column_display_value} as {torrent_info_key_failsafe} for the torrent details result table")
            basic_info.append(torrent_info_key_failsafe)

    codec_result_table.add_row(*basic_info)

    console.line(count=2)
    console.print(codec_result_table, justify='center')
    console.line(count=1)
# -------------- END of identify_type_and_basic_info --------------


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

    # !!! [ Block tests/probes start now ] !!!

    # ------------------- Source ------------------- #
    if missing_value == "source":
        # source, source_type, user_input_source = basic_utilities.basic_get_missing_source(torrent_info, args.disc, auto_mode, missing_value)
        source, source_type, user_input_source = basic_utilities.basic_get_missing_source(torrent_info, False, auto_mode, missing_value)
        torrent_info["source"] = source
        torrent_info["source_type"] = source_type
        return user_input_source

    # ---------------- Video Resolution ---------------- #
    if missing_value == "screen_size":
        # return basic_utilities.basic_get_missing_screen_size(torrent_info, args.disc, media_info_video_track, auto_mode, missing_value)
        return basic_utilities.basic_get_missing_screen_size(torrent_info, False, media_info_video_track, auto_mode, missing_value)

    # ---------------- Audio Channels ---------------- #
    if missing_value == "audio_channels":
        # return basic_utilities.basic_get_missing_audio_channels(torrent_info, args.disc, auto_mode, parse_me, media_info_audio_track, missing_value)
        return basic_utilities.basic_get_missing_audio_channels(torrent_info, False, auto_mode, parse_me, media_info_audio_track, missing_value)

    # ---------------- Audio Codec ---------------- #
    if missing_value == "audio_codec":
        # audio_codec, atmos =  basic_utilities.basic_get_missing_audio_codec(torrent_info=torrent_info, is_disc=args.disc, auto_mode=auto_mode,
        audio_codec, atmos = basic_utilities.basic_get_missing_audio_codec(
            torrent_info=torrent_info,
            is_disc=False,
            auto_mode=auto_mode,
            audio_codec_file_path=f'{working_folder}/parameters/audio_codecs.json',
            media_info_audio_track=media_info_audio_track,
            parse_me=parse_me,
            missing_value=missing_value
        )

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
            is_disc=False,
            auto_mode=auto_mode,
            media_info_video_track=media_info_video_track,
            force_pymediainfo=args.force_pymediainfo
        )
        if dv is not None:
            torrent_info["dv"] = dv
        if hdr is not None:
            torrent_info["hdr"] = hdr
        return video_codec
# -------------- END of analyze_video_file --------------


# ---------------------------------------------------------------------- #
#                      Analysing miscellaneous details!                  #
# ---------------------------------------------------------------------- #
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
        torrent_info["source_type"] = miscellaneous_utilities.miscellaneous_identify_source_type(
            torrent_info["raw_file_name"], auto_mode, torrent_info["source"])

    # ------ WEB streaming service stuff here ------ #
    if torrent_info["source"] == "Web":
        # TODO check whether None needs to be set as `web_source`
        torrent_info["web_source"] = miscellaneous_utilities.miscellaneous_identify_web_streaming_source(f'{working_folder}/parameters/streaming_services.json', torrent_info["raw_file_name"], guess_it_result)

    # --- Custom & extra info --- #
    # some torrents have 'extra' info in the title like 'repack', 'DV', 'UHD', 'Atmos', 'remux', etc
    # We simply use regex for this and will add any matches to the dict 'torrent_info', later when building the final title we add any matches (if they exist) into the title
    # repacks
    torrent_info["repack"] = miscellaneous_utilities.miscellaneous_identify_repacks(torrent_info["raw_file_name"])

    # --- Bluray disc type --- #
    if torrent_info["source_type"] == "bluray_disc":
        torrent_info["bluray_disc_type"] = miscellaneous_utilities.miscellaneous_identify_bluray_disc_type(torrent_info["screen_size"], torrent_info["upload_media"])

    # Bluray disc regions
    # Regions are read from new json file
    bluray_regions = json.load(
        open(f'{working_folder}/parameters/bluray_regions.json'))

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
    torrent_info["edition"] = miscellaneous_utilities.miscellaneous_identify_bluray_edition(torrent_info["upload_media"])

    # --------- Fix scene group tags --------- #
    # Whilst most scene group names are just capitalized but occasionally as you can see ^^ some are not (e.g. KOGi)
    # either way we don't want to be capitalizing everything (e.g. we want 'NTb' not 'NTB') so we still need a dict of scene groups and their proper capitalization
    if "release_group" in torrent_info:
        scene, release_group = miscellaneous_utilities.miscellaneous_perform_scene_group_capitalization(f'{working_folder}/parameters/scene_groups.json', torrent_info["release_group"])
        torrent_info["release_group"] = release_group
        torrent_info["scene"] = scene

    # --------- SD? --------- #
    res = re.sub("[^0-9]", "", torrent_info["screen_size"])
    if int(res) < 720:
        torrent_info["sd"] = 1
# -------------- END of identify_miscellaneous_details --------------



# ---------------------------------------------------------------------- #
#                               Reupload Job!                            #
# ---------------------------------------------------------------------- #
def reupload_job():
    logging.info(f'[Main] Starting reupload job at {datetime.now()}')

    torrents = reupload_utilities.reupload_get_processable_torrents(torrent_client, cache)

    if torrents is None or len(torrents) == 0:
        logging.info('[Main] There are no completed torrents for reuploading. Snoozing...')
        return

    logging.info(f'[Main] There are a total of {len(torrents)} completed torrents that needs to be re-uploaded')

    for torrent in torrents:
        # for each completed torrents we start the processing
        logging.info(f'[Main] Starting processing of torrent {torrent["name"]} from path {torrent["save_path"]}')

        cached_data = reupload_utilities.get_cached_data(torrent["hash"], cache)
        logging.debug(f"[Main] Cached data obtained from cache for torrent {torrent['hash']}: {pformat(cached_data)}")
        if cached_data is None:
            # Initializing the torrent data to cache
            reupload_utilities.initialize_torrent_data(torrent, cache)
        else:
            logging.info(f"[Main] Cached data found for torrent with hash {torrent['hash']}")
            if reupload_utilities.should_upload_be_skipped(cache, cached_data):
                logging.info(f"[Main] Skipping upload and processing of torrent {cached_data['name']} since retry limit has exceeded")
                continue

        # dynamic_tracker_selection
        upload_to_trackers_working = reupload_utilities.get_available_dynamic_trackers(
            torrent_client=torrent_client,
            torrent=torrent,
            original_upload_to_trackers=upload_to_trackers,
            api_keys_dict=api_keys_dict,
            all_trackers_list=acronym_to_tracker.keys()
        )
        logging.info(f"[Main] Trackers this torrent needs to be uploaded to are {upload_to_trackers_working}")

        save_path = torrent["save_path"]
        # before we start doing anything we need to check whether the media file can be accessed by the uploader.
        # to check whether the file is accessible we need to adhere to any path translations that user want to do
        torrent_path = reupload_utilities.reupload_get_translated_torrent_path(torrent["content_path"])

        torrent_info.clear()
        # Remove all old temp_files & data from the previous upload
        torrent_info["working_folder"] = utils.delete_leftover_files(working_folder, file=torrent_path, resume=False)

        console.print(f'Re-Uploading File/Folder: [bold][blue]{torrent_path}[/blue][/bold]')

        rar_file_validation_response = utils.check_for_dir_and_extract_rars(torrent_path)
        if not rar_file_validation_response[0]:
            # status is False, due to some error and hence we'll skip this upload
            # Skip this entire 'file upload' & move onto the next (if exists)
            continue
        torrent_info["upload_media"] = rar_file_validation_response[1]

        guess_it_result = utils.perform_guessit_on_filename(torrent_info["upload_media"])

        nfo = glob.glob(f"{torrent_info['upload_media']}/*.nfo")
        if nfo and len(nfo) > 0:
            torrent_info["nfo_file"] = nfo[0]

        # File we're uploading
        console.print(f'Uploading File/Folder: [bold][blue]{torrent_path}[/blue][/bold]')
        # -------- Basic info --------
        # So now we can start collecting info about the file/folder that was supplied to us (Step 1)
        # this guy will also try to set tmab and imdb from media info summary
        if identify_type_and_basic_info(torrent_info["upload_media"], guess_it_result) == 'skip_to_next_file':
            # If there is an issue with the file & we can't upload we use this check to skip the current file & move on to the next (if exists)
            logging.debug(f"[Main] Skipping {torrent_info['upload_media']} because type and basic information cannot be identified.")
            continue

        # -------- Fix/update values --------
        # set the correct video & audio codecs (Dolby Digital --> DDP, use x264 if encode vs remux etc)
        identify_miscellaneous_details(guess_it_result)

        # the metadata items will be first obtained from cached_data. if its not available then we'll go ahead with mediainfo_summary data and tmdb search
        movie_db = reupload_utilities.reupload_get_movie_db_from_cache(cache, cached_data, torrent_info["title"], torrent_info["year"] if "year" in torrent_info else "", torrent_info["type"])

        metadata_tmdb = reupload_utilities.reupload_get_external_id_based_on_priority(movie_db, torrent_info, cached_data, "tmdb")
        metadata_imdb = reupload_utilities.reupload_get_external_id_based_on_priority(movie_db, torrent_info, cached_data, "imdb")
        metadata_tvmaze = reupload_utilities.reupload_get_external_id_based_on_priority(movie_db, torrent_info, cached_data, "tvmaze")

        # tmdb, imdb and tvmaze in torrent_info will be filled by this method
        possible_matches = metadata_utilities.fill_database_ids(torrent_info, [metadata_tmdb], [metadata_imdb], [metadata_tvmaze], auto_mode)

        if torrent_info["tmdb"] == "0" and torrent_info["imdb"] == "0" and torrent_info["tvmaze"] == "0":
            # here we couldn't select a tmdb id automatically / no results from tmdb. Hence we mark this as a special case and stop the upload of the torrent
            # updating the voerall status of the torrent
            reupload_utilities.update_field(torrent["hash"], "status", reupload_utilities.TorrentStatus.TMDB_IDENTIFICATION_FAILED, False, cache)
            reupload_utilities.update_field(torrent["hash"], "possible_matches", possible_matches, True, cache)
            continue

        original_title = torrent_info["title"]
        original_year = torrent_info["year"] if "year" in torrent_info else ""

        # -------- Use official info from TMDB --------
        title, year, tvdb, mal = metadata_utilities.metadata_compare_tmdb_data_local(torrent_info)
        torrent_info["title"] = title
        if year is not None:
            torrent_info["year"] = year
        # TODO try to move the tvdb and mal identification along with `metadata_get_external_id`
        torrent_info["tvdb"] = tvdb
        torrent_info["mal"] = mal

        # saving the updates to moviedb in cache
        reupload_utilities.reupload_persist_updated_moviedb_to_cache(cache, movie_db, torrent_info, torrent["hash"], original_title, original_year)

        # Fix some default naming styles
        translation_utilities.fix_default_naming_styles(torrent_info)

        # -------- Dupe check for single tracker uploads --------
        # If user has provided only one Tracker to upload to, then we do dupe check prior to taking screenshots. [if dupe_check is enabled]
        # If there are duplicates in the tracker, then we do not waste time taking and uploading screenshots.
        if os.getenv('check_dupes') == 'true' and len(upload_to_trackers_working) == 1:
            tracker = upload_to_trackers_working[0]
            temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]

            console.line(count=2)
            console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')

            dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
            # If dupes are present and user decided to stop upload, for single tracker uploads we stop operation immediately
            # True == dupe_found
            # False == no_dupes/continue upload
            if dupe_check_response:
                logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
                logging.info("[Main] Marking this torrent as dupe check failed in cache")
                reupload_utilities.update_torrent_status(torrent["hash"], reupload_utilities.TorrentStatus.DUPE_CHECK_FAILED, cache)
                torrent_client.update_torrent_category(info_hash=torrent["hash"], category_name=reupload_utilities.TorrentStatus.DUPE_CHECK_FAILED)
                console.print("Dupe check failed. skipping this torrent upload..\n",style="bold red", highlight=False)
                continue

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

        # This flag will be set if upload can be performed on atleast one tracker.
        # If the upload cannot be performed on all the configured tracker. then the torrent in client will be moved to dupe check failed status.
        # If the user has configured only one tracker, then dupe will not reach here.
        # single tracker dupe check is handled prior to screenshot generation
        is_non_dupes_present = False
        for tracker in upload_to_trackers_working:

            torrent_info["shameless_self_promotion"] = f'Uploaded with {"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"} using GG-BOT Auto-ReUploader'

            temp_tracker_api_key = api_keys_dict[f"{str(tracker).lower()}_api_key"]
            logging.info(f"[Main] Trying to upload to: {tracker}")

            # Create a new dictionary that we store the exact keys/vals that the site is expecting
            tracker_settings = {}
            tracker_settings.clear()

            # Open the correct .json file since we now need things like announce URL, API Keys, and API info
            with open("{}/site_templates/".format(working_folder) + str(acronym_to_tracker.get(str(tracker).lower())) + ".json", "r", encoding="utf-8") as config_file:
                config = json.load(config_file)

            # -------- format the torrent title --------
            torrent_info["torrent_title"] = translation_utilities.format_title(config, torrent_info)

            # (Theory) BHD has a different bbcode parser then BLU/ACM so the line break is different for each site
            # this is why we set it in each sites *.json file then retrieve it here in this 'for loop' since its different for each site
            bbcode_line_break = config['bbcode_line_break']

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
            if os.getenv('check_dupes') == 'true' and len(upload_to_trackers_working) > 1:
                console.line(count=2)
                console.rule(f"Dupe Check [bold]({tracker})[/bold]", style='red', align='center')
                # Call the function that will search each site for dupes and return a similarity percentage, if it exceeds what the user sets in config.env we skip the upload
                dupe_check_response = check_for_dupes_in_tracker(tracker, temp_tracker_api_key)
                # True == dupe_found
                # False == no_dupes/continue upload
                if dupe_check_response:
                    logging.error(f"[Main] Could not upload to: {tracker} because we found a dupe on site")
                    # If dupe was found & the script is auto_mode OR if the user responds with 'n' for the 'dupe found, continue?' prompt
                    # we will essentially stop the current 'for loops' iteration & jump back to the beginning to start next cycle (if exists else quits)
                    continue

            is_non_dupes_present = True
            # -------- Generate .torrent file --------
            console.print(f'\n[bold]Generating .torrent file for [chartreuse1]{tracker}[/chartreuse1][/bold]')
            logging.debug(f'[Main] Torrent info just before dot torrent creation. \n {pformat(torrent_info)}')
            # If the type is a movie, then we only include the `raw_video_file` for torrent file creation.
            # If type is an episode, then we'll create torrent file for the the `upload_media` which could be an single episode or a season folder
            if torrent_info["type"] == "movie" and "raw_video_file" in torrent_info:
                torrent_media = torrent_info["raw_video_file"]
            else:
                torrent_media = torrent_info["upload_media"]

            torrent_utilities.generate_dot_torrent(
                media=torrent_media,
                announce=list(os.getenv(f"{str(tracker).upper()}_ANNOUNCE_URL").split(" ")),
                source=config["source"],
                working_folder=working_folder,
                hash_prefix=torrent_info["working_folder"],
                use_mktorrent=args.use_mktorrent,
                tracker=tracker,
                torrent_title=torrent_info["torrent_title"]
            )

            # -------- Assign specific tracker keys --------
            # This function takes the info we have the dict torrent_info and associates with the right key/values needed for us to use X trackers API
            # if for some reason the upload cannot be performed to the specific tracker, the method returns "STOP"
            if translation_utilities.choose_right_tracker_keys(config, tracker_settings, tracker, torrent_info, args, working_folder) == "STOP":
                continue

            logging.debug("::::::::::::::::::::::::::::: Final torrent_info with all data filled :::::::::::::::::::::::::::::")
            logging.debug(f'\n{pformat(torrent_info)}')
            # -------- Upload everything! --------
            # 1.0 everything we do in this for loop isn't persistent, its specific to each site that you upload to
            # 1.1 things like screenshots, TMDB/IMDB ID's can & are reused for each site you upload to
            # 2.0 we take all the info we generated outside of this loop (mediainfo, description, etc) and combine it with tracker specific info and upload it all now
            upload_status, upload_response = upload_to_site(
                upload_to=tracker,
                tracker_api_key=temp_tracker_api_key,
                config=config,
                tracker_settings=tracker_settings
            )

            # Tracker Settings
            if upload_status:
                reupload_utilities.update_success_status_for_torrent_upload(cache, torrent, tracker, upload_response)

                # -------- Post Processing --------
                # TODO do proper post processing steps
                logging.fatal(f'[Main] `upload_media` :: {torrent_info["upload_media"]} `save_path` :: {save_path}')
                if "raw_video_file" in torrent_info:
                    logging.fatal(f'[Main] `raw_video_file` :: {torrent_info["raw_video_file"]}')

                if torrent_info["type"] == "movie":
                    if "raw_video_file" in torrent_info:
                        save_path = torrent_info["upload_media"]
                        logging.info(f'[Main] `raw_video_file` is present in torrent_info. Hence updating client save path to {save_path}')
                    else:
                        save_path = torrent_info["upload_media"].replace(f'/{torrent_info["raw_file_name"]}', '')
                        logging.info(f'[Main] `raw_video_file` is missing in torrent_info. Hence updating client save path to {save_path}')

                torrent_client.upload_torrent(
                    torrent=f'{working_folder}/temp_upload/{torrent_info["working_folder"]}{tracker}-{torrent_info["torrent_title"]}.torrent',
                    save_path=save_path,
                    use_auto_torrent_management=False,
                    is_skip_checking=True
                )
            else:
                reupload_utilities.update_failure_status_for_torrent_upload(cache, torrent, tracker, upload_response)

        # marking dupe check failed torrents
        torrent_client.update_torrent_category(info_hash=torrent["hash"], category_name=None if is_non_dupes_present else reupload_utilities.TorrentStatus.DUPE_CHECK_FAILED)
# -------------- END of reupload_job --------------


# The scheduled job to fetch and parse torrents will be executed every minute
# schedule.every(1).minutes.do(reupload_job)
schedule.every(10).seconds.do(reupload_job)
print(f"Starting reupload process at {datetime.now()}")

while True:
    schedule.run_pending()
