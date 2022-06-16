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

    mock_client = mocker.patch('modules.cache.Cache')
    init_data = initialize_torrent_data(input, mock_client)

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
    mock_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    assert get_torrent_status("INFO_HASH", mock_client) == expected


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
    mock_client = mocker.patch('modules.cache.Cache')
    mocker.patch("modules.cache.Cache.get", return_value=return_data)
    assert is_unprocessable_data_present_in_cache("INFO_HASH", mock_client) == expected