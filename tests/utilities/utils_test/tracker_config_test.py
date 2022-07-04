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
