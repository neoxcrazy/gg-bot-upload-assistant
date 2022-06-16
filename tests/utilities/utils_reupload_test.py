import json
import pytest

from pytest_mock import mocker
from utilities.utils_reupload import *


def test_initialize_torrent_data(mocker):
    input = {}
    input["hash"] = "TORRENT_HASH"
    input["name"] = "TORRENT_NAME"
    expected = {}
    expected["hash"] = "TORRENT_HASH"
    expected["name"] = "TORRENT_NAME"
    expected["torrent"] = json.dumps(input)
    expected["status"] = TorrentStatus.PENDING

    mock_cache_client = mocker.patch('modules.cache.Cache')
    init_data = initialize_torrent_data(input, mock_cache_client)

    assert init_data["id"] is not None
    assert init_data["hash"] == expected["hash"]
    assert init_data["name"] == expected["name"]
    assert init_data["status"] == expected["status"]
    assert init_data["torrent"] == expected["torrent"]
    assert init_data["upload_attempt"] == 1
    assert init_data["movie_db"] == "None"
    assert init_data["possible_matches"] == "None"
    assert init_data["date_created"] is not None


@pytest.mark.parametrize(
    ("return_data", "expected"),
    [
        pytest.param(
           None, None, id="status_not_in_cache"
        ),
        pytest.param(
            [{"status": "TORRENT_STATUS"}], "TORRENT_STATUS", id="status_in_cache"
        ),
        pytest.param(
            [], None, id="status_empty_in_cache"
        )
    ]
)
def test_get_torrent_status(return_data, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    assert get_torrent_status("INFO_HASH", mock_cache_client) == expected


@pytest.mark.parametrize(
    ("return_data", "expected"),
    [
        pytest.param(
           None, False, id="nothing_in_cache"
        ),
        pytest.param(
            [{"status": "READY_FOR_PROCESSING"}], False, id="status_is_ready_for_processing"
        ),
        pytest.param(
            [{"status": "PENDING"}], False, id="status_is_ready_for_pending"
        ),
        pytest.param(
            [{"status": "SUCCESS"}], True, id="status_is_ready_for_success"
        ),
        pytest.param(
            [{"status": "FAILED"}], True, id="status_is_ready_for_failed"
        ),
        pytest.param(
            [{"status": "PARTIALLY_SUCCESSFUL"}], True, id="status_is_ready_for_partial_success"
        ),
        pytest.param(
            [{"status": "TMDB_IDENTIFICATION_FAILED"}], True, id="status_is_ready_for_tmdb_failed"
        ),
        pytest.param(
            [{"status": "DUPE_CHECK_FAILED"}], True, id="status_is_ready_for_dupe_check_failed"
        ),
        pytest.param(
            [{"status": "UNKNOWN_FAILURE"}], True, id="status_is_ready_for_unknown_failure"
        ),
        pytest.param(
            [], False, id="empty_status_in_cache"
        )
    ]
)
def test_is_unprocessable_data_present_in_cache(return_data, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    assert is_unprocessable_data_present_in_cache("INFO_HASH", mock_cache_client) == expected
    # TODO: renamed method to start with _

@pytest.mark.parametrize(
    ("torrent", "expected"),
    [
        pytest.param({
            "upload_attempt": 1, "status": "READY_FOR_PROCESSING", "name": "", "hash": ""
        }, False, id="upload_cannot_be_skipped"),
        pytest.param({
            "upload_attempt": 2, "status": "UNKNOWN_FAILURE", "name": "", "hash": ""
        }, False, id="upload_cannot_be_skipped"),
        pytest.param({
            "upload_attempt": 3, "status": "UNKNOWN_FAILURE", "name": "", "hash": ""
        }, True, id="upload_cannot_be_skipped")
    ]
)
def test_should_upload_be_skipped(torrent, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.save", return_value=None)
    assert should_upload_be_skipped(mock_cache_client, torrent) == expected


@pytest.mark.parametrize(
    ("return_data", "expected"),
    [
        pytest.param(None, None, id="no_data_in_cache"),
        pytest.param([], None, id="empty_data_in_cache"),
        pytest.param([{"status": "value"}], {"status": "value"}, id="data_in_cache"),
        pytest.param([{"status": "value"},{"status1": "value1"}], {"status": "value"}, id="multiple_data_in_cache")
    ]
)
def test_get_cached_data(return_data, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    assert get_cached_data("info_hash", mock_cache_client) == expected


@pytest.mark.parametrize(
    ("return_data", "new_status", "expected"),
    [
        pytest.param([{"status": "value"}], "NEW_STATUS", "NEW_STATUS", id="updating_status"),
    ]
)
def test_update_torrent_status(return_data, new_status, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    mocker.patch("modules.cache.Cache.save", return_value=None)
    assert update_torrent_status("info_hash", new_status, mock_cache_client)["status"] == expected


@pytest.mark.parametrize(
    ("new_data", "is_json", "return_data", "expected"),
    [
        pytest.param("NEW_DATA", False, [{"field": "b"}], "NEW_DATA", id="updating_normal_field"),
        pytest.param({"a":"b", "b":"c"}, True, [{"field": "b"}], json.dumps({"a":"b", "b":"c"}), id="updating_json_data"),
        pytest.param(None, True, [{"field": "b"}], None, id="updating_json_none_data"),
    ]
)
def test_update_field(new_data, is_json, return_data, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    mocker.patch("modules.cache.Cache.save", return_value=None)
    assert update_field("info_hash", "field", new_data, is_json, mock_cache_client)["field"] == expected


def test_insert_into_job_repo(mocker):
    data = { "hash" : "hash", "tracker" : "tracker" }
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.save", return_value=None)
    assert insert_into_job_repo(data, mock_cache_client) == data


@pytest.mark.parametrize(
    ("cached_data", "movie_db", "expected"),
    [
        pytest.param(None, None, {}, id="no_movie_db_data"),
        pytest.param(None, [], {}, id="empty_movie_db_data"),
        pytest.param(None, [{"status": "value"}], {"status": "value"}, id="movie_db_in_cache_no_cached_data"),
        pytest.param({}, [{"status": "value"}], {"status": "value"}, id="movie_db_in_cache_cached_data_without_user_choice"),
        pytest.param({"tmdb_user_choice": ""}, [{"status": "value"}], {}, id="movie_db_in_cache_cached_data_wit_user_choice"),
    ]
)
def test_reupload_get_movie_db_from_cache(cached_data, movie_db, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=movie_db)
    assert reupload_get_movie_db_from_cache(mock_cache_client, cached_data, "", "", "") == expected


@pytest.mark.parametrize(
    ("existing_data", "movie_db", "torrent_info", "expected"),
    [
        pytest.param(
            [{"movie_db": ""}], # the existing torrent data from cache
            {}, # this is the moviedb data obtained from `utilities.utils_reupload.reupload_get_movie_db_from_cache`
            { # this is the metadata in torrent_info
                "tmdb": "tmdb",
                "imdb": "imdb",
                "tvmaze": "tvmaze",
                "tvdb": "tvdb",
                "mal": "mal",
                "type": "type"
            }, 
            { # this is the moviedb being saved to cache
                "tmdb": "tmdb",
                "imdb": "imdb",
                "tvmaze": "tvmaze",
                "tvdb": "tvdb",
                "mal": "mal",
                "type": "type",
                "title": "original_title",
                "year": "original_year"
            }, 
            id="no_movie_db_data"
        )
    ]
)
def test_reupload_persist_updated_moviedb_to_cache(existing_data, movie_db, torrent_info, expected, mocker):
    mock_cache_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=existing_data)
    mocker.patch("modules.cache.Cache.save", return_value=None)
    assert reupload_persist_updated_moviedb_to_cache(mock_cache_client, movie_db, torrent_info, "torrent_hash", "original_title", "original_year") == expected