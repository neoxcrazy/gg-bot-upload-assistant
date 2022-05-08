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
            logging.debug(f'[ResolutionSourceMapping] Considering item `{sub_key}` with priority `{sub_val}`')
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
                    logging.debug(f'[ResolutionSourceMapping] Required `{sub_key}` is present in relevant torrent info list. Considering key as acquired')
            elif sub_val == 2:
                if sub_key in str(relevant_torrent_info_values).lower():
                    total_num_of_optionals_matched += 1
                    logging.debug(f'[ResolutionSourceMapping] SelectMultiple `{sub_key}` is present in relevant torrent info list. Considering key as acquired value')
                optional_keys.append(sub_key)

        logging.debug(f'[ResolutionSourceMapping] Total number of required keys: {total_num_of_required_keys}')
        logging.debug(f'[ResolutionSourceMapping] Total number of acquired keys: {total_num_of_acquired_keys}')
        logging.debug(f'[ResolutionSourceMapping] Optional keys: {optional_keys}')
        logging.debug(f'[ResolutionSourceMapping] Total number of optionals matched: {total_num_of_optionals_matched}')

        if int(total_num_of_required_keys) == int(total_num_of_acquired_keys):
            if len(optional_keys) > 0:
                if int(total_num_of_optionals_matched) > 0:
                    logging.debug(f'[ResolutionSourceMapping] Some {total_num_of_optionals_matched} of optional keys {optional_keys} were matched and no of required items and no of acquired items are equal. Hence considering key `{key}` as a match for `{config["translation"][target_val]}`')
                    possible_match_layer_1.append(key)
                else:
                    logging.debug(f'[ResolutionSourceMapping] No optional keys {optional_keys} were matched.')
            else:
                logging.debug(f'[ResolutionSourceMapping] No of required items and no of acquired items are equal. Hence considering key `{key}` as a match for `{config["translation"][target_val]}`')
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
        console.print(f'\nThis "Type" ([bold]{torrent_info["source"]}[/bold]) or this "Resolution" ([bold]{torrent_info["screen_size"]}[/bold]) is not allowed on this tracker', style='Red underline', highlight=False)
        return "STOP"


def get_hybrid_type(target_val, tracker_settings, config, exit_program, torrent_info):
        """
            Method to get a hybrid type from the source, resolution and type properties of the torrent
        """
        logging.debug(f'------------------ Hybrid mapping started ------------------')
        # getting values for the source, resolution and type properties
        source = tracker_settings[config["translation"]["source"]]
        resolution = tracker_settings[config["translation"]["resolution"]]
        type = tracker_settings[config["translation"]["type"]]
        logging.debug(f'[HybridMapping] Selected values :: source [{source}] resolution [{resolution}] type [{type}]')

        for key in config["hybrid_type"]["mapping"]:
            logging.debug(f"[HybridMapping] Trying to match `{config['translation'][target_val]}` to hybrid key `{key}`")
            is_valid = None
            for sub_key, sub_val in config["hybrid_type"]["mapping"][key].items():
                logging.debug(f'[HybridMapping] The subkey `{sub_key}` from `{sub_val["data_source"]}` need to be one of `{sub_val["values"]}` for the mapping to be accepted.')
                
                datasource = tracker_settings if sub_val["data_source"] == "tracker" else torrent_info
                selected_val = datasource[sub_key]
                
                if selected_val is not None:
                    if len(sub_val["values"]) == 0:
                        logging.info(f"[HybridMapping] For the subkey `{sub_key}` the values configured `{sub_val['values']}` is empty. Assuming by default as valid and continuing.")
                        is_valid = True if is_valid is None else is_valid
                    elif str(selected_val) in sub_val['values']:
                        logging.debug(f"[HybridMapping] The subkey `{sub_key}` `{selected_val}` is present in `{sub_val['values']}` for `{sub_key}` and `{key}`")
                        is_valid = True if is_valid is None else is_valid
                    else:
                        logging.debug(f"[HybridMapping] The subkey `{sub_key}` `{selected_val}` is NOT present in `{sub_val['values']}` for `{sub_key}` and `{key}`")
                        is_valid = False
                else:
                    is_valid = False
                    logging.fatal(f"[HybridMapping] Invalid configuration provided for hybrid key mapping. Key ::{key}, sub key :: {sub_key}, sub value :: {sub_val}")

            if is_valid:
                logging.info(f'[HybridMapping] The hybrid key was identified to be {key}')
                logging.debug(f'------------------ Hybrid mapping Completed ------------------')
                # is_valid is true 
                # all the categories match
                return key
        
        logging.debug(f'------------------ Hybrid mapping Completed With ERRORS ------------------')
        # this means we either have 2 potential matches or no matches at all (this happens if the media does not fit any of the allowed parameters)
        logging.critical('[HybridMapping] Unable to find a suitable "hybrid mapping" match for this file')
        logging.error("[HybridMapping] Its possible that the media you are trying to upload is not allowed on site (e.g. DVDRip to BLU is not allowed)")
        console.print(f'\nThis "Type" ([bold]{torrent_info["source"]}[/bold]) or this "Resolution" ([bold]{torrent_info["screen_size"]}[/bold]) is not allowed on this tracker', style='Red underline', highlight=False)
        if exit_program:
            sys.exit()
        return "HYBRID_MAPPING_INVALID_CONFIGURATION"
