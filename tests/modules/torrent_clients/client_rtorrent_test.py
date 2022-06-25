import pytest
from pytest_mock import mocker

from modules.torrent_clients.client_rtorrent import Rutorrent


def __reuploader_default_mode(param, default=None):
    if param == "reupload_label":
        return "GG_BOT_TEST_LABEL"
    if param == "cross_seed_label":
        return "GG_BOT_CROSS_SEED_TEST"
    if param == "client_host":
        return "localhost"
    return default

def __reuploader_dynamic_mode(param, default=None):
    if param == "dynamic_tracker_selection":
        return True
    if param == "reupload_label":
        return "GG_BOT_TEST_LABEL"
    if param == "cross_seed_label":
        return "GG_BOT_CROSS_SEED_TEST"
    if param == "client_host":
        return "localhost"
    return default


def test_init_rutorrent(mocker):
    mock_api_call = mocker.patch("requests.post")
    mocker.patch("os.getenv", side_effect=__reuploader_default_mode)
    rutorrent = Rutorrent()

    assert rutorrent.dynamic_tracker_selection == False
    assert rutorrent.target_label == "GG_BOT_TEST_LABEL"
    assert rutorrent.seed_label == "GG_BOT_CROSS_SEED_TEST"
    assert rutorrent.source_label == "GG_BOT_CROSS_SEED_TEST_Source"


def test_init_rutorrent_dynamic_reuploader(mocker):
    mock_api_call = mocker.patch("requests.post")
    mocker.patch("os.getenv", side_effect=__reuploader_dynamic_mode)
    rutorrent = Rutorrent()

    assert rutorrent.dynamic_tracker_selection == True
    assert rutorrent.target_label == "GGBOT"
    assert rutorrent.seed_label == "GG_BOT_CROSS_SEED_TEST"
    assert rutorrent.source_label == "GG_BOT_CROSS_SEED_TEST_Source"


@pytest.mark.parametrize(
    ("torrent", "expected"),
    [
        pytest.param({"category": "GGBOT"}, [], id="no_trackers_provided"),
        pytest.param({"category": "GGBOT::"}, [], id="no_trackers_provided"),
        pytest.param({"category": "SomeOtherLabel"}, [], id="wrong_label"),
        pytest.param({"category": ""}, [], id="no_label"),
        pytest.param({"category": "GGBOT::TSP::ATH"}, ["TSP", "ATH"], id="two_trackers_provided"),
        pytest.param({"category": "GGBOT::TSP::ATH::"}, ["TSP", "ATH"], id="two_trackers_provided"),
        pytest.param({"category": "GGBOT::spd::ath::"}, ["spd", "ath"], id="two_trackers_provided"),
    ]
)
def test_get_dynamic_trackers(torrent, expected, mocker):
    mock_api_call = mocker.patch("requests.post")
    mocker.patch("os.getenv", side_effect=__reuploader_dynamic_mode)
    rutorrent = Rutorrent()
    assert rutorrent.get_dynamic_trackers(torrent) == expected

@pytest.mark.parametrize(
    ("torrent", "expected"),
    [
        pytest.param({"category": "GGBOT"}, [], id="no_trackers_provided"),
        pytest.param({"category": "SomeOtherLabel"}, [], id="wrong_label"),
        pytest.param({"category": ""}, [], id="no_label"),
        pytest.param({"category": "GGBOT::"}, [], id="no_trackers_provided"),
        pytest.param({"category": "GGBOT::TSP::ATH"}, [], id="two_trackers_provided"),
        pytest.param({"category": "GGBOT::TSP::ATH::"}, [], id="two_trackers_provided"),
        pytest.param({"category": "GGBOT::spd::ath::"}, [], id="two_trackers_provided"),
    ]
)
def test_get_dynamic_trackers_when_disabled(torrent, expected, mocker):
    mock_api_call = mocker.patch("requests.post")
    mocker.patch("os.getenv", side_effect=__reuploader_default_mode)
    rutorrent = Rutorrent()
    assert rutorrent.get_dynamic_trackers(torrent) == expected