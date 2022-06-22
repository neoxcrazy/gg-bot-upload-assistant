import json
import pytest

from pathlib import Path

import utilities.utils_translation as translation


working_folder = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope='class')
def load_config():
    yield json.load(open(f"{working_folder}/tests/resources/translations/hybrid_mapping.json"))

@pytest.fixture(scope='class')
def load_multiple_mapping_config():
    yield json.load(open(f"{working_folder}/tests/resources/translations/multiple_hybrid_mapping.json"))

@pytest.fixture(scope='class')
def full_tracker_config():
    yield json.load(open(f"{working_folder}/tests/resources/translations/translation_tests/full_tracker_config.json"))


class Args:
    anon = None
    disc = None

    def __init__(self):
        self.anon = False
        self.disc = False


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
    assert translation.__get_hybrid_type("subcat", tracker_settings, load_config, False, torrent_info) == expected


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
            translation.__get_hybrid_type("subcat", tracker_settings, load_config, True, torrent_info)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == "Invalid hybrid mapping configuration provided."


@pytest.mark.parametrize(
    ("tracker_settings","expected"),
    [
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2",
                "cat" : "7"
            },
            False,
            id="no_need_to_delay"
        ),
        pytest.param(
            {
                "source" : "3",
                "cat" : "7"
            },
            False,
            id="no_need_to_delay"
        ),
        pytest.param(
            {
                "source" : "3",
                "resolution" : "2"
            },
            True,
            id="delay_hybrid_mapping_after_all_translations"
        )
    ]
)
@pytest.mark.usefixtures("load_config")
def test_should_delay_mapping(load_config, tracker_settings, expected):
    assert translation.should_delay_mapping("subcat", load_config["hybrid_mappings"]["subcat"]["prerequisite"],tracker_settings) == expected


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
def test_perform_delayed_hybrid_mapping(load_config, tracker_settings, torrent_info, expected):
    translation.perform_delayed_hybrid_mapping(load_config, tracker_settings, torrent_info, False)
    assert tracker_settings["subcat"] == expected


@pytest.mark.parametrize(
    ("tracker_settings", "torrent_info", "subcat_1", "subcat_2", "subcat_3", "subcat_4", "subcat_5"),
    [
        pytest.param(
            {
                "source" : "3",
                "cat" : "2"
            },
            {
                "video_codec" : "H.264",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "1"
            },
            "HYBRID_MAPPING_INVALID_CONFIGURATION",
            "subcat_2_digits",
            "subcat_3_digits",
            "subcat_4_three_digit",
            "101",
            id="delayed_multiple_mapping"
        ),
        pytest.param(
            {
                "source" : "3",
                "cat" : "2"
            },
            {
                "video_codec" : "H.264",
                "source": "SOURCE_FOR_LOGGING",
                "screen_size": "SCREEN_SIZE_FOR_LOGGING",
                "episode_number": "0",
                "mal":"100"
            },
            "subcat_1_mapping",
            "subcat_2_anime",
            "subcat_3_anime",
            "subcat_4_anime",
            "anime",
            id="delayed_multiple_mapping"
        )
    ]
)
@pytest.mark.usefixtures("load_multiple_mapping_config")
def test_perform_delayed_hybrid_mapping_multiple_mappings(
    load_multiple_mapping_config, tracker_settings, torrent_info, subcat_1, subcat_2, subcat_3, subcat_4, subcat_5
):
    translation.perform_delayed_hybrid_mapping(load_multiple_mapping_config, tracker_settings, torrent_info, False)
    assert tracker_settings["subcat_1"] == subcat_1
    assert tracker_settings["subcat_2"] == subcat_2
    assert tracker_settings["subcat_3"] == subcat_3
    assert tracker_settings["subcat_4"] == subcat_4
    assert tracker_settings["subcat_5"] == subcat_5


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    [
        pytest.param(
            json.load(open(f"{working_folder}/tests/resources/translations/translation_tests/1/torrent_info.json")),
            json.load(open(f"{working_folder}/tests/resources/translations/translation_tests/1/tracker_settings.json")),
            id="torrent_info_1"
        ),
        pytest.param(
            json.load(open(f"{working_folder}/tests/resources/translations/translation_tests/2/torrent_info.json")),
            json.load(open(f"{working_folder}/tests/resources/translations/translation_tests/2/tracker_settings.json")),
            id="torrent_info_2"
        )
    ]
)
@pytest.mark.usefixtures("full_tracker_config")
def test_choose_right_tracker_keys(full_tracker_config, torrent_info, expected):
    args = Args()
    tracker_settings = {}
    translation.choose_right_tracker_keys(full_tracker_config, tracker_settings, "GG-BOT", torrent_info, args, working_folder)

    for key in tracker_settings.keys() if len(tracker_settings) > len(expected) else expected.keys():
        if key == "file":
            assert tracker_settings[key].endswith(expected[key])
        else:
            assert tracker_settings[key] == expected[key]
    assert len(tracker_settings) == len(expected)