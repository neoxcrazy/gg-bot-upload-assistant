import os
import json
import glob
import time
import shutil
import hashlib
import logging
import pyfiglet
import subprocess

from pathlib import Path
from pprint import pformat
from guessit import guessit
from dotenv import dotenv_values
from rich.console import Console

from modules.torrent_client import Clients, TorrentClientFactory


console = Console()


def get_hash(string):
    hashed = hashlib.new('sha256')
    hashed.update(string.encode())
    return hashed.hexdigest()


def write_cutsom_user_inputs_to_description(torrent_info, description_file_path, config, tracker, bbcode_line_break, debug=False):
    # -------- Add custom descriptions to description.txt --------
    if "custom_user_inputs" in torrent_info:
        # If the user is uploading to multiple sites we don't want to keep appending to the same description.txt file so remove it each time and write clean bbcode to it
        #  (Note, this doesn't delete bbcode_images.txt so you aren't uploading the same images multiple times)
        if os.path.isfile(description_file_path):
            os.remove(description_file_path)

        # we need to make sure that the tracker supports custom description for torrents.
        # If tracker supports custom descriptions, the the tracker config will have the `description_components` key.
        if "description_components" in config:
            logging.debug('[CustomUserInputs] User has provided custom inputs for torrent description')
            # here we iterate through all the custom inputs provided by the user
            # then we check whether this component is supported by the target tracker. If tracker supports it then the `key` will be present in the tracker config.
            with open(description_file_path, 'a') as description:
                description_components = config["description_components"]
                logging.debug(f'[CustomUserInputs] Custom Message components configured for tracker {tracker} are {pformat(description_components)}')
                for custom_user_input in torrent_info["custom_user_inputs"]:
                    # getting the component type
                    logging.debug(f'[CustomUserInputs] Custom input data {pformat(custom_user_input)}')
                    if custom_user_input["key"] not in description_components:
                        logging.debug('[CustomUserInputs] This type of component is not supported by the tracker. Writing input to description as plain text')
                        # the provided component is not present in the trackers list. hence we adds this to the description directly (plain text)
                        description.write(custom_user_input["value"])
                    else:
                        # provided component is present in the tracker list, so first we'll format the content to be added to the tracker template
                        input_wrapper_type = description_components[custom_user_input["key"]]
                        logging.debug(f'[CustomUserInputs] Component wrapper :: `{input_wrapper_type}`')
                        formatted_value = custom_user_input["value"].replace("\\n", bbcode_line_break)
                        # next we need to check whether the text component has any title
                        if "title" in custom_user_input and custom_user_input["title"] is not None:
                            logging.debug('[CustomUserInputs] User has provided a title for this component')
                            # if user has provided title, next we'll make sure that the tracker supports title for the component.
                            if "TITLE_PLACEHOLDER" in input_wrapper_type:
                                logging.debug(f'[CustomUserInputs] Adding title [{custom_user_input["title"].strip()}] to this component')
                                input_wrapper_type = input_wrapper_type.replace("TITLE_PLACEHOLDER", custom_user_input["title"].strip())
                            else:
                                logging.debug(
                                    f'[CustomUserInputs] Title is not supported for this component {custom_user_input["key"]} in this tracker {tracker}. Skipping title placement')
                        # in cases where tracker supports title and user hasn't provided any title, we'll just remove the title placeholder
                        # note that the = is intentional. since title would be [spoiler=TITILE]. we need to remove =TITLE
                        # if title has already been repalced the below statement won't do anything
                        input_wrapper_type = input_wrapper_type.replace("=TITLE_PLACEHOLDER", "")

                        if debug:  # just for debugging purposes
                            if "][" in input_wrapper_type:
                                logging.debug('[CustomUserInputs] ][ is present in the wrapper type')
                            elif "><" in input_wrapper_type:
                                logging.debug('[CustomUserInputs] >< is present in the wrapper type')
                            else:
                                logging.debug('[CustomUserInputs] No special characters present in the wrapper type')
                            logging.debug(f'[CustomUserInputs] Wrapper type before formatting {input_wrapper_type}')

                        if "][" in input_wrapper_type:
                            final_formatted_data = input_wrapper_type.replace("][", f']{formatted_value}[')
                        elif "><" in input_wrapper_type:
                            final_formatted_data = input_wrapper_type.replace("><", f'>{formatted_value}<')
                        else:
                            final_formatted_data = formatted_value
                        description.write(final_formatted_data)
                        logging.debug(f'[CustomUserInputs] Formatted value being appended to torrent description {final_formatted_data}')

                    description.write(bbcode_line_break)
        else:  # else for "description_components" in config
            logging.debug(f"[Utils] The tracker {tracker} doesn't support custom descriptions. Skipping custom description placements.")


def add_bbcode_images_to_description(torrent_info, config, description_file_path, bbcode_line_break):
    if "bbcode_images" in torrent_info and "url_images" not in config["translation"]:
        # Screenshots will be added to description only if no custom screenshot payload method is provided.
        # Possible payload mechanisms for screenshot are 1. bbcode, 2. url, 3. post data
        # TODO implement proper screenshot payload mechanism. [under technical_jargons?????]
        #
        # if custom_user_inputs is already present in torrent info, then the delete operation would have already be done
        # so we just need to append screenshots to the description.txt
        if "custom_user_inputs" not in torrent_info and os.path.isfile(description_file_path):
            os.remove(description_file_path)

        # Now open up the correct files and format all the bbcode/tags below
        with open(description_file_path, 'a') as description:
            # First add the [center] tags, "Screenshots" header, Size tags etc etc. This only needs to be written once which is why its outside of the 'for loop' below
            description.write(
                f'{bbcode_line_break}[center] ---------------------- [size=22]Screenshots[/size] ---------------------- {bbcode_line_break}{bbcode_line_break}')
            # Now write in the actual screenshot bbcode
            description.write(torrent_info["bbcode_images"])
            description.write("[/center]")


def write_uploader_signature_to_description(description_file_path, tracker, bbcode_line_break):
    # TODO what will happen if custom_user_inputs and bbcode_images are not present
    # will then open throw some errors???
    with open(description_file_path, 'a') as description:
        # Finally append the entire thing with some shameless self promotion ;) and some line breaks
        if os.getenv("uploader_signature") is not None and len(os.getenv("uploader_signature")) > 0:
            logging.debug('[Utils] User has provided custom uploader signature to use.')
            # the user has provided a custom signature to be used. hence we'll use that.
            uploader_signature = os.getenv("uploader_signature")
            logging.debug(f'[Utils] User provided signature :: {uploader_signature}')
            if not uploader_signature.startswith("[center]") and not uploader_signature.endswith("[/center]"):
                uploader_signature = f'[center]{uploader_signature}[/center]'
            uploader_signature = f'{uploader_signature}'
            description.write(f'{bbcode_line_break}{bbcode_line_break}{uploader_signature}')
        else:
            logging.debug('[Utils] User has not provided any custom uploader signature to use. Using default signature')
            description.write(
                f'{bbcode_line_break}{bbcode_line_break}[center] Uploaded with [color=red]{"<3" if str(tracker).upper() in ("BHD", "BHDTV") or os.name == "nt" else "❤"}[/color] using GG-BOT Upload Assistant[/center]')


def has_user_provided_type(user_type):
    if user_type:
        if user_type[0] in ('tv', 'movie'):
            logging.info(f"[Utils] Using user provided type {user_type[0]}")
            return True
        else:
            logging.error(f'[Utils] User has provided invalid media type as argument {user_type[0]}. Type will be detected dynamically!')
            return False
    else:
        logging.info("[Utils] Type not provided by user. Type will be detected dynamically!")
        return False


def delete_leftover_files(working_folder, file, resume=False):
    """
        Used to remove temporary files (mediainfo.txt, description.txt, screenshots) from the previous upload
        Func is called at the start of each run to make sure there are no mix up with wrong screenshots being uploaded etc.

        Not much significance when using the containerized solution, however if the `temp_upload` folder in container
        is mapped to a docker volume / host path, then clearing would be best. Hence keeping this method.
    """
    # We need these folders to store things like screenshots, .torrent & description files.
    # So create them now if they don't exist
    if Path(f"{working_folder}/temp_upload/").is_dir():
        # this means that the directory exists
        # If they do already exist then we need to remove any old data from them
        if resume:
            logging.info(f"[Utils] Resume flag provided by user. Preserving the contents of the folder: {working_folder}/temp_upload/")
        else:
            files = glob.glob(f'{working_folder}/temp_upload/*')
           # for f in files:
           #     if os.path.isfile(f):
           #         os.remove(f)
           #     else:
           #         shutil.rmtree(f)
            logging.info(f"[Utils] Deleted the contents of the folder: {working_folder}/temp_upload/")
    else:
        os.mkdir(f"{working_folder}/temp_upload/")

    if bool(os.getenv("readable_temp_data", False)) == True:
        files = f'{file}/'.replace("//", "/").strip().replace(" ", ".").replace(":", ".").replace("'", "").split("/")[:-1]
        files.reverse()
        unique_hash = files[0]
    else:
        unique_hash = get_hash(file)

    if not Path(f"{working_folder}/temp_upload/{unique_hash}").is_dir():
        os.mkdir(f"{working_folder}/temp_upload/{unique_hash}")
    if not Path(f"{working_folder}/temp_upload/{unique_hash}/screenshots/").is_dir():
        os.mkdir(f"{working_folder}/temp_upload/{unique_hash}/screenshots/")
    logging.info(f"[Utils] Created subfolder {unique_hash} for file {file}")
    return f"{unique_hash}/"


def write_file_contents_to_log_as_debug(file_path):
    """
        Method reads and writes the contents of the provided `file_path` to the log as debug lines.
        note that the method doesn't check for debug mode or not, those checks needs to be done by the caller
    """
    with open(file_path, 'r') as file_contents:
        lines = file_contents.readlines()
        _ = [logging.debug(line.replace('\\n', '').strip()) for line in lines]


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
    if Path(file_path).is_dir():
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
                subprocess.run([unrar_sys_package, 'e', rar_file[0], file_path])
                logging.debug(f"[Utils] Successfully extracted file : {rar_file[0]}")

                # This is how we identify which file we just extracted (Last modified)
                list_of_files = glob.glob(f"{os.path.join(file_path, '')}*")
                latest_file = max(list_of_files, key=os.path.getctime)

                logging.info(f"[Utils] Using the extracted {latest_file} for further processing")
                # the value for 'upload_media' with the path to the video file we just extracted
                return True, latest_file
            else:
                # If the user doesn't have unrar installed then we let them know here and move on to the next file (if exists)
                console.print('unrar is not installed, Unable to extract the rar archinve\n', style='bold red')
                logging.critical('[Utils] `unrar` is not installed, Unable to extract rar archive')
                logging.info('[Utils] Perhaps first try "sudo apt-get install unrar" then run this script again')
                # Skip this entire 'file upload' & move onto the next (if exists)
                return False, file_path
        return True, file_path
    else:
        logging.info(f'[Utils] Uploading the following file: {file_path}')
        return True, file_path


def prepare_and_validate_tracker_api_keys_dict(api_keys_file_path):
    """
        Reads the apis keys from environment and returns as a dictionary.

        Method will read the available api_keys from the `api_keys_file_path`, and for each of the mentioned keys, the value will be
        read from the environment variables. This method also checks whether the TMDB api key has been provided or not.

        In cases where the TMDB api key has not been configured, the method will raise an `AssertionError`.
    """

    api_keys = json.load(open(api_keys_file_path))
    api_keys_dict = dict()
    for value in api_keys:
        api_keys_dict[value] = os.getenv(value.upper(), "")

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
        if os.getenv(key, "") == "":
            console.print(f"Outdated config.env file. Variable [red][bold]{key}[/bold][/red] is missing.", style="blue")
            logging.error(f"Outdated config.env file. Variable {key} is missing.")


def get_and_validate_configured_trackers(trackers, all_trackers, api_keys_dict, all_trackers_list):
    upload_to_trackers = []
    # small sanity check
    if trackers is not None and len(trackers) < 1:
        trackers = None

    tracker_list = all_trackers_list
    if all_trackers:  # user wants to upload to all the trackers possible
        logging.info(f"[Utils] User has chosen to upload to add possible trackers: {tracker_list}")
    else:
        logging.info("[Utils] Attempting check and validate and default trackers configured")
        tracker_list = os.getenv("default_trackers_list", "")
        if len(tracker_list) > 0:
            tracker_list = [x.strip() for x in tracker_list.split(',')]

    for tracker in trackers or tracker_list or []:
        tracker = str(tracker)
        if f"{tracker.lower()}_api_key" in api_keys_dict:
            # Make sure that an API key is set for that site
            if len(api_keys_dict[f"{tracker.lower()}_api_key"]) <= 1:
                continue
            if tracker.upper() not in upload_to_trackers:
                upload_to_trackers.append(tracker.upper())
        else:
            logging.error(f"[Utils] We can't upload to '{tracker}' because that site is not supported")

    # Make sure that the user provides at least 1 valid tracker we can upload to
    # if len(upload_to_trackers) == 0 that means that the user either
    #   1. didn't provide any site at all,
    #   2. the site is not supported, or
    #   3. the API key isn't provided
    if len(upload_to_trackers) < 1:
        logging.exception("[Utils] No valid trackers specified for upload destination (e.g. BHD, BLU, ACM)")
        raise AssertionError("Provide at least 1 tracker we can upload to (e.g. BHD, BLU, ACM)")

    logging.debug(f"[Utils] Trackers selected by bot: {upload_to_trackers}")
    return upload_to_trackers


def _get_client_translated_path(torrent_info):
    # before we can upload the torrent to the client, we might need to do some path translations.
    # suppose, we are trying to upload a movie with the user provided path (-p argument) as
    ''' /home/user/data/movie_name/movie.mkv '''
    # when we add to client and sets the save location, it needs to be set as '/home/user/data/movie_name/'
    # if the user is running the torrent client in a docker container, or the uploader is running in a docker container 😉,
    # the paths accessible to the torrent client will be different. It could be ...
    """ /media/downloads/movie_name/movie.mkv """
    # In these cases we may need to perform path translations.
    """
        From: /home/user/data/movie_name/movie.mkv
        To: /media/downloads/movie_name/movie.mkv
    """

    if bool(os.getenv('translation_needed', False)) == True:
        logging.info('[Utils] Translating paths... ("translation_needed" flag set to True in config.env) ')

        # Just in case the user didn't end the path with a forward slash...
        uploader_accessible_path = f"{os.getenv('uploader_accessible_path', '__MISCONFIGURED_PATH__')}/".replace('//', '/')
        client_accessible_path = f"{os.getenv('client_accessible_path', '__MISCONFIGURED_PATH__')}/".replace('//', '/')

        if "__MISCONFIGURED_PATH__/" in [client_accessible_path, uploader_accessible_path]:
            logging.error("[Utils] User have enabled translation, but haven't provided the translation paths. Stopping cross-seeding...")
            return False

        # log the changes
        logging.info(f'[Utils] Uploader path: {torrent_info["upload_media"]}')
        logging.info(f'[Utils] Translated path: {torrent_info["upload_media"].replace(uploader_accessible_path, client_accessible_path)}')

        # Now we replace the remote path with the system one
        torrent_info["upload_media"] = torrent_info["upload_media"].replace(uploader_accessible_path, client_accessible_path)
    return f'{torrent_info["upload_media"]}/'.replace('//', '/')


def _post_mode_cross_seed(torrent_client, torrent_info, working_folder, tracker, allow_multiple_files):
    # TODO check and validate connection to torrent client.
    # or should this be done at the start?? Just becase torrent client connection cannot be established
    # doesn't mean that we cannot do the upload. Maybe show a warning at the start that cross-seeding is enabled and
    # client is not or misconfigured ???
    # we perform cross-seeding only if tracker upload was successful
    if f"{tracker}_upload_status" in torrent_info and torrent_info[f"{tracker}_upload_status"] == True:
        logging.info("[Utils] Attempting to upload dot torrent to configured torrent client.")
        logging.info(f"[Utils] `upload_media` :: '{torrent_info['upload_media']}' `client_path` :: '{torrent_info['client_path']}' ")
        console.print(f"\nFile Path: \t{torrent_info['upload_media']}")
        console.print(f"Client Save Path: \t{torrent_info['client_path']}")

        if allow_multiple_files == False and  "raw_video_file" in torrent_info and torrent_info["type"] == "movie":
            logging.info(f'[Utils] `raw_video_file` :: {torrent_info["raw_video_file"]}')
            save_path = torrent_info["client_path"]
        else:
            save_path = torrent_info["client_path"].replace(f'/{torrent_info["raw_file_name"]}', '')

        # getting the proper .torrent file for the provided tracker
        torrent_file = None
        for file in glob.glob(f"{working_folder}/temp_upload/{torrent_info['working_folder']}" + r"/*.torrent"):
            if f"/{tracker}-" in file:
                torrent_file = file
                console.print(f"Identified .torrent file \t'{file}' for tracker as '{tracker}'")
                logging.info(f"[Utils] Identified .torrent file '{file}' for tracker '{tracker}'")

        if torrent_file is not None:
            res = torrent_client.upload_torrent(
                torrent=torrent_file,
                save_path=save_path,
                use_auto_torrent_management=False,
                is_skip_checking=True
            )
        else:
            logging.error(f"[Utils] Could not identify the .torrent file for tracker '{tracker}'")
            console.print(f"⚠️ ☠️ ⚠️ [bold red]Could not identify the .torrent file for tracker [green]{tracker}[/green]." +
                          " [/bold red] Please seed this tracker's torrent manually. ⚠️ ☠️ ⚠️")
            res = None
        return res if res is not None else True
    return False


def _post_mode_watch_folder(torrent_info, working_folder):
    move_locations = {"torrent": f"{os.getenv('dot_torrent_move_location')}", "media": f"{os.getenv('media_move_location')}"}
    logging.debug(f"[Utils] Move locations configured by user :: {move_locations}")
    torrent_info["post_processing_complete"] = True

    console.print(f"Torrent move location :: [bold green]{move_locations['torrent']}[/bold green]")
    console.print(f"Media move location :: [bold green]{move_locations['media']}[/bold green]")

    for move_location_key, move_location_value in move_locations.items():
        # If the user supplied a path & it exists we proceed
        if len(move_location_value) == 0:
            logging.debug(f'[Utils] Move location not configured for {move_location_key}')
            continue
        if os.path.exists(move_location_value):
            logging.info(f"[Utils] The move path {move_location_value} exists")

            if move_location_key == 'torrent':
                sub_folder = "/"
                if os.getenv("enable_type_base_move", False) != False:
                    sub_folder = sub_folder + torrent_info["type"] + "/"
                    # os.makedirs(os.path.dirname(move_locations["torrent"] + sub_folder), exist_ok=True)
                    if os.path.exists(f"{move_locations['torrent']}{sub_folder}"):
                        logging.info(f"[Utils] Sub location '{move_locations['torrent']}{sub_folder}' exists.")
                    else:
                        logging.info(f"[Utils] Creating Sub location '{move_locations['torrent']}{sub_folder}'.")
                        Path(f"{move_locations['torrent']}{sub_folder}").mkdir(parents=True, exist_ok=True)
                # The user might have upload to a few sites so we need to move all files that end with .torrent to the new location
                list_dot_torrent_files = glob.glob(f"{working_folder}/temp_upload/{torrent_info['working_folder']}*.torrent")
                for dot_torrent_file in list_dot_torrent_files:
                    # Move each .torrent file we find into the directory the user specified
                    logging.debug(f'[Utils] Moving {dot_torrent_file} to {move_locations["torrent"]}{sub_folder}')
                    try:
                        shutil.move(dot_torrent_file,f'{move_locations["torrent"]}{sub_folder}')
                    except Exception:
                        logging.exception(f'[Utils] Cannot move torrent {dot_torrent_file} to location {move_locations["torrent"] + sub_folder}')
                        console.print(f"[bold red]Failed to move [green]{dot_torrent_file}[/green] to location [green]{move_locations['torrent'] + sub_folder}[/green] [/bold red]")

            # Media files are moved instead of copied so we need to make sure they don't already exist in the path the user provides
            if move_location_key == 'media':
                if str(f"{Path(torrent_info['upload_media']).parent}/") == move_location_value:
                    console.print(f'\nError, {torrent_info["upload_media"]} is already in the move location you specified: "{move_location_value}"\n', style="red", highlight=False)
                    logging.error(f"[Utils] {torrent_info['upload_media']} is already in {move_location_value}, Not moving the media")
                else:
                    sub_folder = "/"
                    if os.getenv("enable_type_base_move", False) != False:
                        sub_folder = sub_folder + torrent_info["type"] + "/"
                        move_location_value = move_location_value + sub_folder
                        os.makedirs(os.path.dirname(move_location_value), exist_ok=True)
                    logging.info(f"[Utils] Moving {torrent_info['upload_media']} to {move_location_value }")
                    try:
                        shutil.move(torrent_info["upload_media"], move_location_value)
                    except Exception:
                        logging.exception(f"[Utils] Cannot move media {torrent_info['upload_media']} to location {move_location_value}")
                        console.print(f"[bold red]Failed to move [green]{torrent_info['upload_media']}[/green] to location [green]{move_location_value}[/green] [/bold red]")
        else:
            logging.error(f"[Utils] Move path doesn't exist for {move_location_key} as {move_location_value}")
            console.print(f"[bold red]Location [green]{move_location_value}[/green] doesn't exit. Cannot move [green]{move_location_key}[/green][/bold red]")


def get_torrent_client_if_needed():
    logging.debug(f"[Utils] enable_post_processing {os.getenv('enable_post_processing', False)}")
    logging.debug(f"[Utils] post_processing_mode {os.getenv('post_processing_mode', False)}")
    if bool(os.getenv("enable_post_processing", False)) == True and os.getenv("post_processing_mode", "") == "CROSS_SEED":
        # getting an instance of the torrent client factory
        torrent_client_factory = TorrentClientFactory()
        # creating the torrent client using the factory based on the users configuration
        torrent_client = torrent_client_factory.create(Clients[os.getenv('client')])
        # checking whether the torrent client connection has been created successfully or not
        torrent_client.hello()
        return torrent_client
    else:
        logging.info("[Utils] Skipping torrent client creation...")
        return None


def perform_post_processing(torrent_info, torrent_client, working_folder, tracker, allow_multiple_files=False):
    # After we finish uploading, we can add all the dot torrent files to a torrent client to start seeding immediately.
    # This post processing step can be enabled or disabled based on the users configuration
    if bool(os.getenv("enable_post_processing", False)):
        # When running in a bare meta, there is a chance for the user to provide relative paths.
        """ data/movie_name/movie.mkv """
        # the way to identify a relative path is to check whether the `upload_media` starts with a `/`
        if not torrent_info["upload_media"].startswith("/"):
            torrent_info["upload_media"] = f'{working_folder}/{torrent_info["upload_media"]}'
            logging.info(f'[Utils] User has provided relative path. Converting to absolute path for torrent client :: "{torrent_info["upload_media"]}"')

        # apply path translations and getting translated paths
        translated_path = _get_client_translated_path(torrent_info)
        if translated_path == False:
            return False
        torrent_info["client_path"] = translated_path

        post_processing_mode = os.getenv("post_processing_mode", "")
        if post_processing_mode == "CROSS_SEED":
            console.print("[bold] 🌱 Detected [red]Cross Seed[/red] as the post processing mode. 🌱 [/bold]", justify="center")
            return _post_mode_cross_seed(torrent_client, torrent_info, working_folder, tracker, allow_multiple_files)
        elif post_processing_mode == "WATCH_FOLDER":
            console.print("[bold] ⌚ Detected [red]Watch Folder[/red] as the post processing mode. ⌚ [/bold]", justify="center")
            return _post_mode_watch_folder(torrent_info, working_folder)
        else:
            logging.error(f"[Utils] Post processing is enabled, but invalid mode provided: '{post_processing_mode}'")
            return False
    else:
        logging.info("[Utils] No process processing steps needed, as per users configuration")
        console.print("\n[bold magenta] 😞  Oops!!. No post processing steps have been configured. 😞 [/bold magenta]", justify="center")
        return False


def display_banner(mode):
    gg_bot = pyfiglet.figlet_format("GG-BOT", font="banner3-D")
    mode = pyfiglet.figlet_format(mode, font="banner3-D", width=210)

    console.print(f'[bold green]{gg_bot}[/bold green]', justify="center")
    console.print(f'[bold blue]{mode}[/bold blue]', justify="center", style='#38ACEC')
    return True


def sanitize_release_group_from_guessit(torrent_info):
    # setting NOGROUP as group if the release_group cannot be identified from guessit
    if "release_group" in torrent_info and len(torrent_info["release_group"]) > 0:
        # sometimes, guessit identifies wrong release groups. So we just do another sanity check just to ensure that the release group
        # provided by guessit is correct.
        if torrent_info["upload_media"].replace(".mkv", "").replace(".mp4", "").endswith(f"-{torrent_info['release_group']}"):
            # well the release group identified by guessit seems correct.
            if torrent_info["release_group"].startswith("X-"):
                # a special case where title ends with DTS-X-EPSILON and guess it extracts release group as X-EPSILON
                logging.info(f'Guessit identified release group as {torrent_info["release_group"]}. Since this starts with X- (probably from DTS-X-RELEASE_GROUP), overwriting release group as {torrent_info["release_group"][2:]}')
                return torrent_info["release_group"][2:]
        else:
            logging.debug("Release group could not be identified by guessit. Setting release group as NOGROUP")
            return "NOGROUP"
    else:
        logging.debug("Release group could not be identified by guessit. Setting release group as NOGROUP")
        return "NOGROUP"
    return torrent_info["release_group"]
