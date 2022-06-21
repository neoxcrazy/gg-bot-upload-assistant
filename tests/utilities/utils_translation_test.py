import json
import pytest

from pathlib import Path

import utilities.utils_translation as translation


working_folder = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope='class')
def load_config():
    yield json.load(open(f"{working_folder}/tests/resources/hybrid_mapping/hybrid_mapping.json"))


# resolution            source              type
# ----------------------------------------------------
# 1  => 2160p       1 => full disc      7  => movie
# 2  => 1080p       2 => remux          12 => complete_season
# 3  => 1080i       3 => encode         10 => individual_episodes
# 5  => 720p        4 => wedl
# 6  => 576p        5 => webrip
# 7  => 576i        6 => hdtv
# 8  => 480p
# 9  => 480i
# 10 => other
# 11 => 4360p
@pytest.mark.parametrize(
    ("tracker_settings", "torrent_info", "expected"),
    [
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2",
                "cat" : "7"
            },
            {
                "video_codec" : "H.264",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "1",
            id="Movies_encode_x264"
        ),
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2",
                "cat" : "7"
            },
            {
                "video_codec" : "H.265",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "43",
            id="Movies_encode_HEVC"
        ),
        pytest.param(
            {
                "source" : "6",
                "resolution" : "1",
                "cat" : "10"
            },
            {
                "video_codec" : "H.265",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "7",
            id="TV_Single_Episode_HDTV"
        ),
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2",
                "cat" : "7"
            },
            {
                "video_codec" : None,
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "HYBRID_MAPPING_INVALID_CONFIGURATION",
            id="invalid_config"
        ),
        pytest.param(
            {
                "source" : "5",
                "resolution" : "2",
                "cat" : ""
            },
            {
                "video_codec" : None,
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "5",
            id="empty_values_defaulting"
        ),
        pytest.param(
            {
                "source" : "100",
                "resolution" : "2",
                "cat" : "2"
            },
            {
                "video_codec" : None,
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            "100",
            id="rule_order_testing_first"
        ),
        pytest.param(
            {
                "source" : "100",
                "resolution" : "2",
                "cat" : "2"
            },
            {
                "video_codec" : None,
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "2"
            },
            "101",
            id="rule_order_testing_second"
        ),
        pytest.param(
            {
                "source" : "100",
                "resolution" : "2",
                "cat" : "2"
            },
            {
                "video_codec" : None,
                "mal": "200",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "2"
            },
            "anime",
            id="is_not_none_or_is_present"
        )
    ]
)
@pytest.mark.usefixtures("load_config")
def test_get_hybrid_type(load_config, tracker_settings, torrent_info, expected):
    hybrid_type = translation.get_hybrid_type("hybrid_type", tracker_settings, load_config, False, torrent_info)
    assert hybrid_type == expected


@pytest.mark.parametrize(
    ("tracker_settings", "torrent_info"),
    [
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2",
                "cat" : "7"
            },
            {
                "video_codec" : None,
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0"
            },
            id="invalid_config_program_exit")
    ]
)
@pytest.mark.usefixtures("load_config")
def test_get_hybrid_type_application_exit(load_config, tracker_settings, torrent_info):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
            translation.get_hybrid_type("hybrid_type", tracker_settings, load_config, True, torrent_info)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == "Invalid hybrid mapping configuration provided."