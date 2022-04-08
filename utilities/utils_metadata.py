import os
import sys
import logging
import requests

from rich import box
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def do_tmdb_search(url):
    return requests.get(url)


def metadata_search_tmdb_for_id(query_title, year, content_type, auto_mode):
    console.line(count=2)
    console.rule(f"TMDB Search Results", style='red', align='center')
    console.line(count=1)

    # sanitizing query_title
    escaped_query_title = f'\'{query_title}\''

    content_type = "tv" if content_type == "episode" else content_type # translation for TMDB API
    query_year = "&year=" + str(year) if len(year) != 0 else ""

    result_num = 0
    result_dict = {}

    logging.info(f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/search/{content_type}?api_key=<REDACTED>&query={escaped_query_title}&page=1&include_adult=false{query_year}")
    search_tmdb_request = do_tmdb_search(f"https://api.themoviedb.org/3/search/{content_type}?api_key={os.getenv('TMDB_API_KEY')}&query={escaped_query_title}&page=1&include_adult=false{query_year}")

    if search_tmdb_request.ok:
        # print(json.dumps(search_tmdb_request.json(), indent=4, sort_keys=True))
        if len(search_tmdb_request.json()["results"]) == 0:
            logging.critical("[MetadataUtils] No results found on TMDB using the title '{}' and the year '{}'".format(escaped_query_title, year))
            logging.info("[MetadataUtils] Attempting to do a more liberal TMDB Search")
            
            search_tmdb_request = do_tmdb_search(f"https://api.themoviedb.org/3/search/{content_type}?api_key={os.getenv('TMDB_API_KEY')}&query={query_title}&page=1&include_adult=false{query_year}")
            
            if search_tmdb_request.ok:
                if len(search_tmdb_request.json()["results"]) == 0:
                    logging.critical("[MetadataUtils] No results found on TMDB using the title '{}' and the year '{}'".format(query_title, year))
                    if (int(os.getenv("tmdb_result_auto_select_threshold")) or 1) >= 0:
                        return {
                            "tmdb": "0",
                            "imdb": "0",
                            "tvmaze": "0",
                            "possible_matches": None
                        }
                    else:
                        sys.exit("No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID")
            else:
                if (int(os.getenv("tmdb_result_auto_select_threshold")) or 1) >= 0:
                    return {
                        "tmdb": "0",
                        "imdb": "0",
                        "tvmaze": "0",
                        "possible_matches": None
                    }
                else:
                    sys.exit("No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID")
        else:
            query_title = escaped_query_title
        logging.info(f"[MetadataUtils] TMDB search has returned proper responses. Parseing and identifying the proper TMDB Id")
        logging.info(f'[MetadataUtils] TMDB Search parameters. Title :: {query_title}, Year :: {year}')
        tmdb_search_results = Table(show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim")
        tmdb_search_results.add_column("Result #", justify="center")
        tmdb_search_results.add_column("Title", justify="center")
        tmdb_search_results.add_column("TMDB URL", justify="center")
        tmdb_search_results.add_column("Release Date", justify="center")
        tmdb_search_results.add_column("Language", justify="center")
        tmdb_search_results.add_column("Overview", justify="center")
        
        selected_tmdb_results = 0
        selected_tmdb_results_data = []
        for possible_match in search_tmdb_request.json()["results"]:
            
            result_num += 1  # This counter is used so that when we prompt a user to select a match, we know which one they are referring to
            result_dict[str(result_num)] = possible_match["id"]  # here we just associate the number count ^^ with each results TMDB ID

            # ---- Parse the output and process it ---- #
            # Get the movie/tv 'title' from json response
            # TMDB will return either "title" or "name" depending on if the content your searching for is a TV show or movie
            title_match = list(map(possible_match.get, filter(lambda x: x in "title, name", possible_match)))
            title_match_result = "N.A."
            if len(title_match) > 0:
                title_match_result = title_match.pop()
            else:
                logging.error(f"[MetadataUtils] Title not found on TMDB for TMDB ID: {str(possible_match['id'])}")
            logging.info(f'[MetadataUtils] Selected Title: [{title_match_result}]')

            # Same situation as with the movie/tv title. The key changes depending on what the content type is
            selected_year = "N.A."
            year_match = list(map(possible_match.get, filter(lambda x: x in "release_date, first_air_date", possible_match)))
            if len(year_match) > 0:
                selected_year = year_match.pop()
            else:
                logging.error(f"[MetadataUtils] Year not found on TMDB for TMDB ID: {str(possible_match['id'])}")
            logging.info(f'[MetadataUtils] Selected Year: [{selected_year}]')
            
            # attempting to eliminate tmdb results based on year.
            # if the year we have is 2005, then we will only consider releases from year 2004, 2005 and 2006
            # entries from all other years will be eliminated
            if content_type == "tv":
                logging.info("[MetadataUtils] Skipping year matching since this is an episode.")
            elif year != "" and int(year) > 0 and selected_year != "N.A." and len(selected_year) > 0:
                year = int(year)
                selected_year_sub_part = int(selected_year.split("-")[0])
                logging.info(f"[MetadataUtils] Applying year filter. Expected years are [{year - 1}, {year}, or {year + 1}]. Obtained year [{selected_year_sub_part}]")
                if selected_year_sub_part == year or  selected_year_sub_part == year - 1 or  selected_year_sub_part == year + 1:
                    logging.debug(f"[MetadataUtils] The possible match has passed the year filter")
                else:
                    logging.info(f"[MetadataUtils] The possible match failed to pass year filter.")
                    del result_dict[str(result_num)]
                    result_num -= 1
                    continue

            if "overview" in possible_match:
                if len(possible_match["overview"]) > 1:
                    overview = possible_match["overview"]
                else:
                    logging.error(f"[MetadataUtils] Overview not found on TMDB for TMDB ID: {str(possible_match['id'])}")
                    overview = "N.A."
            else:
                overview = "N.A."
            # ---- (DONE) Parse the output and process it (DONE) ---- #

            # Now add that json data to a row in the table we show the user
            selected_tmdb_results_data.append({
                "result_num": result_num,
                "title": title_match_result,
                "content_type": content_type,
                "tmdb_id": possible_match['id'],
                "release_date": selected_year,
                "language": possible_match["original_language"],
                "overview": overview
            })
            tmdb_search_results.add_row(
                f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]", title_match_result,
                f"themoviedb.org/{content_type}/{str(possible_match['id'])}", str(selected_year), possible_match["original_language"], overview, end_section=True )
            selected_tmdb_results += 1

        logging.info(f"[MetadataUtils] Total number of results for TMDB search: {str(result_num)}")
        if result_num < 1:
            console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
            logging.info(f"[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
            return {
                "tmdb": "0",
                "imdb": "0",
                "tvmaze": "0",
                "possible_matches": selected_tmdb_results_data
            }
        # once the loop is done we can show the table to the user
        console.print(tmdb_search_results, justify="center")
        
        list_of_num = []  # here we convert our integer that was storing the total num of results into a list
        for i in range(result_num):
            i += 1
            # The idea is that we can then show the user all valid options they can select
            list_of_num.append(str(i))

        if auto_mode == 'false' and selected_tmdb_results > 1 and (os.getenv("auto_select_tmdb_result") or False):
            # prompt for user input with 'list_of_num' working as a list of valid choices
            user_input_tmdb_id_num = Prompt.ask("Input the correct Result #", choices=list_of_num, default="1")
        elif selected_tmdb_results <= (int(os.getenv("tmdb_result_auto_select_threshold")) or 1) or (os.getenv("tmdb_result_auto_select_threshold") or 1) == 0:
            # if user configured `tmdb_result_auto_select_threshold` as 0, then we can proceed
            # or
            # selected_tmdb_results must be less than or equal to the threshold configured,
            console.print("Auto selected the #1 result from TMDB...")
            user_input_tmdb_id_num = "1"
            logging.info(f"[MetadataUtils] auto_mode is enabled so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")
        else:
            console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
            logging.info(f"[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
            return {
                "tmdb": "0",
                "imdb": "0",
                "tvmaze": "0",
                "possible_matches": selected_tmdb_results_data
            }

        # We take the users (valid) input (or auto selected number) and use it to retrieve the appropriate TMDB ID
        # torrent_info["tmdb"] = str(result_dict[user_input_tmdb_id_num])
        tmdb = str(result_dict[user_input_tmdb_id_num])
        # Now we can call the function 'metadata_get_external_id()' to try and identify the IMDB ID (insert it into torrent_info dict right away)
        imdb = str(metadata_get_external_id(id_site='tmdb', id_value=tmdb, external_site="imdb", content_type=content_type))
        if content_type in ["episode", "tv"]:  # getting TVmaze ID
            # Now we can call the function 'metadata_get_external_id()' to try and identify the TVmaze ID (insert it into torrent_info dict right away)
            tvmaze = str(metadata_get_external_id(id_site='imdb', id_value=imdb, external_site="tvmaze", content_type=content_type))
        else:
            tvmaze = "0"
        return {
            "tmdb": tmdb,
            "imdb": imdb,
            "tvmaze": tvmaze,
            "possible_matches": selected_tmdb_results_data
        }
    else:
        return {
            "tmdb": "0",
            "imdb": "0",
            "tvmaze": "0",
            "possible_matches": selected_tmdb_results_data
        }


def metadata_get_external_id(id_site, id_value, external_site, content_type):
    """
        This method is called when we need to get id for `external_site` using the id `id_value` which we already have for site `id_site`

        imdb id can be obtained from tmdb id
        tmdb id can be obtained from imdb id
        tvmaze id can be obtained from imdb id
    """

    content_type = "tv" if content_type == "episode" else content_type  # translation for TMDB API

    get_imdb_id_from_tmdb_url = f"https://api.themoviedb.org/3/{content_type}/{id_value}/external_ids?api_key={os.getenv('TMDB_API_KEY')}&language=en-US"
    get_tmdb_id_from_imdb_url = f"https://api.themoviedb.org/3/find/{id_value}?api_key={os.getenv('TMDB_API_KEY')}&language=en-US&external_source=imdb_id"
    get_tvmaze_id_from_imdb_url = f"https://api.tvmaze.com/lookup/shows?imdb={id_value}"
    get_imdb_id_from_tvmaze_url = f"https://api.tvmaze.com/shows/{id_value}"
    
    try:
        if external_site == "imdb": # we need imdb id
            if id_site == "tmdb": # we have tmdb id
                logging.info(f"[MetadataUtils] GET Request For IMDB Lookup: https://api.themoviedb.org/3/{content_type}/{id_value}/external_ids?api_key=<REDACTED>&language=en-US")
                imdb_id_request = requests.get(get_imdb_id_from_tmdb_url).json()
                if imdb_id_request["imdb_id"] is None:
                    logging.debug(f"[MetadataUtils] Returning imdb id as `0`")
                    return "0"
                logging.debug(f"[MetadataUtils] Returning imdb id as `{imdb_id_request['imdb_id']}`")
                return imdb_id_request["imdb_id"] if imdb_id_request["imdb_id"] is not None else "0"
            else: # we have tvmaze
                logging.info(f"[MetadataUtils] GET Request For IMDB Lookup: {get_imdb_id_from_tvmaze_url}")
                imdb_id_request = requests.get(get_imdb_id_from_tvmaze_url).json()
                logging.debug(f"[MetadataUtils] Returning imdb id as `{imdb_id_request['externals']['imdb']}`")
                return imdb_id_request['externals']['imdb'] if imdb_id_request['externals']['imdb'] is not None else "0"
        elif external_site == "tvmaze": # we need tvmaze id
            # tv maze needs imdb id to search
            if id_site == "imdb":
                logging.info(f"[MetadataUtils] GET Request For TVMAZE Lookup: {get_tvmaze_id_from_imdb_url}")
                tvmaze_id_request = requests.get(get_tvmaze_id_from_imdb_url).json()
                logging.debug(f"[MetadataUtils] Returning tvmaze id as `{tvmaze_id_request['id']}`")
                return tvmaze_id_request["id"] if tvmaze_id_request["id"] is not None else "0"
            else:
                logging.error(f"[MetadataUtils] Cannot fetch tvmaze id without imdb id.")
                logging.debug(f"[MetadataUtils] Returning tvmaze id as `0`")
                return "0"
        else: # we need tmdb id
            logging.info(f"[MetadataUtils] GET Request For TMDB Lookup: https://api.themoviedb.org/3/find/{id_value}?api_key=<REDACTED>&language=en-US&external_source=imdb_id")
            tmdb_id_request = requests.get(get_tmdb_id_from_imdb_url).json()
            for item in tmdb_id_request:
                if len(tmdb_id_request[item]) == 1:
                    logging.debug(f"[MetadataUtils] Returning tmdb id as `{str(tmdb_id_request[item][0]['id'])}`")
                    return str(tmdb_id_request[item][0]["id"]) if tmdb_id_request[item][0]["id"] is not None else "0"
    except Exception as ex:
        logging.exception(f"[MetadataUtils] Error while fetching external id. Returning `0` as the id")
        return "0"


def search_for_mal_id(content_type, tmdb_id, torrent_info):
    # if 'content_type == tv' then we need to get the TVDB ID since we're going to need it to try and get the MAL ID
    # the below mapping is needed for the Flask app hosted by the original dev.
    # TODO convert this api call to use the metadata locally
    temp_map = {
        "tvdb":0,
        "mal":0,
        "tmdb":tmdb_id
    }
    if content_type == 'tv':
        get_tvdb_id = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={os.getenv('TMDB_API_KEY')}&language=en-US"
        logging.info(f"[MetadataUtils] GET Request For TVDB Lookup: https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key=<REDACTED>&language=en-US")
        get_tvdb_id_response = requests.get(get_tvdb_id).json()
        # Look for the tvdb_id key
        if 'tvdb_id' in get_tvdb_id_response and get_tvdb_id_response['tvdb_id'] is not None:
            temp_map["tvdb"] = str(get_tvdb_id_response['tvdb_id'])

    # We use this small dict to auto fill the right values into the url request below
    content_type_to_value_dict = {'movie': 'tmdb', 'tv': 'tvdb'}

    # Now we we get the MAL ID

    # Before you get too concerned, this address is a flask app I quickly set up to convert TMDB/IMDB IDs to mal using this project/collection https://github.com/Fribb/anime-lists
    # You can test it out yourself with the url: http://195.201.146.92:5000/api/?tmdb=10515 to see what it returns (it literally just returns the number "513" which is the corresponding MAL ID)
    # I might just start include the "tmdb --> mal .json" map with this bot instead of selfhosting it as an api, but for now it works so I'll revisit the subject later
    tmdb_tvdb_id_to_mal = f"http://195.201.146.92:5000/api/?{content_type_to_value_dict[content_type]}={temp_map[content_type_to_value_dict[content_type]]}"
    logging.info(f"[MetadataUtils] GET Request For MAL Lookup: {tmdb_tvdb_id_to_mal}")
    mal_id_response = requests.get(tmdb_tvdb_id_to_mal)

    # If the response returns http code 200 that means that a number has been returned, it'll either be the real mal ID or it will just be 0, either way we can use it
    if mal_id_response.status_code == 200:
        temp_map["mal"] = str(mal_id_response.json())
    return temp_map["tvdb"], temp_map["mal"]


def metadata_compare_tmdb_data_local(torrent_info):
    # We need to use TMDB to make sure we set the correct title & year as well as correct punctuation so we don't get held up in torrent moderation queues
    # I've outlined some scenarios below that can trigger issues if we just try to copy and paste the file name as the title

    # 1. For content that is 'non-english' we typically have a foreign title that we can (should) include in the torrent title using 'AKA' (K so both TMDB & OMDB API do not include this info, so we arent doing this)
    # 2. Some content has special characters (e.g.  The Hobbit: An Unexpected Journey   or   Welcome, or No Trespassing  ) we need to include these in the torrent title
    # 3. For TV Shows, Scene groups typically don't include the episode title in the filename, but we get this info from TMDB and include it in the title
    # 4. Occasionally movies that have a release date near the start of a new year will be using the incorrect year (e.g. the movie '300 (2006)' is occasionally mislabeled as '300 (2007)'

    # This will run regardless is auto_mode is set to true or false since I consider it pretty important to comply with all site rules and avoid creating extra work for tracker staff

    # default values
    title = torrent_info["title"]
    year = torrent_info["year"] if "year" in torrent_info else None
    tvdb = "0"
    mal = "0"

    if torrent_info["type"] == "episode":  # translation for TMDB API
        content_type = "tv"
        content_title = "name"  # Again TV shows on TMDB have different keys then movies so we need to set that here
    else:
        content_type = torrent_info["type"]
        content_title = "title"

    # We should only need 1 API request, so do that here
    get_media_info_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key={os.getenv('TMDB_API_KEY')}"

    get_media_info = requests.get(get_media_info_url).json()
    logging.info(f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key=<REDACTED>")

    # Check the genres for 'Animation', if we get a hit we should check for a MAL ID just in case
    if "genres" in get_media_info:
        for genre in get_media_info["genres"]:
            if genre["name"] == 'Animation':
                tvdb, mal = search_for_mal_id(content_type=content_type, tmdb_id=torrent_info["tmdb"], torrent_info=torrent_info)

    # Acquire and set the title we get from TMDB here
    if content_title in get_media_info:
        title = get_media_info[content_title]
        logging.info(f"[MetadataUtils] Using the title we got from TMDB: {title}")

    # Set the year (if exists)
    if "release_date" in get_media_info and len(get_media_info["release_date"]) > 0:
        # if len(get_media_info["release_date"]) > 0:
        year = get_media_info["release_date"][:4]
        logging.info(f"[MetadataUtils] Using the year we got from TMDB: {year}")
    return title, year, tvdb, mal
