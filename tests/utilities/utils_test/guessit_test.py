import pytest

from pathlib import Path
from pytest_mock import mocker
import utilities.utils as utils


working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"
dummy_for_guessit = "Movie.Name.2017.1080p.BluRay.Remux.AVC.DTS.5.1-RELEASE_GROUP"


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

    Path(f"{folder}/media/{dummy_for_guessit}").mkdir(parents=True, exist_ok=True)  # media guessit folder

    touch(f"{folder}/media/{dummy_for_guessit}/{dummy_for_guessit}.mkv")
    yield
    clean_up(folder)


@pytest.mark.parametrize(
    ("input_path", "expected"),
    [
        pytest.param(f"{working_folder}{temp_working_dir}/media/{dummy_for_guessit}/{dummy_for_guessit}.mkv",
                     {
                         "title": "Movie Name",
                         "year": 2017,
                         "screen_size": "1080p",
                         "source": "Blu-ray",
                         "other": "Remux",
                         "video_codec": "H.264",
                         "video_profile": "Advanced Video Codec High Definition",
                         "audio_codec": "DTS",
                         "audio_channels": "5.1",
                         "release_group": "RELEASE_GROUP",
                         "container": "mkv",
                         "type": "movie"
                     }, id="file_for_guessit"),
        pytest.param(f"{working_folder}{temp_working_dir}/media/{dummy_for_guessit}/",
                     {
                         "title": "Movie Name",
                         "year": 2017,
                         "screen_size": "1080p",
                         "source": "Blu-ray",
                         "other": "Remux",
                         "video_codec": "H.264",
                         "video_profile": "Advanced Video Codec High Definition",
                         "audio_codec": "DTS",
                         "audio_channels": "5.1",
                         "release_group": "RELEASE_GROUP",
                         "type": "movie"
                     }, id="folder_for_guessit"),
    ]
)
def test_perform_guessit_on_filename(input_path, expected):
    guessit_result = utils.perform_guessit_on_filename(input_path)
    for key, value in expected.items():
        assert guessit_result[key] == expected[key]
