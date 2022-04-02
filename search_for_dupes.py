import os
import re
import json
import logging
import requests
from pprint import pformat
from distutils import util
from guessit import guessit
from fuzzywuzzy import fuzz
from rich.table import Table
from rich.prompt import Confirm
from rich.console import Console

console = Console()
working_folder = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=f'{working_folder}/upload_script.log', level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')


def replace_item_in_list(source_list, item_to_replace, list_to_replace_with):
    """
        Method to place an item in a list with another list
    """
    result = []
    for i in source_list:
        if i == item_to_replace:
            result.extend(list_to_replace_with)
        else:
            result.append(i)
    return result


def search_for_dupes_api(search_site, imdb, tmdb, tvmaze, torrent_info, tracker_api, debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    with open(f'{working_folder}/site_templates/{search_site}.json', "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    
    imdb = imdb.replace('tt', '') if config["dupes"]["strip_text"] == True else imdb
    url_dupe_payload = None  # this is here just for the log, its not technically needed

    # multiple authentication modes
    headers = None
    if config["dupes"]["technical_jargons"]["authentication_mode"] == "API_KEY":
        pass # headers = None
    elif config["dupes"]["technical_jargons"]["authentication_mode"] == "BEARER":
        headers = {'Authorization': f'Bearer {tracker_api}'}
        logging.info(f"[DupeCheck] Using Bearer Token authentication method for tracker {search_site}")
    elif config["dupes"]["technical_jargons"]["authentication_mode"] == "HEADER":
        if len(config["dupes"]["technical_jargons"]["header_key"]) > 0:
            headers = {config["dupes"]["technical_jargons"]["header_key"]: tracker_api}
            logging.info(f"[DupeCheck] Using Header based authentication method for tracker {search_site}")
        else:
            logging.fatal(f'[DupeCheck] Header based authentication cannot be done without `header_key` for tracker {search_site}.')
    elif config["dupes"]["technical_jargons"]["authentication_mode"] == "COOKIE":
        logging.fatal(f'[DupeCheck] Cookie based authentication is not supported as for now.')

    if str(config["dupes"]["technical_jargons"]["request_method"]) == "POST": # POST request (BHD)
        url_dupe_search = str(config["torrents_search"]).format(api_key=tracker_api)

        #-------------------------------------------------------------------------
        # Temporary fix for BIT-HDTV TODO need to find a better solution for this.
        if search_site == "bit-hdtv":
            url_replacer = f"https://www.imdb.com/title/{imdb}"
            if torrent_info["type"] == "episode":
                url_replacer = f"https://www.tvmaze.com/shows/{tvmaze}"
            url_dupe_payload = config["dupes"]["payload"].replace("<imdb>", url_replacer).replace("<title>", torrent_info["title"])
        else:
            url_dupe_payload = config["dupes"]["payload"].replace("<imdb>", str(imdb)).replace("<tvmaze>", str(tvmaze)).replace("<tmdb>", str(tmdb)).replace("<api_key>", tracker_api).replace("<title>", torrent_info["title"])
        #-------------------------------------------------------------------------

        logging.debug(f"[DupeCheck] Formatted POST payload {url_dupe_payload} for {search_site}")
        url_dupe_payload = json.loads(url_dupe_payload)

        if config["dupes"]["technical_jargons"]["authentication_mode"] == "API_KEY_PAYLOAD":
            # adding Authentication api_key to payload
            url_dupe_payload[config["dupes"]["technical_jargons"]["auth_payload_key"]] = tracker_api

        if str(config["dupes"]["technical_jargons"]["payload_type"]) == "JSON":
            dupe_check_response = requests.request("POST", url_dupe_search, json=url_dupe_payload, headers=headers)
        else:
            dupe_check_response = requests.request("POST", url_dupe_search, data=url_dupe_payload, headers=headers)
    else: # GET request (BLU & ACM)
        url_dupe_search = str(config["dupes"]["url_format"]).format(search_url=str(config["torrents_search"]).format(api_key=tracker_api), title=torrent_info["title"], imdb=imdb)
        dupe_check_response = requests.request("GET", url_dupe_search, headers=headers)
        
    logging.info(msg=f'[DupeCheck] Dupe search request | Method: {str(config["dupes"]["technical_jargons"]["request_method"])} | URL: {url_dupe_search} | Payload: {url_dupe_payload}')
    
    if dupe_check_response.status_code != 200:
        logging.error(f"[DupeCheck] {search_site} returned the status code: {dupe_check_response.status_code}")
        logging.error(f"[DupeCheck] payload response from {search_site} {dupe_check_response.json()}")
        logging.info(f"[DupeCheck] Dupe check for {search_site} failed, assuming no dupes and continuing upload")
        return False

    # Now that we have the response from tracker(X) we can parse the json and try to identify dupes
    existing_release_types = {}  # We first break down the results into very basic categories like "remux", "encode", "web" etc and store the title + results here
    existing_releases_count = {'bluray_encode': 0, 'bluray_remux': 0, 'webdl': 0, 'webrip': 0, 'hdtv': 0}  # We also log the num each type shows up on site
    single_episode_upload_with_season_pack_available = False

    # adding support for speedapp. Speedapp just returns the torrents as a json array.
    # for compatbility with other trackers a new flag is added named `is_needed` under `parse_json`
    # as the name indicates, it decides whether or not the `dupe_check_response` returned from the tracker
    # needs any further parsing.
    logging.debug(f'[DupeCheck] DupeCheck config for tracker `{search_site}` \n {pformat(config["dupes"])}')
    dupe_check_response = dupe_check_response.json()
    
    torrent_items = dupe_check_response
    if config["dupes"]["parse_json"]["is_needed"]:
        torrent_items = dupe_check_response[str(config["dupes"]["parse_json"]["top_lvl"])]
        if "second_level" in config["dupes"]["parse_json"]:
            torrent_items = torrent_items[config["dupes"]["parse_json"]["second_level"]]

    for item in torrent_items:
        if "torrent_details" in config["dupes"]["parse_json"]:
            # BLU & ACM have us go 2 "levels" down to get torrent info -->  [data][attributes][name] = torrent title
            torrent_details = item[str(config["dupes"]["parse_json"]["torrent_details"])]
        else:
            # BHD only has us go down 1 "level" to get torrent info --> [data][name] = torrent title
            torrent_details = item
        
        torrent_name_key = config["dupes"]["parse_json"]["torrent_name"] if "torrent_name" in config["dupes"]["parse_json"] else "name"
        torrent_title = str(torrent_details[torrent_name_key])
        torrent_title_split = re.split('[.\s]', torrent_title.replace("-", " ").lower())
        torrent_title_upper_split = re.split('[.\s]', torrent_title.replace("-", " "))

        logging.debug(f'[DupeCheck] Dupe check torrent title obtained from tracker {search_site} is {torrent_title}')
        logging.debug(f'[DupeCheck] Torrent title split {torrent_title_split}')
        logging.debug(f'[DupeCheck] Torrent title split {torrent_title_upper_split}')
        # Bluray Encode
        if all(x in torrent_title_split for x in ['bluray']) and any(x in torrent_title_split for x in ['720p', '1080i', '1080p', '2160p']) and any(x in torrent_title_split for x in ['x264', 'x265', 'x 264', 'x 265']):
            existing_release_types[torrent_title] = 'bluray_encode'

        # Bluray Remux
        if all(x in torrent_title_split for x in ['bluray', 'remux']) and any(x in torrent_title_split for x in ['720p', '1080i', '1080p', '2160p']):
            existing_release_types[torrent_title] = 'bluray_remux'

        # WEB-DL
        if (any(x in torrent_title_upper_split for x in ['WEB']) or all(x in torrent_title_split for x in ['web', 'dl']) ) and (any(x in torrent_title_split for x in ['h.264', 'h264', 'h 264', 'h.265', 'h265', 'h 265', 'hevc', 'x264', 'x265', 'x.264', 'x.265', 'x 264', 'x 265'])
            or all(x in torrent_title_split for x in ['h', '265']) or all(x in torrent_title_split for x in ['h', '264'])):
            existing_release_types[torrent_title] = "webdl"

        # WEBRip
        if all(x in torrent_title_split for x in ['webrip']) and (any(x in torrent_title_split for x in ['h.264', 'h264', 'h 264', 'h.265', 'h265', 'h 265', 'hevc', 'x264', 'x265', 'x.264', 'x.265', 'x 264', 'x 265'])
            or all(x in torrent_title_split for x in ['h', '265']) or all(x in torrent_title_split for x in ['h', '264'])):
            existing_release_types[torrent_title] = "webrip"

        # HDTV
        if all(x in torrent_title_split for x in ['hdtv']):
            existing_release_types[torrent_title] = "hdtv"

        # DVD
        if all(x in torrent_title_split for x in ['dvd']):
            existing_release_types[torrent_title] = "dvd"

    logging.debug(f'[DupeCheck] Existing release types identified from tracker {search_site} are {existing_release_types}')

    # This just updates a dict with the number of a particular "type" of release exists on site (e.g. "2 bluray_encodes" or "1 bluray_remux" etc)
    for onsite_quality_type in existing_release_types.values():
        existing_releases_count[onsite_quality_type] += 1
    logging.info(msg=f'[DupeCheck] Results from initial dupe query (all resolution): {existing_releases_count}')

    # If we get no matches when searching via IMDB ID that means this content hasn't been upload in any format, no possibility for dupes
    if len(existing_release_types.keys()) == 0:
        logging.info(msg='[DupeCheck] Dupe query did not return any releases that we could parse, assuming no dupes exist.')
        console.print(f":heavy_check_mark: Yay! No dupes found on [bold]{str(config['name']).upper()}[/bold], continuing the upload process now\n")
        return False

    # --------------- Filter the existing_release_types dict to only include correct res & source_type --------------- #
    logging.debug(f'[DupeCheck] Uploading media properties. Resolution :: {torrent_info["screen_size"]}, Source ::: {torrent_info["source_type"]}')
    logging.debug(f'[DupeCheck] Filtering torrents from tracker that doesn\'t match the above properties')
    for their_title in list(existing_release_types.keys()):  # we wrap the dict keys in a "list()" so we can modify (pop) keys from it while the loop is running below
        # use guessit to get details about the release
        their_title_guessit = guessit(their_title)
        their_title_type = existing_release_types[their_title]

        # This next if statement does 2 things:
        #   1. If the torrent title from the API request doesn't have the same resolution as the file being uploaded we pop (remove) it from the dict "existing_release_types"
        #   2. If the API torrent title source type (e.g. bluray_encode) is not the same as the local file then we again pop it from the "existing_release_types" dict
        if ("screen_size" not in their_title_guessit or their_title_guessit["screen_size"] != torrent_info["screen_size"]) or their_title_type != torrent_info["source_type"]:
            existing_releases_count[their_title_type] -= 1
            existing_release_types.pop(their_title)

    logging.info(msg=f'[DupeCheck] After applying resolution & "source_type" filter: {existing_releases_count}')


    # Movies (mostly blurays) are usually a bit more flexible with dupe/trump rules due to editions, regions, etc
    # TV Shows (mostly web) are usually only allowed 1 "version" onsite & we also need to consider individual episode uploads when a season pack exists etc
    # for those reasons ^^ we place this dict here that we will use to generate the Table we show the user of possible dupes
    # By keeping it out of the fuzzy_similarity() func/loop we are able to directly insert/modify data into it when dealing with tv show dupes/trumps below
    possible_dupe_with_percentage_dict = {}  

    # If we are uploading a tv show we should only add the correct season to the existing_release_types dict
    if "s00e00" in torrent_info:
        # First check if what the user is uploading is a full season or not
        # We just want the season of whatever we are uploading so we can filter the results later 
        # (Most API requests include all the seasons/episodes of a tv show in the response, we don't need all of them)
        is_full_season = bool(len(torrent_info["s00e00"]) == 3)
        if is_full_season: # This is a full season
            season_num = str(torrent_info["s00e00"])
            episode_num  = None
        else: 
            # This is an episode (since a len of 3 would only leave room for 'S01' not 'S01E01' etc)
            season_num = str(torrent_info["s00e00"])[:-3]
            episode_num  = str(torrent_info["s00e00"])[3:]
        logging.info(msg=f'[DupeCheck] Filtering out results that are not from the same season being uploaded ({season_num})')
        
        # Loop through the results & discard everything that is not from the correct season
        number_of_discarded_seasons = 0
        for existing_release_types_key in list(existing_release_types.keys()): # process of elimination
            logging.debug(f'[DupeCheck] Trying to eliminate `{existing_release_types_key}`')
            if season_num is not None and season_num not in existing_release_types_key: # filter our wrong seasons
                logging.debug(f'[DupeCheck] Filtering out `{existing_release_types_key}` since it belongs to different season')
                existing_release_types.pop(existing_release_types_key)
                number_of_discarded_seasons += 1
                continue

            # at this point we've filtered out all the different resolutions/types/seasons
            #  so now we check each remaining title to see if its a season pack or individual episode
            # endswith case added below to prevent failures when dealing with complete packs on trackers.
            # for most cases the first check of startswith itself will return true to get the season.
            extracted_season_episode_from_title = list(filter(lambda x: x.startswith(season_num) or x.endswith(season_num), re.split("[.\s]", existing_release_types_key)))[0]
            if len(extracted_season_episode_from_title) == 3:
                logging.info(msg=f'[DupeCheck] Found a season pack for {season_num} on {search_site}')
                # TODO maybe mark the season pack as a 100% dupe or consider expanding dupe Table to allow for error messages to inform the user

                # If a full season pack is onsite then in almost all cases individual episodes from that season are not allowed to be uploaded anymore
                # check to see if that's ^^ happening, if it is then we will log it and if 'auto_mode' is enabled we also cancel the upload
                # if 'auto_mode=false' then we prompt the user & let them decide
                if not is_full_season:
                    if bool(util.strtobool(os.getenv('auto_mode'))):
                        # possible_dupe_with_percentage_dict[existing_release_types_key] = 100
                        logging.critical(msg=f'[DupeCheck] Canceling upload to {search_site} because uploading a full season pack is already available: {existing_release_types_key}')
                        return True
                    
                    logging.error("[DupeCheck] Marking existence of season pack for single episode upload.")
                    # marking this case when user is trying to upload a single episode when a season pack already exists on the tracker.
                    # when this flag is enabled, we'll show all the season packs in a table and prompt the user to decide whether or not to upload the torrent.
                    single_episode_upload_with_season_pack_available = True

            # now we just need to make sure the episode we're trying to upload is not already on site
            if not single_episode_upload_with_season_pack_available:
                number_of_discarded_episodes = 0
                if (extracted_season_episode_from_title != torrent_info['s00e00']) or (episode_num is not None and episode_num not in existing_release_types_key):
                    number_of_discarded_episodes += 1
                    existing_release_types.pop(existing_release_types_key)        

                logging.info(msg=f'[DupeCheck] Filtered out: {number_of_discarded_episodes} results for having different episode numbers (looking for {episode_num})')
        
        logging.info(msg=f'[DupeCheck] Filtered out: {number_of_discarded_seasons} results for not being the right season ({season_num})')

        
    def fuzzy_similarity(our_title, check_against_title):
        check_against_title_original = check_against_title
        # We will remove things like the title & year from the comparison stings since we know they will be exact matches anyways

        # replace DD+ with DDP from both our title and tracker results title to make the dupe check a bit more accurate since some sites like to use DD+ and others DDP but they refer to the same thing
        our_title = re.sub(r'dd\+', 'ddp', str(our_title).lower())
        check_against_title = re.sub(r'dd\+', 'ddp', str(check_against_title).lower())

        content_title = re.sub('[^0-9a-zA-Z]+', ' ', str(torrent_info["title"]).lower())

        if "year" in torrent_info:
            # Also remove the year because that *should* be an exact match, that's not relevant to detecting changes
            if str(int(torrent_info["year"]) + 1) in check_against_title:
                check_against_title_year = str(int(torrent_info["year"]) + 1)  # some releases are occasionally off by 1 year, it's still the same media so it can be used for dupe check
            elif str(int(torrent_info["year"]) - 1) in check_against_title:
                check_against_title_year = str(int(torrent_info["year"]) - 1)
            else:
                check_against_title_year = str(torrent_info["year"])
        else:
            check_against_title_year = ""

        our_title = re.sub(r'[^A-Za-z0-9 ]+', ' ', str(our_title)).lower().replace(torrent_info["screen_size"], "").replace(check_against_title_year, "")
        our_title = " ".join(our_title.split())

        check_against_title = re.sub(r'[^A-Za-z0-9 ]+', ' ', str(check_against_title)).lower().replace(torrent_info["screen_size"], "").replace(check_against_title_year, "")
        check_against_title = " ".join(check_against_title.split())

        token_set_ratio = fuzz.token_set_ratio(our_title.replace(content_title, ''), check_against_title.replace(content_title, ''))
        logging.info(f"[DupeCheck] '{check_against_title_original}' was flagged with a {str(token_set_ratio)}% dupe probability")

        # Instead of wasting time trying to create a 'low, medium, high' risk system we just have the user enter in a percentage they are comfortable with
        # if a torrent titles vs local title similarity percentage exceeds a limit the user set we immediately quit trying to upload to that site
        # since what the user considers (via token_set_ratio percentage) to be a dupe exists
        return token_set_ratio


    possible_dupes_table = Table(show_header=True, header_style="bold cyan")
    possible_dupes_table.add_column(f"Exceeds Max % ({os.getenv('acceptable_similarity_percentage')}%)", justify="left")
    possible_dupes_table.add_column(f"Possible Dupes ({str(config['name']).upper()})", justify="left")
    possible_dupes_table.add_column("Similarity %", justify="center")

    max_dupe_percentage_exceeded = False
    is_dupes_present = False
    logging.debug(f"[DupeCheck] Existing release types that are dupes: {existing_release_types}")
    for possible_dupe_title in existing_release_types.keys():
        # If we get a match then run further checks
        possible_dupe_with_percentage_dict[possible_dupe_title] = fuzzy_similarity(our_title=torrent_info["torrent_title"], check_against_title=possible_dupe_title)

    for possible_dupe in sorted(possible_dupe_with_percentage_dict, key=possible_dupe_with_percentage_dict.get, reverse=True):
        mark_as_dupe = bool(possible_dupe_with_percentage_dict[possible_dupe] >= int(os.getenv('acceptable_similarity_percentage')))
        mark_as_dupe_color = "bright_red" if mark_as_dupe else "dodger_blue1"
        mark_as_dupe_percentage_difference_raw_num = possible_dupe_with_percentage_dict[possible_dupe] - int(os.getenv('acceptable_similarity_percentage'))
        mark_as_dupe_percentage_difference = f'{"+" if mark_as_dupe_percentage_difference_raw_num >= 0 else "-"}{abs(mark_as_dupe_percentage_difference_raw_num)}%'

        possible_dupes_table.add_row(f'[{mark_as_dupe_color}]{mark_as_dupe}[/{mark_as_dupe_color}] ({mark_as_dupe_percentage_difference})', possible_dupe, f'{str(possible_dupe_with_percentage_dict[possible_dupe])}%')

        # because we want to show the user every possible dupe (not just the ones that exceed the max percentage) 
        # we just mark an outside var True & finish the for loop that adds the table rows
        # 
        # Also if `single_episode_upload_with_season_pack_available`, then we mark the release as dupe
        # TODO Should season packs be tagged as 100% dupe???
        if not max_dupe_percentage_exceeded or single_episode_upload_with_season_pack_available:
            max_dupe_percentage_exceeded = mark_as_dupe
        is_dupes_present = True

    if max_dupe_percentage_exceeded:
        console.print(f"\n\n[bold red on white] :warning: Detected possible dupe! :warning: [/bold red on white]")
        console.print(possible_dupes_table)
        
        if single_episode_upload_with_season_pack_available:
            # if this is an interactive upload then we can prompt the user & let them choose if they want to cancel or continue the upload
            logging.error(msg="[DupeCheck] Almost all trackers don't allow individual episodes to be uploaded after season pack is released")
            console.print(f"\n[bold red on white] :warning: Need user input! :warning: [/bold red on white]")
            console.print(f"You're trying to upload an [bold red]Individual Episode[/bold red] [bold green]({torrent_info['title']} {torrent_info['s00e00']})[/bold green] to [bold]{search_site}[/bold]",  highlight=False)
            console.print(f"[bold red]Season Packs[/bold red] are already available: [bold green]({existing_release_types_key})[/bold green]", highlight=False)
            console.print("Most sites [bold red]don't allow[/bold red] individual episode uploads when the season pack is available")
            console.print('---------------------------------------------------------')
            # If auto_mode is enabled then return true in all cases
            # If user chooses Yes / y => then we return False indicating that there are no dupes and processing can continue
            # If user chooses no / n => then we return True indicating that there are possible duplicates and stop the upload for the tracker
            return True if bool(util.strtobool(os.getenv('auto_mode'))) else not bool(Confirm.ask("\nIgnore and continue upload?"))
        else:
            # If auto_mode is enabled then return true in all cases
            # If user chooses Yes / y => then we return False indicating that there are no dupes and processing can continue
            # If user chooses no / n => then we return True indicating that there are possible duplicates and stop the upload for the tracker
            return True if bool(util.strtobool(os.getenv('auto_mode'))) else not bool(Confirm.ask("\nContinue upload even with possible dupe?"))
    else:
        if is_dupes_present:
            console.print(f"\n\n[bold red] :warning: Possible dupes ignored since threshold not exceeded! :warning: [/bold red]")
            console.print(possible_dupes_table)
            console.line(count=2)
            console.print(f":heavy_check_mark: Yay! No dupes identified on [bold]{str(config['name']).upper()}[/bold] that exceeds the configured threshold, continuing the upload process now\n")
        else:
            console.print(f":heavy_check_mark: Yay! No dupes identified on [bold]{str(config['name']).upper()}[/bold], continuing the upload process now\n")

        return False # no dupes proceed with processing
