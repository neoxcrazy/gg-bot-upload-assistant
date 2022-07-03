import json
import pytest
import hashlib

from pathlib import Path
from pytest_mock import mocker
import utilities.utils as utils


working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"


def nano(file_path, data):
    fp = open(file_path, 'w')
    fp.write(data)
    fp.close()


def touch(file_path):
    fp = open(file_path, 'x')
    fp.close()


def clean_up(pth):
    pth = Path(pth)
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            clean_up(child)
    pth.rmdir()


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/sample").mkdir(parents=True, exist_ok=True)  # config.env folder

    nano(f"{folder}/sample/config.env.sample", "key1=\nkey2=\nkey3=")
    yield
    clean_up(folder)


def test_write_file_contents_to_log_as_debug(mocker):
    mock_logger = mocker.patch("logging.debug")
    utils.write_file_contents_to_log_as_debug(f"{working_folder}{temp_working_dir}/sample/config.env.sample")
    assert mock_logger.call_count == 3


def test_validate_env_file(mocker):
    get_env = mocker.patch("os.getenv", return_value="")
    utils.validate_env_file(f"{working_folder}{temp_working_dir}/sample/config.env.sample")
    assert get_env.call_count == 3


def test_get_and_validate_default_trackers(mocker):
    mocker.patch("os.getenv", side_effect=__default_tracker_success_key_validation)

    acronym_to_tracker = json.load(open(f'{working_folder}/parameters/tracker/acronyms.json'))
    api_keys_dict = utils.prepare_and_validate_tracker_api_keys_dict(f'{working_folder}/parameters/tracker/api_keys.json')
    assert utils.get_and_validate_configured_trackers(None, False, api_keys_dict, acronym_to_tracker.keys()) == ["ANT"]


@pytest.mark.parametrize(
    ("trackers", "all_trackers"),
    [
        pytest.param(["TSP", "BHD", "ABC"], True, id="trackers_provided_with_no_api_key"),
        pytest.param([], False, id="default_trackers_with_no_api_key"),
    ]
)
def test_get_and_validate_configured_trackers_failures(trackers, all_trackers, mocker):
    mocker.patch("os.getenv", side_effect=__default_tracker_failure_key_validation)

    acronym_to_tracker = json.load(open(f'{working_folder}/parameters/tracker/acronyms.json'))
    api_keys_dict = utils.prepare_and_validate_tracker_api_keys_dict(
        f'{working_folder}/parameters/tracker/api_keys.json')

    with pytest.raises(AssertionError):
        assert utils.get_and_validate_configured_trackers(
            trackers, all_trackers, api_keys_dict, acronym_to_tracker.keys())


def __tracker_key_validation(param, default=None):
    if param == "ANT_API_KEY":
        return "ant_api_key_value"
    elif param == "ATH_API_KEY":
        return "ath_api_key_value"
    elif param == "TMDB_API_KEY":
        return "tmdb_api_key_value"
    return ""


def test_prepare_and_validate_tracker_api_keys_dict(mocker):
    mocker.patch("os.getenv", side_effect=__tracker_key_validation)

    expected = dict()
    api_keys = json.load(
        open(f'{working_folder}/parameters/tracker/api_keys.json'))
    for i in range(0, len(api_keys)):
        expected[api_keys[i]] = ""
    expected["ant_api_key"] = "ant_api_key_value"
    expected["ath_api_key"] = "ath_api_key_value"
    expected["tmdb_api_key"] = "tmdb_api_key_value"

    assert utils.prepare_and_validate_tracker_api_keys_dict(
        f'{working_folder}/parameters/tracker/api_keys.json') == expected


def test_validate_tracker_api_keys_no_tmdb(mocker):
    mocker.patch("os.getenv", return_value="")

    with pytest.raises(AssertionError):
        assert utils.prepare_and_validate_tracker_api_keys_dict(
            f'{working_folder}/parameters/tracker/api_keys.json')


# highest priority is given to -t arguments, then --all_trackers then default_trackers from config file
@pytest.mark.parametrize(
    ("trackers", "all_trackers", "expected"),
    [
        pytest.param([], True, ["ANT", "ATH"], id="uploading_to_all_trackers"),
        pytest.param(None, True, ["ANT", "ATH"],
                     id="uploading_to_all_trackers"),
        pytest.param(["NBL", "ATH", "TSP"], True, ["ATH"],
                     id="uploading_to_selected_trackers"),
        pytest.param(["NBL", "ATH", "TSP"], False, ["ATH"],
                     id="uploading_to_selected_trackers")
    ]
)
def test_get_and_validate_configured_trackers(trackers, all_trackers, expected, mocker):
    mocker.patch("os.getenv", side_effect=__tracker_key_validation)

    acronym_to_tracker = json.load(
        open(f'{working_folder}/parameters/tracker/acronyms.json'))
    api_keys_dict = utils.prepare_and_validate_tracker_api_keys_dict(
        f'{working_folder}/parameters/tracker/api_keys.json')

    assert utils.get_and_validate_configured_trackers(
        trackers, all_trackers, api_keys_dict, acronym_to_tracker.keys()) == expected


def test_display_banner(mocker):
    mock_console = mocker.patch('rich.console.Console.print')
    utils.display_banner("GG-BOT-Testing")
    assert mock_console.call_count == 2


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        pytest.param([None], False, id="no_type_provided"),
        pytest.param(["tv"], True, id="tv_type_provided"),
        pytest.param(["movie"], True, id="movie_type_provided"),
        pytest.param(["hello"], False, id="invalid_type_provided"),
        pytest.param(None, False, id="no_inputs"),
    )
)
def test_has_user_provided_type(input, expected):
    assert utils.has_user_provided_type(input) == expected


def test_get_hash():
    test_string = "ThisIsATestString"
    hashed = hashlib.new('sha256')
    hashed.update(test_string.encode())
    expected = hashed.hexdigest()
    assert utils.get_hash(test_string) == expected


"""
    KiB_512 = 19
    MiB_1 = 20
    MiB_2 = 21
    MiB_4 = 22
    MiB_8 = 23
    MiB_16 = 24
    MiB_32 = 25
"""


@pytest.mark.parametrize(
    ('input', 'expected'),
    (
        (1073741824, 19),  # 1 GB => KiB_512
        (2147483648, 20),  # 2 GB => MiB_1
        (3221225472, 21),  # 3 GB => MiB_2
        (5368709120, 22),  # 5 GB => MiB_4
        (7516192768, 22),  # 7 GB => MiB_4
        (10737418240, 23),  # 10 GB => MiB_8
        (16106127360, 23),  # 15 GB => MiB_8
        (21474836480, 24),  # 20 GB => MiB_16
        (32212254720, 24),  # 30 GB => MiB_16
        (42949672960, 24),  # 40 GB => MiB_16
        (53687091200, 24),  # 50 GB => MiB_16
        (64424509440, 24),  # 60 GB => MiB_32
        (75161927680, 25),  # 70 GB => MiB_32
        (85899345920, 25),  # 80 GB => MiB_32
        (96636764160, 25),  # 90 GB => MiB_32
        (107374182400, 25),  # 100 GB => MiB_32
        (214748364800, 25),  # 100 GB => MiB_32
    )
)
def test_get_piece_size_for_mktorrent(input, expected):
    assert utils.get_piece_size_for_mktorrent(input) == expected


"""
    MiB_1 = 1048576
    MiB_2 = 2097152
    Mib_4 = 4194304
    Mib_8 = 8388608
    Mib_16 = 16777216
"""


@pytest.mark.parametrize(
    ('input', 'expected'),
    (
        # pytest.param(1, 1, id='test name')
        (1073741824, 1048576),  # 1 GB => MiB_1
        (2147483648, 2097152),  # 2 GB => MiB_2
        (3221225472, 4194304),  # 3 GB => MiB_4
        (5368709120, 4194304),  # 5 GB => MiB_4
        (7516192768, 4194304),  # 7 GB => MiB_4
        (10737418240, 8388608),  # 10 GB => MiB_8
        (16106127360, 8388608),  # 15 GB => MiB_8
        (21474836480, 16777216),  # 20 GB => MiB_16
        (32212254720, 16777216),  # 30 GB => MiB_16
        (42949672960, 16777216),  # 40 GB => MiB_16
        (53687091200, 16777216),  # 50 GB => MiB_16
        (64424509440, 16777216),  # 60 GB => MiB_16
        (75161927680, 16777216),  # 70 GB => MiB_16
        (85899345920, 16777216),  # 80 GB => MiB_16
        (96636764160, 16777216),  # 90 GB => MiB_16
        (107374182400, 16777216),  # 100 GB => MiB_16
        (214748364800, 16777216),  # 100 GB => MiB_16

    )
)
def test_calculate_piece_size(input, expected):
    assert utils.calculate_piece_size(input) == expected  # 1 GB => 1 MiB


def __default_tracker_failure_key_validation(param, default=None):
    if param == "ANT_API_KEY":
        return "ant_api_key_value"
    elif param == "ATH_API_KEY":
        return "ath_api_key_value"
    elif param == "default_trackers_list":
        return "NBL,STC"
    elif param == "TMDB_API_KEY":
        return "tmdb_api_key_value"
    return ""


def __default_tracker_success_key_validation(param, default=None):
    if param == "ANT_API_KEY":
        return "ant_api_key_value"
    elif param == "ATH_API_KEY":
        return "ath_api_key_value"
    elif param == "default_trackers_list":
        return "NBL,STC,ANT"
    elif param == "TMDB_API_KEY":
        return "tmdb_api_key_value"
    return ""
