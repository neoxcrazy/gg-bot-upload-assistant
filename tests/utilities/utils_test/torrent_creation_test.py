import glob
import pytest

from pathlib import Path
from torf import Torrent
from pytest_mock import mocker

import utilities.utils as utils
import utilities.utils_torrent as torrent_utilities



working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"
data_dir = "/tests/media"


@pytest.fixture(scope="class", autouse=True)
def create_file_for_torrent_creation():
    # temp working folder inside tests
    folder = f"{working_folder}{data_dir}" # this will be the working folder sent to code

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/file1").mkdir(parents=True, exist_ok=True)

    with open(f"{folder}/file1/file1.dat", 'wb') as f:
        num_chars = 1024 * 1024 # 1MB file for quicker tests execution
        f.write(str.encode("GG-BOT") * num_chars)
    yield
    clean_up(folder)


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}" # this will be the working folder sent to code

    if Path(folder).is_dir():
        clean_up(folder)
    else:
        Path(f"{folder}/temp_upload/{utils.get_hash('GenerateTorrentTesting')}").mkdir(parents=True, exist_ok=True)  # temp_upload folder

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


def test_folder_torrent_creation_pytorf():
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_folder_torrent_creation_mktorrent():
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=True,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_single_file_torrent_creation_pytorf():
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_single_file_torrent_creation_mktorrent():
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=True,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_single_file_torrent_creation_pytorf_multiple_announce():
    announce_list = ["https://gg-bot.com/announce/commence/1", "https://gg-bot.com/announce/commence/2", "https://gg-bot.com/announce/commence/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_single_file_torrent_creation_mktorrent_multiple_announce():
    announce_list = ["https://gg-bot.com/announce/commence/1", "https://gg-bot.com/announce/commence/2", "https://gg-bot.com/announce/commence/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=True,
        tracker="GG-BOT",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT'


def test_existing_torrent_modification_single_announce():
    test_single_file_torrent_creation_pytorf()

    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_single_announce_torrent_modification_multiple_announce():
    test_single_file_torrent_creation_pytorf()

    announce_list = ["https://gg-bot.com/announce/edited/1", "https://gg-bot.com/announce/edited/2", "https://gg-bot.com/announce/edited/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_multiple_announce_torrent_modification_single_announce():
    test_single_file_torrent_creation_pytorf_multiple_announce()

    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_multiple_announce_torrent_modification_multiple_announce():
    test_single_file_torrent_creation_pytorf_multiple_announce()

    announce_list = ["https://gg-bot.com/announce/edited/1", "https://gg-bot.com/announce/edited/2", "https://gg-bot.com/announce/edited/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_mktorrent_modification_single_announce():
    test_single_file_torrent_creation_mktorrent()

    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_single_announce_mktorrent_modification_multiple_announce():
    test_single_file_torrent_creation_mktorrent()

    announce_list = ["https://gg-bot.com/announce/edited/1", "https://gg-bot.com/announce/edited/2", "https://gg-bot.com/announce/edited/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_multiple_announce_mktorrent_modification_single_announce():
    test_single_file_torrent_creation_mktorrent_multiple_announce()

    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = ["https://gg-bot.com/announce/commence/testing"],
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == 'https://gg-bot.com/announce/commence/testing'
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'


def test_existing_multiple_announce_mktorrent_modification_multiple_announce():
    test_single_file_torrent_creation_mktorrent_multiple_announce()

    announce_list = ["https://gg-bot.com/announce/edited/1", "https://gg-bot.com/announce/edited/2", "https://gg-bot.com/announce/edited/3"]
    torrent_utilities.generate_dot_torrent(
        media = f'{working_folder}{data_dir}/file1/file1.dat',
        announce = announce_list,
        source = "GG-BOT-SECOND-SOURCE",
        working_folder=f"{working_folder}{temp_working_dir}",
        use_mktorrent=False,
        tracker="GG-BOT-TRACKER-TWO",
        torrent_title="This.Is.The.Title.Of.The.Torrent",
        hash_prefix=f"{utils.get_hash('GenerateTorrentTesting')}/"
    )
    # check whether the .torrent file has been created
    expected_torrent_title = f'{working_folder}{temp_working_dir}/temp_upload/{utils.get_hash("GenerateTorrentTesting")}/GG-BOT-TRACKER-TWO-This.Is.The.Title.Of.The.Torrent.torrent'
    assert Path(expected_torrent_title).is_file() == True

    created_torrent = Torrent.read(glob.glob(expected_torrent_title)[0])
    assert created_torrent.comment == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.created_by == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['announce'] == announce_list[0]
    assert len(created_torrent.metainfo['announce-list']) == len(announce_list)
    assert created_torrent.metainfo['announce-list'][0] == [announce_list[0]]
    assert created_torrent.metainfo['announce-list'][1] == [announce_list[1]]
    assert created_torrent.metainfo['announce-list'][2] == [announce_list[2]]
    assert created_torrent.metainfo['comment'] == 'Torrent created by GG-Bot Upload Assistant'
    assert created_torrent.metainfo['created by'] == 'GG-Bot Upload Assistant'
    assert created_torrent.metainfo['info']['private'] == True
    assert created_torrent.metainfo['info']['source'] == 'GG-BOT-SECOND-SOURCE'



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
    assert torrent_utilities.get_piece_size_for_mktorrent(input) == expected


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
        (75161927680, 33554432),  # 70 GB => MiB_32
        (85899345920, 33554432),  # 80 GB => MiB_32
        (96636764160, 33554432),  # 90 GB => MiB_32
        (107374182400, 33554432),  # 100 GB => MiB_32
        (214748364800, 33554432),  # 100 GB => MiB_32

    )
)
def test_calculate_piece_size(input, expected):
    assert torrent_utilities.calculate_piece_size(input) == expected  # 1 GB => 1 MiB

