import json
import pytest

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

    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Gods of Egypt.json"))


def test_tmdb_movie_cannot_auto_select(mocker):
    query_title = "Uncharted"
    query_year = "2022"
    content_type = "movie"

    tmdb_response = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Uncharted.json")))
    mocker.patch("requests.get", return_value=tmdb_response)
    mocker.patch("rich.prompt.Prompt.ask", return_value="1")
    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Uncharted.json"))


def test_tmdb_tv_auto_select(mocker):
    query_title = "Bosch Legacy"
    query_year = ""
    content_type = "episode"

    tmdb_response = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Bosch Legacy.json")))
    mocker.patch("requests.get", return_value=tmdb_response)

    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Bosch Legacy.json"))


def test_tmdb_movie_loose_search(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_response_loose = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_loose])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))
    mocker.patch("os.getenv", return_value=1)

    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1.json"))


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

    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == expected


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
    assert metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False) == json.load(open(f"{working_folder}/tests/resources/tmdb/expected/Kung Fu Panda 1_loose_reuploader.json"))


def test_tmdb_movie_no_results_exit(mocker, monkeypatch):
    query_title = "Kung Fu Panda 1"
    query_year = "2008"
    content_type = "movie"

    tmdb_response_strict = TMDBResponse(json.load(open(f"{working_folder}/tests/resources/tmdb/results/Kung Fu Panda 1_strict.json")))
    tmdb_responses = iter([tmdb_response_strict, tmdb_response_strict])
    monkeypatch.setattr('requests.get', lambda url: next(tmdb_responses))

    mocker.patch('os.getenv', side_effect=__upload_assistant)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
            metadata.metadata_search_tmdb_for_id(query_title, query_year, content_type, False)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == "No results found on TMDB, try running this script again but manually supply the TMDB or IMDB ID"


