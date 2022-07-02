import json
import pytest
import requests

from pathlib import Path
from pytest_mock import mocker
import utilities.utils_metadata as metadata


working_folder = Path(__file__).resolve().parent.parent.parent


class TMDBResponse:
    ok = None
    data = None

    def __init__(self, data):
        self.ok = "True"
        self.data = data

    def json(self):
        return self.data



def test_tmdb_movie_auto_select(mocker):
    query_title = "Gods of Egypt"
    query_year = "2016"
    content_type = "movie"

    tmdb_response = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Gods of Egypt.json")))
    mocker.patch("requests.get", return_value=tmdb_response)

    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Gods of Egypt.json"))


def test_tmdb_movie_cannot_auto_select(mocker):
    query_title = "Uncharted"
    query_year = "2022"
    content_type = "movie"

    tmdb_response = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Uncharted.json")))
    mocker.patch("requests.get", return_value=tmdb_response)
    mocker.patch("rich.prompt.Prompt.ask", return_value="1")
    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Uncharted.json"))


def test_tmdb_tv_auto_select(mocker):
    query_title = "Bosch Legacy"
    query_year = ""
    content_type = "episode"

    tmdb_response = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Bosch Legacy.json")))
    mocker.patch("requests.get", return_value=tmdb_response)

    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Bosch Legacy.json"))


def test_tmdb_movie_loose_search(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_response_loose = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_loose])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))
    mocker.patch("os.getenv", return_value=1)

    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1.json"))


def __auto_reuploader(key, default=None):
    if key == "tmdb_result_auto_select_threshold":
        return 1
    return default


def __upload_assistant(key, default=None):
    return default


def __auto_reuploader_loosely_configured(key, default=None):
    if key == "tmdb_result_auto_select_threshold":
        return 10
    return default


def test_tmdb_movie_no_results(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_strict])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))

    mocker.patch('os.getenv', side_effect=__auto_reuploader)

    expected = {
        "tmdb": "0",
        "imdb": "0",
        "tvmaze": "0",
        "possible_matches": None
    }

    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == expected


def test_tmdb_movie_loosely_configured_reuploader(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_response_loose = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_loose])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))
    mocker.patch('os.getenv', side_effect=__auto_reuploader_loosely_configured)

    expected = {
        "tmdb": "0",
        "imdb": "0",
        "tvmaze": "0",
        "possible_matches": None
    }
    assert metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1_loose_reuploader.json"))


def test_tmdb_movie_no_results_exit(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_strict])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))

    mocker.patch('os.getenv', side_effect=__upload_assistant)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
            metadata._metadata_search_tmdb_for_id(query_title, query_year, content_type, False)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == "No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID"


@pytest.mark.parametrize(
    ("id_site", "id_value", "external_site", "content_type", "mock_response_file", "expected"),
    [
        # IMDB Available
        pytest.param(
            "imdb", # id_site
            "123456", # id_value
            "tmdb", # external_site
            "movie", # content_type
            "imdb_available_need_tmdb_for_movie", # mock_response_file
            "557", # expected
            id="imdb_available_need_tmdb_for_movie"
        ),
        pytest.param(
            "imdb", # id_site
            "123456", # id_value
            "tmdb", # external_site
            "episode", # content_type
            "imdb_available_need_tmdb_for_episode", # mock_response_file
            "1418", # expected
            id="imdb_available_need_tmdb_for_episode"
        ),
        pytest.param(
            "imdb", # id_site
            "123456", # id_value
            "tvmaze", # external_site
            "episode", # content_type
            "imdb_available_need_tvmaze_for_episode", # mock_response_file
            "66", # expected
            id="imdb_available_need_tvmaze_for_episode"
        ),
        pytest.param(
            "imdb", # id_site
            "123456", # id_value
            "tvmaze", # external_site
            "movie", # content_type
            "imdb_available_need_tvmaze_for_movie", # mock_response_file
            "0", # expected
            id="imdb_available_need_tvmaze_for_movie" # will be called only if content_type is episode
        ),
        # TMDB Available
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "tvmaze", # external_site
            "movie", # content_type
            "tmdb_available_need_tvmaze_for_movie", # mock_response_file
            "0", # expected
            id="tmdb_available_need_tvmaze_for_movie" # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "tvmaze", # external_site
            "episode", # content_type
            "tmdb_available_need_tvmaze_for_episode", # mock_response_file
            "0", # expected
            id="tmdb_available_need_tvmaze_for_episode" # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "imdb", # external_site
            "movie", # content_type
            "tmdb_available_need_imdb_for_movie", # mock_response_file
            "tt0145487", # expected
            id="tmdb_available_need_imdb_for_movie" # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "imdb", # external_site
            "movie", # content_type
            "tmdb_available_need_imdb_for_movie", # mock_response_file
            "tt0145487", # expected
            id="tmdb_available_need_imdb_for_movie" # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "imdb", # external_site
            "episode", # content_type
            "tmdb_available_need_imdb_for_episode", # mock_response_file
            "tt0898266", # expected
            id="tmdb_available_need_imdb_for_episode" # tvmaze can be obtained only using imdb id
        ),
        pytest.param(
            "tmdb", # id_site
            "123456", # id_value
            "imdb", # external_site
            "episode", # content_type
            "tmdb_available_need_imdb_for_movie_error", # mock_response_file
            "0", # expected
            id="tmdb_available_need_imdb_for_movie_error" # tvmaze can be obtained only using imdb id
        ),
        # TVMAZE Available
        pytest.param(
            "tvmaze", # id_site
            "123123", # id_value
            "imdb", # external_site
            "episode", # content_type
            "tvmaze_available_need_imdb_for_episode", # mock_response_file
            "tt7772602", # expected
            id="tvmaze_available_need_imdb_for_episode" # tvmaze can be obtained only using imdb id
        ),
    ]
)
def test_metadata_get_external_id(id_site, id_value, external_site, content_type, mock_response_file, expected, mocker):
    mock_response_file_data = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/external_id_search/{mock_response_file}.json")))
    mocker.patch("requests.get", return_value=mock_response_file_data)

    assert metadata._metadata_get_external_id(id_site, id_value, external_site, content_type) == expected


def __api_return_values(url, **kwargs):
    print(url.url)

    if url.url == "https://api.themoviedb.org/3/search/tv?api_key=DUMMY_API_KEY&query='Peaky%20Blinders'&page=1&include_adult=false&year=2022":
        # TMDB SEARCH
        # episode_all_ids_missing
        return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/tmdb_search.json")))
    if url.url == "https://api.themoviedb.org/3/tv/60574/external_ids?api_key=DUMMY_API_KEY&language=en-US":
        # TMDB => IMDB
        # episode_all_ids_missing
        # episode_tmdb_is_present
        return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/tmdb_to_imdb.json")))
    if url.url == "https://api.tvmaze.com/lookup/shows?imdb=tt2442560":
        # IMDB => TVMAZE
        # episode_imdb_is_present
        # episode_all_ids_missing
        # episode_tmdb_is_present
        return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/imdb_to_tvmaze.json")))

    if url.url == "https://api.themoviedb.org/3/find/tt2442560?api_key=DUMMY_API_KEY&language=en-US&external_source=imdb_id":
        # IMDB => TMDB
        # episode_imdb_is_present
        # episode_tvmaze_is_present
        return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_imdb_is_present/imdb_to_tmdb.json")))


    if url.url == "https://api.tvmaze.com/shows/269":
        # TVMAZE => IMDB
        # episode_tvmaze_is_present
        return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_tvmaze_is_present/tvmaze_to_imdb.json")))

    return TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/full_id_search/XXXXXX/imdb_available_need_tmdb_for_episode.json")))


def __env_auto_uploader(param, default=None):
    if param == "TMDB_API_KEY":
        return "DUMMY_API_KEY"
    if param == "tmdb_result_auto_select_threshold":
        return 5
    return None


@pytest.mark.parametrize(
    ("torrent_info", "tmdb_id", "imdb_id", "tvmaze_id", "auto_mode", "expected"),
    [
        pytest.param(
            {"type": "episode"},
            "123123",
            "tt7654323",
            "12342",
            False,
            {"imdb":"tt7654323", "tmdb":"123123", "tvmaze":"12342", "possible_match":None},
            id="episode_all_ids_available"
        ),
        pytest.param(
            {"type": "episode"},
            ["123123"],
            ["tt7654323"],
            ["12342"],
            False,
            {"imdb":"tt7654323", "tmdb":"123123", "tvmaze":"12342", "possible_match":None},
            id="episode_all_ids_available"
        ),
        pytest.param(
            {"type": "episode"},
            "123123",
            "7654323",
            "12342",
            False,
            {"imdb":"tt7654323", "tmdb":"123123", "tvmaze":"12342", "possible_match":None},
            id="episode_all_ids_available_adding_tt"
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year":"2022"},
            "",
            "",
            "",
            False,
            {
                "imdb":"tt2442560",
                "tmdb":"60574",
                "tvmaze":"269",
                "possible_match": f"{working_folder}/tests/resources/tmdb/results/full_id_search/episode_all_ids_missing/possible_match.json"
            },
            id="episode_all_ids_missing"
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year":"2022"},
            "",
            "tt2442560",
            "",
            False,
            {
                "imdb":"tt2442560",
                "tmdb":"60574",
                "tvmaze":"269",
                "possible_match": None
            },
            id="episode_imdb_is_present"
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year":"2022"},
            "60574",
            "",
            "",
            False,
            {
                "imdb":"tt2442560",
                "tmdb":"60574",
                "tvmaze":"269",
                "possible_match": None
            },
            id="episode_tmdb_is_present"
        ),
        pytest.param(
            {"type": "episode", "title": "Peaky Blinders", "year":"2022"},
            "",
            "",
            "269",
            False,
            {
                "imdb":"tt2442560",
                "tmdb":"60574",
                "tvmaze":"269",
                "possible_match": None
            },
            id="episode_tvmaze_is_present"
        ),
    ]
)
def test_fill_database_ids(torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode, expected, mocker):
    # this mocker is so that, we can run out whole code, and we intercept http call from inside requests package.
    mocker.patch("requests.sessions.Session.send", side_effect=__api_return_values)
    mocker.patch("os.getenv", side_effect=__env_auto_uploader)

    possible_match = metadata.fill_database_ids(torrent_info, tmdb_id, imdb_id, tvmaze_id, auto_mode)
    print(torrent_info)
    print(possible_match)
    assert torrent_info["imdb"] == expected["imdb"]
    assert torrent_info["tmdb"] == expected["tmdb"]
    assert torrent_info["tvmaze"] == expected["tvmaze"]
    if expected["possible_match"] is None:
        assert possible_match == expected["possible_match"]
    else:
        assert possible_match == json.load(open(expected["possible_match"]))

