import pytest
from pathlib import Path
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
    else:
        Path(f"{folder}/temp_upload/{utils.get_hash('some_name')}/screenshots").mkdir(
            parents=True, exist_ok=True)  # temp_upload folder
        Path(f"{folder}/nothing").mkdir(parents=True,
                                        exist_ok=True)  # temp_upload folder

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
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == False
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True
    assert computed_working_folder == f"{hash}/"


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
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{hash}").is_dir() == True
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{old_hash}").is_dir() == True
    assert Path(
        f"{working_folder}{temp_working_dir}/temp_upload/{hash}/screenshots/").is_dir() == True
    assert computed_working_folder == f"{hash}/"


def test_create_temp_upload_itself():
    # here we'll be working with /tests/working_folder/temp_upload/
    # this will be the folder that the actual code will be dealing with
    computed_working_folder = utils.delete_leftover_files(
        working_folder=f"{working_folder}{temp_working_dir}/nothing",
        file="some_name1",
        resume=True
    )
    hash = utils.get_hash("some_name1")
    assert Path(
        f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}").is_dir() == True
    assert Path(
        f"{working_folder}{temp_working_dir}/nothing/temp_upload/{hash}/screenshots/").is_dir() == True
    assert computed_working_folder == f"{hash}/"
