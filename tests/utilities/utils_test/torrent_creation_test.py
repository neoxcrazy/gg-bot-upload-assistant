import glob
import pytest

from pathlib import Path
from torf import Torrent
from pytest_mock import mocker

import utilities.utils as utils



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
    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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

    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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

    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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

    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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

    utils.generate_dot_torrent(
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
    utils.generate_dot_torrent(
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