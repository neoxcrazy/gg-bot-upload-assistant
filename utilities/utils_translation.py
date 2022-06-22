import os
import sys
import logging

from rich.console import Console


console = Console()


def identify_resolution_source(target_val, config, relevant_torrent_info_values, torrent_info):
    # target_val is type (source) or resolution_id (resolution)
    possible_match_layer_1 = []
    for key in config["Required"][(config["translation"][target_val])]:
        # this key is the number provided under the target_val
        logging.debug(f"[ResolutionSourceMapping] Trying to match `{config['translation'][target_val]}` to configured key `{key}`")

        total_num_of_required_keys = 0
        total_num_of_acquired_keys = 0

        # If we have a list of options to choose from, each match is saved here
        total_num_of_optionals_matched = 0
        optional_keys = []

        for sub_key, sub_val in config["Required"][(config["translation"][target_val])][key].items():
            # for each sub key and its priority we
            logging.debug(
                f'[ResolutionSourceMapping] Considering item `{sub_key}` with priority `{sub_val}`')
            # Sub-Key Priorities
            # ---------------------
            # 0 = optional
            # 1 = required
            # 2 = select from available items in list

            if sub_val == 1:
                total_num_of_required_keys += 1
                # Now check if the sub_key is in the relevant_torrent_info_values list
                if sub_key in str(relevant_torrent_info_values).lower():
                    total_num_of_acquired_keys += 1
                    logging.debug(
                        f'[ResolutionSourceMapping] Required `{sub_key}` is present in relevant torrent info list. Considering key as acquired')
            elif sub_val == 2:
                if sub_key in str(relevant_torrent_info_values).lower():
                    total_num_of_optionals_matched += 1
                    logging.debug(
                        f'[ResolutionSourceMapping] SelectMultiple `{sub_key}` is present in relevant torrent info list. Considering key as acquired value')
                optional_keys.append(sub_key)

        logging.debug(f'[ResolutionSourceMapping] Total number of required keys: {total_num_of_required_keys}')
        logging.debug(f'[ResolutionSourceMapping] Total number of acquired keys: {total_num_of_acquired_keys}')
        logging.debug(f'[ResolutionSourceMapping] Optional keys: {optional_keys}')
        logging.debug(f'[ResolutionSourceMapping] Total number of optionals matched: {total_num_of_optionals_matched}')

        if int(total_num_of_required_keys) == int(total_num_of_acquired_keys):
            if len(optional_keys) > 0:
                if int(total_num_of_optionals_matched) > 0:
                    logging.debug(
                        f'[ResolutionSourceMapping] Some {total_num_of_optionals_matched} of optional keys {optional_keys} were matched and no of required items and no of acquired items are equal. Hence considering key `{key}` as a match for `{config["translation"][target_val]}`')
                    possible_match_layer_1.append(key)
                else:
                    logging.debug(f'[ResolutionSourceMapping] No optional keys {optional_keys} were matched.')
            else:
                logging.debug(
                    f'[ResolutionSourceMapping] No of required items and no of acquired items are equal. Hence considering key `{key}` as a match for `{config["translation"][target_val]}`')
                possible_match_layer_1.append(key)
            # We check for " == 0" so that if we get a profile that matches all the "1" then we can break immediately (2160p BD remux requires 'remux', '2160p', 'bluray')
            # so if we find all those values in optional_keys list then we can break
            # knowing that we hit 100% of the required values instead of having to cycle through the "optional" values and select one of them
            if len(optional_keys) == 0 and key != "other":
                break

            if len(optional_keys) >= 2 and int(total_num_of_optionals_matched) == 1:
                break

        if len(possible_match_layer_1) >= 2 and "Other" in possible_match_layer_1:
            possible_match_layer_1.remove("Other")

    # checking whether we were able to get a match in any of the configuration
    if len(possible_match_layer_1) == 1:
        val = possible_match_layer_1.pop()
        logging.debug(f'[ResolutionSourceMapping] Successfully matched one item for `{config["translation"][target_val]}` => `{val}`')
        return val
    else:
        # this means we either have 2 potential matches or no matches at all (this happens if the media does not fit any of the allowed parameters)
        logging.critical('[ResolutionSourceMapping] Unable to find a suitable "source" match for this file')
        logging.error("[ResolutionSourceMapping] Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip to BLU is not allowed)")
        console.print(
            f'\nThis "Type" ([bold]{torrent_info["source"]}[/bold]) or this "Resolution" ([bold]{torrent_info["screen_size"]}[/bold]) is not allowed on this tracker', style='Red underline', highlight=False)
        return "STOP"


def get_hybrid_type(translation_value, tracker_settings, config, exit_program, torrent_info):
    """
        Method to get a hybrid type from the source, resolution and type properties of the torrent
    """
    logging.info("[HybridMapping] Performing hybrid mapping now...")
    logging.debug('------------------ Hybrid mapping started ------------------')
    # logging all the Prerequisite data
    # if any of the Prerequisite data is not available, then this method will not be invoked
    for prerequisite in config["hybrid_mappings"][translation_value]["prerequisite"]:
        logging.info(f"[HybridMapping] Prerequisite :: '{prerequisite}' Value :: '{tracker_settings[prerequisite]}'")

    for key in config["hybrid_mappings"][translation_value]["mapping"]:
        logging.debug(f"[HybridMapping] Trying to match '{translation_value}' to hybrid key '{key}'")
        is_valid = None
        for sub_key, sub_val in config["hybrid_mappings"][translation_value]["mapping"][key].items():
            user_wants_negation = "not" in sub_val and sub_val["not"] == True
            if user_wants_negation:
                logging.debug(f"[HybridMapping] The subkey '{sub_key}' from '{sub_val['data_source']}' must NOT be one of {sub_val['values']} for the mapping to be accepted.")
            else:
                logging.debug(f"[HybridMapping] The subkey '{sub_key}' from '{sub_val['data_source']}' need to be one of {sub_val['values']} for the mapping to be accepted.")

            datasource = tracker_settings if sub_val["data_source"] == "tracker" else torrent_info
            selected_val = datasource[sub_key] if sub_key in datasource else None
            logging.debug(f"[HybridMapping] Value selected from data source is '{selected_val}'")
            if selected_val is not None:
                if len(sub_val["values"]) == 0:
                    logging.info(f"[HybridMapping] For the subkey '{sub_key}' the values configured '{sub_val['values']}' is empty. Assuming by default as valid and continuing.")
                    is_valid = True if is_valid is None else is_valid
                elif user_wants_negation and str(selected_val) not in sub_val['values']:
                    logging.debug(f"[HybridMapping] The subkey '{sub_key}' '{selected_val}' is not present in '{sub_val['values']}' for '{sub_key}' and '{key}'")
                    is_valid = True if is_valid is None else is_valid
                elif not user_wants_negation and str(selected_val) in sub_val['values']:
                    logging.debug(f"[HybridMapping] The subkey '{sub_key}' '{selected_val}' is present in '{sub_val['values']}' for '{sub_key}' and '{key}'")
                    is_valid = True if is_valid is None else is_valid
                elif sub_val['values'][0] == "IS_NOT_NONE_OR_IS_PRESENT" and selected_val is not None and len(str(selected_val)) > 0:
                    logging.debug(f"[HybridMapping] The subkey '{sub_key}' '{selected_val}' is present in '{sub_val['data_source']}' for '{sub_key}' and '{key}'")
                    is_valid = True if is_valid is None else is_valid
                else:
                    logging.debug(f"[HybridMapping] The subkey '{sub_key}' '{selected_val}' is NOT present in '{sub_val['values']}' for '{sub_key}' and '{key}'")
                    is_valid = False
            else:
                is_valid = False
                logging.fatal(f"[HybridMapping] Invalid configuration provided for hybrid key mapping. Key :: '{key}', sub key :: '{sub_key}', sub value :: '{sub_val}'")

        if is_valid:
            logging.info(f"[HybridMapping] The hybrid key was identified to be '{key}'")
            logging.debug('------------------ Hybrid mapping Completed ------------------')
            # is_valid is true
            # all the categories match
            return key

    logging.debug('------------------ Hybrid mapping Completed With ERRORS ------------------')
    # this means we either have 2 potential matches or no matches at all (this happens if the media does not fit any of the allowed parameters)
    logging.critical('[HybridMapping] Unable to find a suitable "hybrid mapping" match for this file')
    logging.error("[HybridMapping] Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip to BLU is not allowed)")
    console.print(f"Failed to perform Hybrid Mapping for '{translation_value}'. This type of upload might not be allowed on this tracker.", style='Red underline')
    if exit_program: # TODO add check for required or optional. If required, then exit app
        sys.exit("Invalid hybrid mapping configuration provided.")
    return "HYBRID_MAPPING_INVALID_CONFIGURATION"


def should_delay_mapping(translation_value, prerequisites, tracker_settings):
    logging.info(f"[HybridMapping] Performing 'prerequisite' validation for '{translation_value}'")
    for prerequisite in prerequisites :
        if prerequisite not in tracker_settings:
            logging.info(f"[HybridMapping] The prerequisite '{prerequisite}' for '{translation_value}' is not available currently. " +
                "Skipping hybrid mapping for now and proceeding with remaining translations...")
            return True
    return False


def perform_delayed_hybrid_mapping(config, tracker_settings, torrent_info, exit_program):
    no_of_hybrid_mappings = len(config["hybrid_mappings"].keys())
    logging.info(f"[HybridMapping] Performing hybrid mapping after all translations have completed. No of hybrid mappings :: '{no_of_hybrid_mappings}'")

    for _ in range(0, no_of_hybrid_mappings):
        for translation_value in config["hybrid_mappings"].keys():
            # check whether the particular field can be underdo hybrid mapping
            delay_mapping = should_delay_mapping(
                translation_value=translation_value,
                prerequisites=config["hybrid_mappings"][translation_value]["prerequisite"],
                tracker_settings=tracker_settings
            )
            if translation_value not in tracker_settings and delay_mapping == False:
                tracker_settings[translation_value] = get_hybrid_type(
                    translation_value=translation_value,
                    tracker_settings=tracker_settings,
                    config=config,
                    exit_program=exit_program,
                    torrent_info=torrent_info
                )


# ---------------------------------------------------------------------- #
#           !!! WARN !!! This Method has side effects. !!! WARN !!!
# ---------------------------------------------------------------------- #
def __create_imdb_without_tt_key(torrent_info):
    torrent_info["imdb_with_tt"] = torrent_info["imdb"]
    if len(torrent_info["imdb"]) >= 2:
        if str(torrent_info["imdb"]).startswith("tt"):
            torrent_info["imdb"] = str(
                torrent_info["imdb"]).replace("tt", "")
        else:
            torrent_info["imdb_with_tt"] = f'tt{torrent_info["imdb"]}'
    else:
        torrent_info["imdb"] = "0"
        torrent_info["imdb_with_tt"] = "0"


def __get_relevant_items_for_tracker_keys(torrent_info):
    relevant_torrent_info_values = []
    for relevant_items in ["source_type", "screen_size", "bluray_disc_type"]:
        if relevant_items in torrent_info:
            relevant_torrent_info_values.append(torrent_info[relevant_items])
    logging.debug(f'The relevant torrent info values for resolution / source identification are {relevant_torrent_info_values}')
    return relevant_torrent_info_values


# ---------------------------------------------------------------------- #
#                  Set correct tracker API Key/Values                    #
# ---------------------------------------------------------------------- #
# ---------------------------------------------------------------------- #
#           !!! WARN !!! This Method has side effects. !!! WARN !!!
# ---------------------------------------------------------------------- #
def choose_right_tracker_keys(config, tracker_settings, tracker, torrent_info, args, working_folder):
    required_items = config["Required"]
    optional_items = config["Optional"]

    # BLU requires the IMDB with the "tt" removed so we do that here, BHD will automatically put the "tt" back in... so we don't need to make an exception for that
    if "imdb" in torrent_info:
        __create_imdb_without_tt_key(torrent_info)

    # torrent title
    tracker_settings[config["translation"]["torrent_title"]] = torrent_info["torrent_title"]

    # Save a few key values in a list that we'll use later to identify the resolution and type
    relevant_torrent_info_values = __get_relevant_items_for_tracker_keys(torrent_info)

    # Filling in data for all the keys that have mapping/translations
    # Here we iterate over the translation mapping and for each translation key, we check the required and optional items for that value
    # once identified we handle it
    logging.info("[Main] Starting translations from torrent info to tracker settings.")
    is_hybrid_translation_needed = False

    for translation_key, translation_value in config["translation"].items():
        logging.debug(f"[Main] Trying to translate {translation_key} to {translation_value}")

        # ------------ required_items start ------------
        for required_key, required_value in required_items.items():
            # get the proper mapping, the elements that doesn't match can be ignored
            if str(required_key) == str(translation_value):
                # hybrid_type is managed by hybrid_mapping.
                if required_value == "hybrid_type":
                    break

                logging.debug(f"[Main] Key {translation_key} mapped to required item {required_key} with value type as {required_value}")

                # the torrent file is always submitted as a file
                if required_value in ("file", "file|base64", "file|array", "file|string|array"):
                    # adding support for base64 encoded files
                    # the actual encoding will be performed in `upload_to_site` method
                    if translation_key in torrent_info:
                        tracker_settings[config["translation"][translation_key]] = torrent_info[translation_key]
                    # Make sure you select the right .torrent file
                    if translation_key == "dot_torrent":
                        tracker_settings[config["translation"]["dot_torrent"]] = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}{tracker}-{torrent_info["torrent_title"]}.torrent'

                # The reason why we keep this elif statement here is because the conditional right above is also technically a "string"
                # but its easier to keep mediainfo and description in text files until we need them so we have that small exception for them
                elif required_value in ("string", "string|array"):
                    # BHD requires the key "live" (0 = Sent to drafts and 1 = Live on site)
                    if required_key == "live":
                        # BHD Live/Draft
                        is_live_on_site = str(os.getenv('live')).lower()
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

                if translation_key in ('source', 'resolution', 'resolution_id'):
                    return_value = identify_resolution_source(
                        target_val=translation_key,
                        config=config,
                        relevant_torrent_info_values=relevant_torrent_info_values,
                        torrent_info=torrent_info
                    )
                    if return_value == "STOP":
                        return return_value
                    tracker_settings[config["translation"][translation_key]] = return_value
        # ------------ required_items end ------------

        # ------------ optional_items start ------------
        # This mainly applies to BHD since they are the tracker with the most 'Optional' fields,
        # BLU/ACM only have 'nfo_file' as an optional item which we take care of later
        for optional_key, optional_value in optional_items.items():
            if str(optional_key) == str(translation_value):
                # hybrid_type is managed by hybrid_mapping.
                if optional_value == "hybrid_type":
                    break

                logging.debug(f"[Main] Key {translation_key} mapped to optional item {optional_key} with value type as {optional_value}")
                # -!-!- Editions -!-!- #
                if optional_key == 'edition' and 'edition' in torrent_info:
                    # First we remove any 'fluff' so that we can try to match the edition to the list BHD has, if not we just upload it as a custom edition
                    local_edition_formatted = str(torrent_info["edition"]).lower().replace("edition", "").replace("cut", "").replace("'", "").replace(" ", "")
                    # Remove extra 's'
                    if local_edition_formatted.endswith('s'):
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
                    logging.debug(f"[CategoryMapping] Identified {optional_key} for tracker with {'FullDisk' if args.disc else 'File/Folder'} upload")
                    if args.disc:
                        logging.debug("[CategoryMapping] Skipping mediainfo for tracker settings since upload is FullDisk.")
                    else:
                        logging.debug(f"[CategoryMapping] Setting mediainfo from torrent_info to tracker_settings for optional_key {optional_key}")
                        tracker_settings[optional_key] = torrent_info.get("mediainfo", "0")
                        continue
                elif translation_key == "bdinfo":
                    logging.debug(f"[CategoryMapping] Identified {optional_key} for tracker with {'FullDisk' if args.disc else 'File/Folder'} upload")
                    if args.disc:
                        logging.debug(f"[CategoryMapping] Setting mediainfo from torrent_info to tracker_settings for optional_key {optional_key}")
                        tracker_settings[optional_key] = torrent_info.get("mediainfo", "0")
                        continue
                    else:
                        logging.debug("[CategoryMapping] Skipping bdinfo for tracker settings since upload is NOT FullDisk.")
                else:
                    tracker_settings[optional_key] = torrent_info.get(translation_key, "")
        # ------------ optional_items end ------------

        # ----------- hybrid_mapping_v2 start -----------
        # using in instead of == since multiple hybrid mappings can be configured
        # such as hybrid_type_1, hybrid_type_2, hybrid_type_3 ....
        if "hybrid_type" in translation_key:
            logging.info(f"[HybridMapping] Identified 'hybrid_type' for tracker attribute '{translation_value}'")
            logging.info(f"[HybridMapping] Validating the hybrid mapping settings for '{translation_value}'")
            if "hybrid_mappings" in config and translation_value in config["hybrid_mappings"]:
                delayed_mapping = False
                # to do hybrid translation we might need certain prerequisite fields to be resolved before hand in tracker settings.
                # we first check whether they have been resolved or not.
                # If those values have been resolved then we can just call the `get_hybrid_type` to resolve it.
                # otherwise we mark the present of this hybrid type and do the mapping after all required and optional
                # value mapping have been completed.
                # prerequisite needed only for tracker_settings. Not for torrent_info data
                if "prerequisite" in config["hybrid_mappings"][translation_value]:
                    delayed_mapping = should_delay_mapping(
                        translation_value=translation_value,
                        prerequisites=config["hybrid_mappings"][translation_value]["prerequisite"],
                        tracker_settings=tracker_settings
                    )
                    is_hybrid_translation_needed = delayed_mapping if is_hybrid_translation_needed == False else is_hybrid_translation_needed
                else:
                    logging.info(f"[HybridMapping] No 'prerequisite' required for '{translation_value}'")

                if delayed_mapping == True:
                    continue

                logging.info(f"[HybridMapping] Going to perform hybrid mapping for :: '{translation_value}'")
                tracker_settings[translation_value] = get_hybrid_type(
                    translation_value=translation_value,
                    tracker_settings=tracker_settings,
                    config=config,
                    exit_program=True,
                    torrent_info=torrent_info
                )
            else:
                logging.error(f"[HybridMapping] No hybrid mapping configurations provided for '{translation_value}'." +
                    "\nFor all `hybrid_type` hybrid mapping is required irrepective whether the value is required or optional.")
                sys.exit("Invalid hybrid mapping configuration provided.")
        # ------------ hybrid_mapping_v2 end ------------

    # Adding default values from template to tracker settings
    for default_key, default_value in config["Default"].items():
        logging.debug(f'[DefaultMapping] Adding default key `{default_key}` with value `{default_value}` to tracker settings')
        tracker_settings[default_key] = default_value

    # at this point we have finished iterating over the translation key items
    if is_hybrid_translation_needed:
        tracker_settings[config["translation"]["hybrid_type"]] = get_hybrid_type(
            translation_value=translation_value,
            tracker_settings=tracker_settings,
            config=config,
            exit_program=False,
            torrent_info=torrent_info
        )
# -------------- END of choose_right_tracker_keys --------------