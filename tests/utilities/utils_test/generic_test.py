import pytest
from pathlib import Path
from pytest_mock import mocker
import utilities.utils as utils

working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    """
        Folder struture that will be created for each tests
        ----------------------------------------------------------------------
        tests/
            - working_folder/
                - resources/
                - rar/
                - torrent/
                    - test1.torrent
                    - test2.torrent
                - media/
                    - file.mkv
                    - Movie.Name.2017.1080p.BluRay.Remux.AVC.DTS.5.1-RELEASE_GROUP
                        - Movie.Name.2017.1080p.BluRay.Remux.AVC.DTS.5.1-RELEASE_GROUP.mkv
                - move/
                    - torrent/
                    - media/
                - sample/
                    - config.env.sample
                - temp_upload/
                    - test_working_folder/
                        - TRACKER-Some Title different from torrent_title.torrent
                        - TRACKER2-Some Title different from torrent_title.torrent
                    - test_working_folder_2/
                        - torrent1.torrent
                        - torrent2.torrent
                        - screenshots/
                            - image1.png
                            - image2.png
        ----------------------------------------------------------------------
    """
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/temp_upload/{utils.get_hash('some_name')}/screenshots").mkdir(parents=True, exist_ok=True)  # temp_upload folder
    Path(f"{folder}/nothing").mkdir(parents=True, exist_ok=True)  # temp_upload folder

    # creating some random files inside `/tests/working_folder/temp_upload`
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/torrent1.torrent')
    touch(f'{folder}/temp_upload/torrent1.torrent')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/torrent2.torrent')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/screenshots/image1.png')
    touch(f'{folder}/temp_upload/{utils.get_hash("some_name")}/screenshots/image2.png')

    yield
    clean_up(folder)


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


def test_delete_leftover_humanreadable_files(mocker):
    mocker.patch("os.getenv", return_value=True)
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="/somepath/some more/This is: some ra'ndom.files.thing-WHO",
        resume=False
    )
    human_readable_folder = "This.is..some.random.files.thing-WHO"
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{human_readable_folder}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{human_readable_folder}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{human_readable_folder}/screenshots/").is_dir() == True


def test_delete_leftover_humanreadable_files_disabled(mocker):
    mocker.patch("os.getenv", return_value=False)
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="/somepath/some more/This is: some ra'ndom.files.thing-WHO",
        resume=False
    )
    new_hash = utils.get_hash("/somepath/some more/This is: some ra'ndom.files.thing-WHO")
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{new_hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{new_hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{new_hash}/screenshots/").is_dir() == True


def test_delete_leftover_files():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="some_name1",
        resume=False
    )
    hash = utils.get_hash("some_name1")
    old_hash = utils.get_hash("some_name")
    # check whether the hash folder has been created or not
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True


def test_retain_leftover_files_for_resume():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}",
        file="some_name1",
        resume=True
    )
    hash = utils.get_hash("some_name1")
    old_hash = utils.get_hash("some_name")
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True


def test_create_temp_upload_itself():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}/nothing",
        file="some_name1",
        resume=True
    )
    hash = utils.get_hash("some_name1")
    assert computed_working_folder == f"{hash}/"
    assert Path(f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}").is_dir() == True
    assert Path(f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}/screenshots/").is_dir() == True


@pytest.mark.parametrize(
    ("torrent_info", "expected"),
    [
        pytest.param(
            { "release_group" : "RELEASE_GROUP", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC-RELEASE_GROUP.mkv" },
            "RELEASE_GROUP",
            id="proper_release_group_from_guessit"
        ),
        pytest.param(
            { "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="no_release_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="empty_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "X-RELEASE_GROUP", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL 7.1 Atmos DV HDR HEV DTS-X-RELEASE_GROUP.mkv" },
            "RELEASE_GROUP",
            id="dts-x-wrong_group_from_guessit"
        ),
        pytest.param(
            { "release_group" : "DV", "upload_media" : "/data/Movies/Name of the Movie 2022 STREAM WEB-DL DD+ 5.1 Atmos DV HDR HEVC.mkv" },
            "NOGROUP",
            id="group_from_guessit_when_no_group"
        ),
    ]
)
def test_sanitize_release_group_from_guessit(torrent_info, expected):
    assert utils.sanitize_release_group_from_guessit(torrent_info) == expected