import os
import sys
import json
import glob
import math
import time
import logging
import subprocess

from torf import Torrent
from pathlib import Path
from ffmpy import FFprobe
from pprint import pformat
from guessit import guessit
from datetime import datetime
from dotenv import dotenv_values
from rich.console import Console
from pymediainfo import MediaInfo

console = Console()


def calculate_piece_size(size):
    """
    Return the piece size for a total torrent size of ``size`` bytes

    For torrents up to 1 GiB, the maximum number of pieces is 1024 which
    means the maximum piece size is 1 MiB.  With increasing torrent size
    both the number of pieces and the maximum piece size are gradually
    increased up to 10,240 pieces of 8 MiB.  For torrents larger than 80 GiB
    the piece size is :attr:`piece_size_max` with as many pieces as
    necessary.

    It is safe to override this method to implement a custom algorithm.

    :return: calculated piece size
    """
    if size <= 2**30:          # 1 GiB / 1024 pieces = 1 MiB max
        pieces = size / 1024
    elif size <= 4 * 2**30:    # 4 GiB / 2048 pieces = 2 MiB max
        pieces = size / 2048
    elif size <= 6 * 2**30:    # 6 GiB / 3072 pieces = 2 MiB max
        pieces = size / 3072
    elif size <= 8 * 2**30:    # 8 GiB / 2048 pieces = 4 MiB max
        pieces = size / 2048
    elif size <= 16 * 2**30:   # 16 GiB / 2048 pieces = 8 MiB max
        pieces = size / 2048
    elif size <= 32 * 2**30:   # 32 GiB / 2048 pieces = 16 MiB max
        pieces = size / 2048
    elif size <= 64 * 2**30:   # 64 GiB / 4096 pieces = 16 MiB max
        pieces = size / 4096
    elif size > 64 * 2**30:
        pieces = size / 10240
    # Math is magic!
    # piece_size_max :: 16 * 1024 * 1024 => 16MB
    return int(min(max(1 << max(0, math.ceil(math.log(pieces, 2))), 16 * 1024), 16 * 1024 * 1024))


def generate_dot_torrent(media, announce, source, working_folder, use_mktorrent, tracker, torrent_title, callback=None):
    """
        media : the -p path param passed to GGBot. (dot torrent will be created for this path or file)
    """
    logging.info("[DotTorrentGeneration] Creating the .torrent file now")
    logging.info(f"[DotTorrentGeneration] Primary announce url: {announce[0]}")
    logging.info(f"[DotTorrentGeneration] Source field in info will be set as `{source}`")

    if len(glob.glob(working_folder + "/temp_upload/*.torrent")) == 0:
        # we need to actually generate a torrent file "from scratch"
        logging.info("[DotTorrentGeneration] Generating new .torrent file since old ones doesn't exist")
        if use_mktorrent:
            print("Using mktorrent to generate the torrent")
            logging.info("[DotTorrentGeneration] Using MkTorrent to generate the torrent")
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
            torrent_size = sum(f.stat().st_size for f in Path(media).glob('**/*') if f.is_file()) if os.path.isdir(media) else os.path.getsize(media)
            piece_size = get_piece_size_for_mktorrent(torrent_size)
            logging.info(f'[DotTorrentGeneration] Size of the torrent: {torrent_size}')
            logging.info(f'[DotTorrentGeneration] Piece Size of the torrent: {piece_size}')
            if len(announce) == 1:
                os.system(f"mktorrent -v -p -l 23 -c \"Torrent created by GG-Bot Upload Assistant\" -s '{source}' -a '{announce[0]}' -o \"{working_folder}/temp_upload/{tracker}-{torrent_title}.torrent\" \"{media}\"")
            else:
                os.system(f"mktorrent -v -p -l 23 -c \"Torrent created by GG-Bot Upload Assistant\" -s '{source}' -a '{announce}' -o \"{working_folder}/temp_upload/{tracker}-{torrent_title}.torrent\" \"{media}\"")
            logging.info("[DotTorrentGeneration] Mktorrent .torrent write into {}".format("[" + source + "]" + torrent_title + ".torrent"))
            # torrent_info["dot_torrent"] = f'{working_folder}/temp_upload/{torrent_title}.torrent'
        else:
            print("Using python torf to generate the torrent")
            torrent = Torrent(media,
                              trackers=announce,
                              source=source,
                              comment="Torrent created by GG-Bot Upload Assistant",
                              created_by="GG-Bot Upload Assistant",
                              exclude_globs=["*.txt", "*.jpg", "*.png", "*.nfo", "*.svf", "*.rar", "*.screens","*.sfv"],
                              private=True,
                              creation_date=datetime.now())
            torrent.piece_size=calculate_piece_size(torrent.size)
            logging.info(f'[DotTorrentGeneration] Size of the torrent: {torrent.size}')
            logging.info(f'[DotTorrentGeneration] Piece Size of the torrent: {torrent.piece_size}')
            torrent.generate(callback=callback)
            torrent.write(f'{working_folder}/temp_upload/{tracker}-{torrent_title}.torrent')
            torrent.verify_filesize(media)
            # Save the path to .torrent file in torrent_settings
            # torrent_info["dot_torrent"] = f'{working_folder}/temp_upload/{torrent_title}.torrent'
            logging.info("[DotTorrentGeneration] Trying to write into {}".format("[" + source + "]" + torrent_title + ".torrent"))
    else:
        print("Editing previous .torrent file to work with {} instead of generating a new one".format(source))
        logging.info("[DotTorrentGeneration] Editing previous .torrent file to work with {} instead of generating a new one".format(source))

        # just choose whichever, doesn't really matter since we replace the same info anyways
        edit_torrent = Torrent.read(glob.glob(working_folder + '/temp_upload/*.torrent')[0])

        if len(announce) == 1:
            logging.debug(f"[DotTorrentGeneration] Only one announce url provided for tracker {tracker}.")
            logging.debug(f"[DotTorrentGeneration] Removing announce-list if present in existing torrent.")
            edit_torrent.metainfo.pop('announce-list', "")
        else:
            logging.debug(f"[DotTorrentGeneration] Multiple announce urls provided for tracker {tracker}. Updating announce-list")
            edit_torrent.metainfo.pop('announce-list', "")
            edit_torrent.metainfo['announce-list'] = list()
            for announce_url in announce[1:]:
                logging.debug(f"[DotTorrentGeneration] Adding secondary announce url {announce_url}")
                announce_list = list()
                announce_list.append(announce_url)
                edit_torrent.metainfo['announce-list'].append(announce_list)
            logging.debug(f"[DotTorrentGeneration] Final announce-list in torrent metadata {edit_torrent.metainfo['announce-list']}")

        edit_torrent.metainfo['announce'] = announce[0]
        edit_torrent.metainfo['info']['source'] = source
        # Edit the previous .torrent and save it as a new copy
        Torrent.copy(edit_torrent).write(f'{working_folder}/temp_upload/{tracker}-{torrent_title}.torrent')

    if os.path.isfile(f'{working_folder}/temp_upload/{tracker}-{torrent_title}.torrent'):
        logging.info(f'[DotTorrentGeneration] Successfully created the following file: {working_folder}/temp_upload/{tracker}-{torrent_title}.torrent')
    else:
        logging.error(f'[DotTorrentGeneration] The following .torrent file was not created: {working_folder}/temp_upload/{tracker}-{torrent_title}.torrent')


def write_cutsom_user_inputs_to_description(torrent_info, description_file_path, config, tracker, bbcode_line_break):
    # -------- Add custom descriptions to description.txt --------
    if "custom_user_inputs" in torrent_info:
        # If the user is uploading to multiple sites we don't want to keep appending to the same description.txt file so remove it each time and write clean bbcode to it
        #  (Note, this doesn't delete bbcode_images.txt so you aren't uploading the same images multiple times)
        if os.path.isfile(description_file_path):
            os.remove(description_file_path)
        
        # we need to make sure that the tracker supports custom description for torrents. 
        # If tracker supports custom descriptions, the the tracker config will have the `description_components` key.
        if "description_components" in config:
            logging.debug(f'[CustomUserInputs] User has provided custom inputs for torrent description')
            # here we iterate through all the custom inputs provided by the user
            # then we check whether this component is supported by the target tracker. If tracker supports it then the `key` will be present in the tracker config.
            with open(description_file_path, 'a') as description:
                description_components = config["description_components"]
                logging.debug(f'[CustomUserInputs] Custom Message components configured for tracker {tracker} are {pformat(description_components)}')
                for custom_user_input in torrent_info["custom_user_inputs"]:
                    # getting the component type
                    logging.debug(f'[CustomUserInputs] Custom input data {pformat(custom_user_input)}')
                    if custom_user_input["key"] not in description_components:
                        logging.debug(f'[CustomUserInputs] This type of component is not supported by the tracker. Writing input to description as plain text')
                        # the provided component is not present in the trackers list. hence we adds this to the description directly (plain text)
                        description.write(custom_user_input["value"])
                    else:
                        # provided component is present in the tracker list, so first we'll format the content to be added to the tracker template
                        input_wrapper_type = description_components[custom_user_input["key"]]
                        logging.debug(f'[CustomUserInputs] Component wrapper :: `{input_wrapper_type}`')
                        formatted_value = custom_user_input["value"].replace("\\n", bbcode_line_break)
                        # next we need to check whether the text component has any title
                        if "title" in custom_user_input and custom_user_input["title"] is not None:
                            logging.debug(f'[CustomUserInputs] User has provided a title for this component')
                            # if user has provided title, next we'll make sure that the tracker supports title for the component.
                            if "TITLE_PLACEHOLDER" in input_wrapper_type:
                                logging.debug(f'[CustomUserInputs] Adding title [{custom_user_input["title"].strip()}] to this component')
                                input_wrapper_type = input_wrapper_type.replace("TITLE_PLACEHOLDER", custom_user_input["title"].strip())
                            else:
                                logging.debug(f'[CustomUserInputs] Title is not supported for this component {custom_user_input["key"]} in this tracker {tracker}. Skipping title placement')
                        # in cases where tracker supports title and user hasn't provided any title, we'll just remove the title placeholder
                        # note that the = is intentional. since title would be [spoiler=TITILE]. we need to remove =TITLE
                        # if title has already been repalced the below statement won't do anything
                        input_wrapper_type = input_wrapper_type.replace("=TITLE_PLACEHOLDER", "")

                        if args.debug: # just for debugging purposes
                            if "][" in input_wrapper_type:
                                logging.debug(f'[CustomUserInputs] ][ is present in the wrapper type')
                            logging.debug(f'[CustomUserInputs] Wrapper type before formatting {input_wrapper_type}')

                        final_formatted_data = input_wrapper_type.replace("][", f']{formatted_value}[' if "][" in input_wrapper_type else formatted_value)
                        description.write(final_formatted_data)
                        logging.debug(f'[CustomUserInputs] Formatted value being appended to torrent description {final_formatted_data}')

                    description.write(bbcode_line_break)
        else: # else for "description_components" in config
            logging.debug(f"[Utils] The tracker {tracker} doesn't support custom descriptions. Skipping custom description placements.")


def add_bbcode_images_to_description(torrent_info, config, description_file_path, bbcode_line_break):
    if "bbcode_images" in torrent_info and not ("url_images" in config["translation"] or "url_images" in config["translation"]):
        # Screenshots will be added to description only if no custom screenshot payload method is provided.
        # Possible payload mechanisms for screenshot are 1. bbcode, 2. url, 3. post data
        # TODO implement proper screenshot payload mechanism. [under technical_jargons?????]
        #
        # if custom_user_inputs is already present in torrent info, then the delete operation would have already be done
        # so we just need to append screenshots to the description.txt
        if "custom_user_inputs" not in torrent_info and os.path.isfile(description_file_path):
            os.remove(description_file_path)

        # Now open up the correct files and format all the bbcode/tags below
        with open(torrent_info["bbcode_images"], 'r') as bbcode, open(description_file_path, 'a') as description:
            # First add the [center] tags, "Screenshots" header, Size tags etc etc. This only needs to be written once which is why its outside of the 'for loop' below
            description.write(f'{bbcode_line_break}[center] ---------------------- [size=22]Screenshots[/size] ---------------------- {bbcode_line_break}{bbcode_line_break}')
            # Now write in the actual screenshot bbcode
            for line in bbcode:
                description.write(line)
            description.write("[/center]")


def write_uploader_signature_to_description(description_file_path, tracker, bbcode_line_break):
    # TODO what will happen if custom_user_inputs and bbcode_images are not present
    # will then open throw some errors???
    with open(description_file_path, 'a') as description:
        # Finally append the entire thing with some shameless self promotion ;) and some line breaks
        if os.getenv("uploader_signature") is not None and len(os.getenv("uploader_signature")) > 0:
            logging.debug(f'[Utils] User has provided custom uploader signature to use.')
            # the user has provided a custom signature to be used. hence we'll use that.
            uploader_signature = os.getenv("uploader_signature")
            logging.debug(f'[Utils] User provided signature :: {uploader_signature}')
            if not uploader_signature.startswith("[center]") and not uploader_signature.endswith("[/center]"):
                uploader_signature = f'[center]{uploader_signature}[/center]'
            uploader_signature = f'{uploader_signature}{bbcode_line_break}[center]Powered by GG-BOT Upload Assistant[/center]'
            description.write(f'{bbcode_line_break}{bbcode_line_break}{uploader_signature}')
        else:
            logging.debug(f'[Utils] User has not provided any custom uploader signature to use. Using default signature')
            description.write(f'{bbcode_line_break}{bbcode_line_break}[center] Uploaded with [color=red]{"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"}[/color] using GG-BOT Upload Assistant[/center]')


def has_user_provided_type(user_type):
    if user_type:
        if user_type[0] in ('tv', 'movie'):
            logging.info(f"Using user provided type {user_type[0]}")
            return True
        else:
            logging.error(f'User has provided invalid media type as argument {user_type[0]}. Type will be detected dynamically!')
            return False
    else:
        logging.info("Type not provided by user. Type will be detected dynamically!")
        return False


def delete_leftover_files(working_folder):
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
            logging.info("[Utils] Deleted the contents of the folder: {}".format(working_folder + old_temp_data))


def write_file_contents_to_log_as_debug(file_path):
    """
        Method reads and writes the contents of the provided `file_path` to the log as debug lines.
        note that the method doesn't check for debug mode or not, those checks needs to be done by the caller
    """
    with open(file_path, 'r') as file_contents:
        lines = file_contents.readlines()
        [ logging.debug(line.replace('\\n','').strip()) for line in lines ]

        
def perform_guessit_on_filename(file_name):
    guessit_start_time = time.perf_counter()
    
    if file_name.endswith("/"):
        file_name_split = file_name[0:len(file_name) - 1].split("/")
    else:
        file_name_split = file_name.split("/")
    file_name = file_name_split[len(file_name_split) - 1]

    guess_it_result = guessit(file_name)
    guessit_end_time = time.perf_counter()
    logging.debug(f'[Utils] Time taken for guessit regex operations :: {guessit_end_time - guessit_start_time}')
    logging.debug("::::::::::::::::::::::::::::: GuessIt output result :::::::::::::::::::::::::::::")
    logging.debug(f'\n{pformat(guess_it_result)}')
    return guess_it_result


def check_for_dir_and_extract_rars(file_path):
    """
        Return values -> Status, Actual File Path
        
        Status indicates whether the file/folder validation was performed successfully.
        I case of any errors, status will be false and the upload of that file can be skipped
    """
    # If the path the user specified is a folder with .rar files in it then we unpack the video file & set the torrent_info key equal to the extracted video file
    if os.path.isdir(file_path):
        logging.info(f"[Utils] User wants to upload a folder: {file_path}")

        # Now we check to see if the dir contains rar files
        rar_file = glob.glob(f"{os.path.join(file_path, '')}*rar")
        if rar_file:
            logging.info(f"[Utils] '{file_path}' is a .rar archive, extracting now...")
            logging.info(f"[Utils] Rar file: {rar_file[0]}")

            # Now verify that unrar is installed
            unrar_sys_package = '/usr/bin/unrar'
            if os.path.isfile(unrar_sys_package):
                logging.info("[Utils] Found 'unrar' system package, Using it to extract the video file now")
                
                # run the system package unrar and save the extracted file to its parent dir
                subprocess.run([unrar_sys_package, 'e', rar_file[0], file])
                logging.debug(f"[Utils] Successfully extracted file : {rar_file[0]}")

                # This is how we identify which file we just extracted (Last modified)
                list_of_files = glob.glob(f"{os.path.join(file, '')}*")
                latest_file = max(list_of_files, key=os.path.getctime)

                logging.info(f"[Utils] Using the extracted {latest_file} for further processing")
                # the value for 'upload_media' with the path to the video file we just extracted
                return True, latest_file
            else:
                # If the user doesn't have unrar installed then we let them know here and move on to the next file (if exists)
                console.print('unrar is not installed, Unable to extract the rar archinve\n', style='bold red')
                logging.critical('[Utils] `unrar` is not installed, Unable to extract rar archive')
                logging.info('[Utils] Perhaps first try "sudo apt-get install unrar" then run this script again')
                return False, file_path # Skip this entire 'file upload' & move onto the next (if exists)
        return True, file_path
    else:
        logging.info(f'[Utils] Uploading the following file: {file_path}')
        return True, file_path


def prepare_and_validate_tracker_api_keys_dict(api_keys_file_path):
    api_keys = json.load(open(api_keys_file_path))
    api_keys_dict = dict()
    for i in range (0, len(api_keys)):
        api_keys_dict[api_keys[i]] = os.getenv(api_keys[i].upper())

    # Make sure the TMDB API is provided [Mandatory Property]
    try:
        if len(api_keys_dict['tmdb_api_key']) == 0:
            raise AssertionError("TMDB API key is required")
    except AssertionError as err:  # Log AssertionError in the logfile and quit here
        logging.exception("TMDB API Key is required")
        raise err

    return api_keys_dict


def validate_env_file(sample_env_location):
    sample_env_keys = dotenv_values(sample_env_location).keys()
    # validating env file with expected keys from sample file
    for key in sample_env_keys:
        if os.getenv(key) is None:
            console.print(f"Outdated config.env file. Variable [red][bold]{key}[/bold][/red] is missing.", style="blue")
            logging.error(f"Outdated config.env file. Variable {key} is missing.")


def get_and_validate_configured_trackers(trackers, all_trackers, api_keys_dict, all_trackers_list):
    upload_to_trackers = []

    tracker_list = all_trackers_list
    if all_trackers: # user wants to upload to all the trackers possible
        logging.info(f"[Utils] User has chosen to upload to add possible trackers: {tracker_list}")
    else:
        logging.info("[Utils] Attempting check and validate and default trackers configured")
        tracker_list = os.getenv("default_trackers_list") or ""
        if len(tracker_list) > 0:
            tracker_list= [ x.strip() for x in tracker_list.split(',') ]

    for tracker in trackers or tracker_list or []:
        if "{tracker}_api_key".format(tracker=str(tracker).lower()) in api_keys_dict:
            # Make sure that an API key is set for that site
            try:
                if len(api_keys_dict[(str(tracker).lower()) + "_api_key"]) <= 1:
                    raise AssertionError("Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)")
                if str(tracker).upper() not in upload_to_trackers : upload_to_trackers.append(str(tracker).upper())
            except AssertionError as err:
                logging.error("[Utils] We can't upload to '{}' because that sites API key is not specified".format(tracker))
        else:
            logging.error("[Utils] We can't upload to '{}' because that site is not supported".format(tracker))

    # Make sure that the user provides at least 1 valid tracker we can upload to
    try:
        # if len(upload_to_trackers) == 0 that means that the user either didn't provide any site at all, the site is not supported, or the API key isn't provided
        if len(upload_to_trackers) < 1:
            raise AssertionError("Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)")
    except AssertionError as err:  # Log AssertionError in the logfile and quit here
        logging.exception("[Utils] No valid trackers specified for upload destination (e.g. BHD, BLU, ACM)")
        raise err

    logging.debug(f"[Utils] Trackers selected by bot: {upload_to_trackers}")
    return upload_to_trackers
