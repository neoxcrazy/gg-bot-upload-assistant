import os
import sys
import logging
import requests

from rich import box
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt


console = Console()


def _do_tmdb_search(url):
    return requests.get(url)


def __is_auto_reuploader():
    return os.getenv("tmdb_result_auto_select_threshold", None) is not None


def _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data=None):
    # `auto_select_tmdb_result` => This property is present in upload assistant.
    #   For upload assistant if we don't get any results from TMDB, we stop the program.
    #
    # `tmdb_result_auto_select_threshold` => This property is present in auto reuploader.
    # For auto reuploader
    #           1. `auto_select_tmdb_result` will not be present and
    #           2. `tmdb_result_auto_select_threshold` will be present
    #   we return every id as `0` and the auto_reupload will flag the torrent as TMDB_IDENTIFICATION_FAILED
    if __is_auto_reuploader():
        return {
            "tmdb": "0",
            "imdb": "0",
            "tvmaze": "0",
            "possible_matches": selected_tmdb_results_data
        }
    else:
        sys.exit("No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID")


def _metadata_search_tmdb_for_id(query_title, year, content_type, auto_mode):
    console.line(count=2)
    console.rule("TMDB Search Results", style='red', align='center')
    console.line(count=1)

    # sanitizing query_title
    escaped_query_title = f'\'{query_title}\''

    # translation for TMDB API
    content_type = "tv" if content_type == "episode" else content_type
    query_year = "&year=" + str(year) if len(year) != 0 else ""

    result_num = 0
    result_dict = {}

    # here we do a two phase tmdb search. Initially we do a search with escaped title eg: 'Kung fu Panda 1'.
    # TMDB will try to match the exact title to return results. If we get data here, we proceed with it.
    #
    # if we don't get data for the escaped title request, then we do another request to get data without escaped query.
    logging.info(
        f"[MetadataUtils] GET Request: https://api.themoviedb.org/3/search/{content_type}?api_key=<REDACTED>&query={escaped_query_title}&page=1&include_adult=false{query_year}")
    # doing search with escaped title (strict search)
    search_tmdb_request = _do_tmdb_search(
        f"https://api.themoviedb.org/3/search/{content_type}?api_key={os.getenv('TMDB_API_KEY')}&query={escaped_query_title}&page=1&include_adult=false{query_year}")

    if search_tmdb_request.ok:
        # print(json.dumps(search_tmdb_request.json(), indent=4, sort_keys=True))
        if len(search_tmdb_request.json()["results"]) == 0:
            logging.critical("[MetadataUtils] No results found on TMDB using the title '{}' and the year '{}'".format(escaped_query_title, year))
            logging.info("[MetadataUtils] Attempting to do a more liberal TMDB Search")
            # doing request without escaped title (search is not strict)
            search_tmdb_request = _do_tmdb_search(
                f"https://api.themoviedb.org/3/search/{content_type}?api_key={os.getenv('TMDB_API_KEY')}&query={query_title}&page=1&include_adult=false{query_year}")

            if search_tmdb_request.ok:
                if len(search_tmdb_request.json()["results"]) == 0:
                    logging.critical(f"[MetadataUtils] No results found on TMDB using the title '{query_title}' and the year '{year}'")
                    return _return_for_reuploader_and_exit_for_assistant()
            else:
                return _return_for_reuploader_and_exit_for_assistant()

        query_title = escaped_query_title
        logging.info("[MetadataUtils] TMDB search has returned proper responses. Parseing and identifying the proper TMDB Id")
        logging.info(f'[MetadataUtils] TMDB Search parameters. Title :: {query_title}, Year :: \'{year}\'')

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
            # here we just associate the number count ^^ with each results TMDB ID
            result_dict[str(result_num)] = possible_match["id"]

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
            # TODO implement the tmdb title 1:1 comparision here

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
                if selected_year_sub_part == year or selected_year_sub_part == year - 1 or selected_year_sub_part == year + 1:
                    logging.debug("[MetadataUtils] The possible match has passed the year filter")
                else:
                    logging.info("[MetadataUtils] The possible match failed to pass year filter.")
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
                f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]",
                title_match_result,
                f"themoviedb.org/{content_type}/{str(possible_match['id'])}",
                str(selected_year),
                possible_match["original_language"],
                overview,
                end_section=True
            )
            selected_tmdb_results += 1

        logging.info(f"[MetadataUtils] Total number of results for TMDB search: {str(result_num)}")
        if result_num < 1:
            console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
            logging.info("[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
            _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data)

        # once the loop is done we can show the table to the user
        console.print(tmdb_search_results, justify="center")

        # here we convert our integer that was storing the total num of results into a list
        list_of_num = []
        for i in range(result_num):
            i += 1
            # The idea is that we can then show the user all valid options they can select
            list_of_num.append(str(i))


        if __is_auto_reuploader():
            if selected_tmdb_results <= int(os.getenv("tmdb_result_auto_select_threshold", 1)) or int(os.getenv("tmdb_result_auto_select_threshold", 1)) == 0:
                console.print("Auto selected the #1 result from TMDB...")
                user_input_tmdb_id_num = "1"
                logging.info(f"[MetadataUtils] `tmdb_result_auto_select_threshold` is valid so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")
            else:
                console.print("Cannot auto select a TMDB id. Marking this upload as [bold red]TMDB_IDENTIFICATION_FAILED[/bold red]")
                logging.info("[MetadataUtils] Cannot auto select a TMDB id. Marking this upload as TMDB_IDENTIFICATION_FAILED")
                return {
                    "tmdb": "0",
                    "imdb": "0",
                    "tvmaze": "0",
                    "possible_matches": selected_tmdb_results_data
                }
        else:
            if auto_mode == 'true' or selected_tmdb_results == 1:
                console.print("Auto selected the #1 result from TMDB...")
                user_input_tmdb_id_num = "1"
                logging.info(f"[MetadataUtils] 'auto_mode' is enabled or 'only 1 result from TMDB', so we are auto selecting #1 from tmdb results (TMDB ID: {str(result_dict[user_input_tmdb_id_num])})")
            else:
                # prompt for user input with 'list_of_num' working as a list of valid choices
                user_input_tmdb_id_num = Prompt.ask("Input the correct Result #", choices=list_of_num, default="1")


        # We take the users (valid) input (or auto selected number) and use it to retrieve the appropriate TMDB ID
        # torrent_info["tmdb"] = str(result_dict[user_input_tmdb_id_num])
        tmdb = str(result_dict[user_input_tmdb_id_num])
        # Now we can call the function '_metadata_get_external_id()' to try and identify the IMDB ID (insert it into torrent_info dict right away)
        imdb = str(_metadata_get_external_id(id_site='tmdb', id_value=tmdb, external_site="imdb", content_type=content_type))
        if content_type in ["episode", "tv"]:  # getting TVmaze ID
            # Now we can call the function '_metadata_get_external_id()' to try and identify the TVmaze ID (insert it into torrent_info dict right away)
            tvmaze = str(_metadata_get_external_id(id_site='imdb', id_value=imdb, external_site="tvmaze", content_type=content_type))
        else:
            tvmaze = "0"
        return {
            "tmdb": tmdb,
            "imdb": imdb,
            "tvmaze": tvmaze,
            "possible_matches": selected_tmdb_results_data
        }
    else:
        _return_for_reuploader_and_exit_for_assistant(selected_tmdb_results_data)


def _metadata_get_external_id(id_site, id_value, external_site, content_type):
    """
        This method is called when we need to get id for `external_site` using the id `id_value` which we already have for site `id_site`

        imdb id can be obtained from tmdb id
        tmdb id can be obtained from imdb id
        tvmaze id can be obtained from imdb id
    """

    # translation for TMDB API
    content_type = "tv" if content_type == "episode" else content_type

    get_imdb_id_from_tmdb_url = f"https://api.themoviedb.org/3/{content_type}/{id_value}/external_ids?api_key={os.getenv('TMDB_API_KEY')}&language=en-US"
    get_tmdb_id_from_imdb_url = f"https://api.themoviedb.org/3/find/{id_value}?api_key={os.getenv('TMDB_API_KEY')}&language=en-US&external_source=imdb_id"
    get_tvmaze_id_from_imdb_url = f"https://api.tvmaze.com/lookup/shows?imdb={id_value}"
    get_imdb_id_from_tvmaze_url = f"https://api.tvmaze.com/shows/{id_value}"

    try:
        if external_site == "imdb":  # we need imdb id
            if id_site == "tmdb":  # we have tmdb id
                logging.info(f"[MetadataUtils] GET Request For IMDB Lookup: https://api.themoviedb.org/3/{content_type}/{id_value}/external_ids?api_key=<REDACTED>&language=en-US")
                imdb_id_request = requests.get(get_imdb_id_from_tmdb_url).json()
                if imdb_id_request["imdb_id"] is None or len(imdb_id_request["imdb_id"]) < 1:
                    logging.debug("[MetadataUtils] Returning imdb id as `0`")
                    return "0"
                logging.debug(f"[MetadataUtils] Returning imdb id as `{imdb_id_request['imdb_id']}`")
                return imdb_id_request["imdb_id"] if imdb_id_request["imdb_id"] is not None else "0"
            else:  # we have tvmaze
                logging.info(f"[MetadataUtils] GET Request For IMDB Lookup: {get_imdb_id_from_tvmaze_url}")
                imdb_id_request = requests.get(get_imdb_id_from_tvmaze_url).json()
                logging.debug(f"[MetadataUtils] Returning imdb id as `{imdb_id_request['externals']['imdb']}`")
                return imdb_id_request['externals']['imdb'] if imdb_id_request['externals']['imdb'] is not None else "0"
        elif external_site == "tvmaze":  # we need tvmaze id
            # tv maze needs imdb id to search
            if id_site == "imdb":
                logging.info(f"[MetadataUtils] GET Request For TVMAZE Lookup: {get_tvmaze_id_from_imdb_url}")
                tvmaze_id_request = requests.get(get_tvmaze_id_from_imdb_url).json()
                logging.debug(f"[MetadataUtils] Returning tvmaze id as `{tvmaze_id_request['id']}`")
                return str(tvmaze_id_request["id"]) if tvmaze_id_request["id"] is not None else "0"
            else:
                logging.error("[MetadataUtils] Cannot fetch tvmaze id without imdb id.")
                logging.debug("[MetadataUtils] Returning tvmaze id as `0`")
                return "0"
        else:  # we need tmdb id
            logging.info(f"[MetadataUtils] GET Request For TMDB Lookup: https://api.themoviedb.org/3/find/{id_value}?api_key=<REDACTED>&language=en-US&external_source=imdb_id")
            tmdb_id_request = requests.get(get_tmdb_id_from_imdb_url).json()
            for item in tmdb_id_request:
                if len(tmdb_id_request[item]) == 1:
                    logging.debug(f"[MetadataUtils] Returning tmdb id as `{str(tmdb_id_request[item][0]['id'])}`")
                    return str(tmdb_id_request[item][0]["id"]) if tmdb_id_request[item][0]["id"] is not None else "0"
            # TODO see how we can get tmdb id if we have tvmaze id
    except Exception:
        logging.exception("[MetadataUtils] Error while fetching external id. Returning `0` as the id")
        return "0"


def search_for_mal_id(content_type, tmdb_id, torrent_info):
    # if 'content_type == tv' then we need to get the TVDB ID since we're going to need it to try and get the MAL ID
    # the below mapping is needed for the Flask app hosted by the original dev.
    # TODO convert this api call to use the metadata locally
    temp_map = {
        "tvdb": 0,
        "mal": 0,
        "tmdb": tmdb_id
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
        # Again TV shows on TMDB have different keys then movies so we need to set that here
        content_title = "name"
    else:
        content_type = torrent_info["type"]
        content_title = "title"

    # We should only need 1 API request, so do that here
    get_media_info_url = f"https://api.themoviedb.org/3/{content_type}/{torrent_info['tmdb']}?api_key={os.getenv('TMDB_API_KEY')}"

    try:
        get_media_info = requests.get(get_media_info_url).json()
    except Exception:
        logging.exception('[MetadataUtils] Failed to get TVDB and MAL id from TMDB.')
        return title, year, tvdb, mal

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


# ---------------------------------------------------------------------- #
#           !!! WARN !!! This Method has side effects. !!! WARN !!!
# ---------------------------------------------------------------------- #
# The method rewrites the following fields in torrent_info
# imdb, tmdb, tvmaze
# The method returns the data obtained from tmdb after filtering
def fill_database_ids(torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode):
    movie_db_providers = ['imdb', 'tmdb', 'tvmaze']
    possible_matches = None
    # small sanity check
    if not isinstance(tmdb_id, list):
        tmdb_id = [tmdb_id]
    if not isinstance(imdb_id, list):
        imdb_id = [imdb_id]
    if not isinstance(tvmaze_id, list):
        tvmaze_id = [tvmaze_id]
    # -------- Get TMDB & IMDB ID --------
    # If the TMDB/IMDB was not supplied then we need to search TMDB for it using the title & year
    for media_id_key, media_id_val in {"tmdb": tmdb_id, "imdb": imdb_id, "tvmaze": tvmaze_id}.items():
        # we include ' > 1 ' to prevent blank ID's and issues later
        if media_id_val[0] is not None and len(media_id_val[0]) > 1:
            # We have one more check here to verify that the "tt" is included for the IMDB ID (TMDB won't accept it if it doesnt)
            if media_id_key == 'imdb' and not str(media_id_val[0]).lower().startswith('tt'):
                torrent_info[media_id_key] = f'tt{media_id_val[0]}'
            else:
                torrent_info[media_id_key] = media_id_val[0]

    if all(x in torrent_info for x in movie_db_providers):
        # This means both the TMDB & IMDB ID are already in the torrent_info dict
        logging.info("[Main] TMDB, TVmaze & IMDB ID have been identified from media_info, so no need to make any TMDB API request")

    elif any(x in torrent_info for x in ['imdb', 'tmdb', 'tvmaze']):
        # This means we can skip the search via title/year and instead use whichever ID to get the other (tmdb -> imdb and vice versa)
        ids_present = list(filter(lambda id: id in torrent_info, movie_db_providers))
        ids_missing = [id for id in movie_db_providers if id not in ids_present]

        logging.info(f"[Main] We have '{ids_present}' with us currently.")
        logging.info(f"[Main] We are missing '{ids_missing}' starting External Database API requests now")
        # highest priority is given to imdb id.
        # if imdb id is provided by the user, then we use it to figure our the other two ids.
        # else we go for tmdb id and then tvmaze id

        if "imdb" in ids_present:
            # imdb id is available.
            torrent_info["tmdb"] = _metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tmdb", content_type=torrent_info["type"])
            if torrent_info["type"] == "episode":
                torrent_info["tvmaze"] = _metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tvmaze", content_type=torrent_info["type"])
            else:
                torrent_info["tvmaze"] = "0"
        elif "tmdb" in ids_present:
            torrent_info["imdb"] = _metadata_get_external_id(id_site="tmdb", id_value=torrent_info["tmdb"], external_site="imdb", content_type=torrent_info["type"])
            # we got value for imdb id, now we can use that to find out the tvmaze id
            if torrent_info["type"] == "episode":
                torrent_info["tvmaze"] = _metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tvmaze", content_type=torrent_info["type"])
        elif "tvmaze" in ids_present:
            if torrent_info["type"] == "episode":
                # we get the imdb id from tvmaze
                torrent_info["imdb"] = _metadata_get_external_id(id_site="tvmaze", id_value=torrent_info["tvmaze"], external_site="imdb", content_type=torrent_info["type"])
                # and use the imdb id to find out the tmdb id
                torrent_info["tmdb"] = _metadata_get_external_id(id_site="imdb", id_value=torrent_info["imdb"], external_site="tmdb", content_type=torrent_info["type"])
            else:
                logging.fatal("[Main] TVMaze id provided for a non TV show. trying to identify 'TMDB' & 'IMDB' ID via title & year")
                # this method searchs and gets all three ids ` 'imdb', 'tmdb', 'tvmaze' `
                metadata_result = _metadata_search_tmdb_for_id(
                    query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"], auto_mode=auto_mode)
                torrent_info["tmdb"] = metadata_result["tmdb"]
                torrent_info["imdb"] = metadata_result["imdb"]
                torrent_info["tvmaze"] = metadata_result["tvmaze"]
                possible_matches = metadata_result["possible_matches"]
    else:
        logging.info("[Main] We are missing the 'TMDB', 'TVMAZE' & 'IMDB' ID, trying to identify it via title & year")
        # this method searchs and gets all three ids ` 'imdb', 'tmdb', 'tvmaze' `
        metadata_result = _metadata_search_tmdb_for_id(
            query_title=torrent_info["title"], year=torrent_info["year"] if "year" in torrent_info else "", content_type=torrent_info["type"], auto_mode=auto_mode
        )

        torrent_info["tmdb"] = metadata_result["tmdb"]
        torrent_info["imdb"] = metadata_result["imdb"]
        torrent_info["tvmaze"] = metadata_result["tvmaze"]
        possible_matches = metadata_result["possible_matches"]
    return possible_matches