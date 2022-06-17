import os
import shutil
import pytest

from pathlib import Path
from pytest_mock import mocker
from unittest.mock import MagicMock

from utilities.utils import *
from modules.torrent_client import Clients, TorrentClientFactory, TorrentClient


working_folder = Path(__file__).resolve().parent.parent.parent
temp_working_dir = "/tests/working_folder"
temp_upload_dir = "/temp_upload"
rar_file_source = "/tests/resources/rar/data.rar"
rar_file_target = f"{temp_working_dir}/rar/data.rar"


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
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}"
    proper_test_working_folder = f"{working_folder}{temp_upload_dir}"
    # /tests/working_folder

    if Path(folder).is_dir():
        clean_up(folder)
    else:
        Path(f"{folder}/torrent").mkdir(parents=True, exist_ok=True) # torrents folder
        Path(f"{folder}/media").mkdir(parents=True, exist_ok=True) # media folder
        Path(f"{folder}/move/torrent").mkdir(parents=True, exist_ok=True) # media folder
        Path(f"{folder}/move/media").mkdir(parents=True, exist_ok=True) # media folder
        Path(f"{folder}/rar").mkdir(parents=True, exist_ok=True) # rar folder
    
    for dot_torrent in ["test1.torrent", "test2.torrent"]:
        fp = open(f"{folder}/torrent/{dot_torrent}", 'x')
        logging.info(f"Creating file: {folder}/torrent/{dot_torrent}")
        fp.close()
    
    fp = open(f"{folder}/media/file.mkv", 'x')
    logging.info(f"Creating file: {folder}/media/file.mkv")
    fp.close()

    # creating dot torrent files for cross-seeding tests
    if Path(proper_test_working_folder).is_dir():
        clean_up(f"{proper_test_working_folder}/")
    else:
        Path(f"{proper_test_working_folder}/test_working_folder").mkdir(parents=True, exist_ok=True) # test_working_folder folder
    
    fp = open(f'{proper_test_working_folder}/test_working_folder/TRACKER-Some Title different from torrent_title.torrent', 'x')
    fp.close()
    fp = open(f'{proper_test_working_folder}/test_working_folder/TRACKER2-Some Title different from torrent_title.torrent', 'x')
    fp.close()


    shutil.copy(f"{working_folder}{rar_file_source}", f"{working_folder}{rar_file_target}")

    yield

    # clean up. deleting the temp working folder and all its contents
    clean_up(folder)
    clean_up(f"{proper_test_working_folder}/")


def test_get_hash():
    test_string = "ThisIsATestString"
    hashed = hashlib.new('sha256')
    hashed.update(test_string.encode())
    expected = hashed.hexdigest()
    assert get_hash(test_string) == expected


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
        (1073741824, 19), # 1 GB => KiB_512
        (2147483648, 20), # 2 GB => MiB_1
        (3221225472, 21), # 3 GB => MiB_2
        (5368709120, 22), # 5 GB => MiB_4
        (7516192768, 22), # 7 GB => MiB_4
        (10737418240, 23), # 10 GB => MiB_8
        (16106127360, 23), # 15 GB => MiB_8
        (21474836480, 24), # 20 GB => MiB_16
        (32212254720, 24), # 30 GB => MiB_16
        (42949672960, 24), # 40 GB => MiB_16
        (53687091200, 24), # 50 GB => MiB_16
        (64424509440, 24), # 60 GB => MiB_16
        (75161927680, 24), # 70 GB => MiB_16
        (85899345920, 24), # 80 GB => MiB_16
        (96636764160, 24), # 90 GB => MiB_16
        (107374182400, 24), # 100 GB => MiB_16
        (214748364800, 24), # 100 GB => MiB_16
    )
)
def test_get_piece_size_for_mktorrent(input, expected):
    assert get_piece_size_for_mktorrent(input) == expected


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
        (1073741824, 1048576), # 1 GB => MiB_1
        (2147483648, 2097152), # 2 GB => MiB_2
        (3221225472, 4194304), # 3 GB => MiB_4
        (5368709120, 4194304), # 5 GB => MiB_4
        (7516192768, 4194304), # 7 GB => MiB_4
        (10737418240, 8388608), # 10 GB => MiB_8
        (16106127360, 8388608), # 15 GB => MiB_8
        (21474836480, 16777216), # 20 GB => MiB_16
        (32212254720, 16777216), # 30 GB => MiB_16
        (42949672960, 16777216), # 40 GB => MiB_16
        (53687091200, 16777216), # 50 GB => MiB_16
        (64424509440, 16777216), # 60 GB => MiB_16
        (75161927680, 16777216), # 70 GB => MiB_16
        (85899345920, 16777216), # 80 GB => MiB_16
        (96636764160, 16777216), # 90 GB => MiB_16
        (107374182400, 16777216), # 100 GB => MiB_16
        (214748364800, 16777216), # 100 GB => MiB_16
    )
)
def test_calculate_piece_size(input, expected):
    assert calculate_piece_size(input) == expected # 1 GB => 1 MiB


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
    assert has_user_provided_type(input) == expected


# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------ Tests For Cross Seeding -----------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------
"""
    ___________________________________________________________________________________________________________________________

    --------------------------------------------------------- MOVIES ----------------------------------------------------------
    ___________________________________________________________________________________________________________________________
    Input is a file:
    --------------------------------------------
        when uploader is running in bare metal the -p argument could be a relative path or full path (---A--- or ---B--- respectively)
        when uploader is running in docker container, the -p argument will have the full path to the file. (---B---)

        ---A--- TESTED
        Input: files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv
        raw_file_name: Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv
        upload_media: files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv

        ---B---TESTED
        Input: /projects/Python\ Projects/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv
        raw_file_name: Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv
        upload_media: /projects/Python\ Projects/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv


    Input is a folder:
    ---------------------------------------------------
        TESTED

        Input: /projects/Python Projects/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA
        raw_file_name: Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA
        raw_video_file: /projects/Python\ Projects/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv
        upload_media: /projects/Python\ Projects/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/

    ___________________________________________________________________________________________________________________________
    
    --------------------------------------------------------- TV SHOW ---------------------------------------------------------
    ___________________________________________________________________________________________________________________________

"""
def __no_cross_seed_side_effect(param, default):
    return default


def __invalid_processing_mode_side_effect(param, default):
    if param == "enable_post_processing":
        return True
    elif param == "post_processing_mode":
        return "foo_bar"
    return default


def __cross_seed_no_translation_side_effect(param, default):
    if param == "enable_post_processing":
        return True
    elif param == "translation_needed":
        return False
    elif param == "post_processing_mode":
        return "CROSS_SEED"
    else:
        return default


def __cross_seed_with_translation_side_effect(param, default):
    if param in ["enable_post_processing", "translation_needed"]:
        return True
    elif param == "uploader_path":
        return "/gg-bot-upload-assistant/files"
    elif param == "client_path":
        return "/some/folder/accessible/by/client/data"
    elif param == "post_processing_mode":
        return "CROSS_SEED"
    else:
        return default


def __cross_seed_with_translation_side_effect_sad_path(param, default):
    if param in ["enable_post_processing", "translation_needed"]:
        return True
    elif param == "post_processing_mode":
        return "CROSS_SEED"
    else:
        return default


def __mock_upload_torrent(torrent, save_path, use_auto_torrent_management, is_skip_checking):
    return (torrent, save_path, use_auto_torrent_management, is_skip_checking)


def test_invalid_processing_mode(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__invalid_processing_mode_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')

    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == False


def test_no_client_upload(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__no_cross_seed_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')

    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == False


def test_client_upload_movie_folder_with_translation_sad_path(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_with_translation_side_effect_sad_path)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')

    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == False


def test_client_upload_tv_season_with_translation(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES/Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "tv"
    torrent_info["working_folder"] = "test_working_folder/"
    torrent_info["complete_season"] = "1"
    torrent_info["daily_episodes"] = "0"
    torrent_info["individual_episodes"] = "0"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        '/some/folder/accessible/by/client/data/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected


def test_client_upload_tv_episode_with_translation(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES/Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "tv"
    torrent_info["working_folder"] = "test_working_folder/"
    torrent_info["complete_season"] = "0"
    torrent_info["daily_episodes"] = "0"
    torrent_info["individual_episodes"] = "1"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        '/some/folder/accessible/by/client/data/Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected


def test_client_upload_movie_folder_with_translation(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent
    
    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        '/some/folder/accessible/by/client/data/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected


def test_client_upload_movie_folder(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        '/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected
        

def test_client_upload_movie_folder_torrent_upload_failed(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = False
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent
   
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == False


def test_client_upload_movie_file(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        '/gg-bot-upload-assistant/files/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected


def test_client_upload_movie_file_relative(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent', 
        f'{working_folder}/files/',
        False,
        True
    )
    assert perform_post_processing(torrent_info, mock_client, working_folder, tracker) == expected


# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------ Tests For Watch Folder ------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------

def __watch_folder_no_type_side_effect(param, default=None):
    if param =="enable_post_processing":
        return True
    elif param == "translation_needed":
        return False
    elif param == "dot_torrent_move_location":
        return f"{working_folder}{temp_working_dir}/move/torrent"
    elif param == "media_move_location":
        return f"{working_folder}{temp_working_dir}/move/media"
    elif param == "post_processing_mode":
        return "WATCH_FOLDER"
    else:
        return default

# moving media with type based movement
def __watch_folder_media_type_side_effect(param, default=None):
    if param == "dot_torrent_move_location":
        return ""
    else:
        return __watch_folder_type_side_effect(param, default)

# moving media
def __watch_folder_media_no_type_side_effect(param, default=None):
    if param == "dot_torrent_move_location":
        return ""
    else:
        return __watch_folder_no_type_side_effect(param, default)

# moving torrent with type based movement
def __watch_folder_torrent_type_side_effect(param, default=None):
    if param == "media_move_location":
        return ""
    else:
        return __watch_folder_type_side_effect(param, default)

# moving torrent
def __watch_folder_torrent_no_type_side_effect(param, default=None):
    if param == "media_move_location":
        return ""
    else:
        return __watch_folder_no_type_side_effect(param, default)


def __watch_folder_type_side_effect(param, default=None):
    if param =="enable_type_base_move":
        return True
    else:
        return __watch_folder_no_type_side_effect(param, default)

"""
    Cases for WATCH_FOLDER
    1. Move media and torrent
    2. Move media and torrent with type based movement
    3. Move media
    4. Move media with type based movement
    5. Move torrent 
    6. Move torrent with type based movement
"""
# moving torrent and media
def test_watch_folder_torrent_media(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_no_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")

    assert original_media_path.is_file() == False
    assert original_torrent_1_path.is_file() == False
    assert original_torrent_2_path.is_file() == False

    assert moved_media_path.is_file() == True
    assert moved_torrent_1_path.is_file() == True
    assert moved_torrent_2_path.is_file() == True

# moving torrent and media with type based movement
def test_watch_folder_torrent_media_type(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/movie/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/movie/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/movie/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")
    
    assert original_media_path.is_file() == False
    assert original_torrent_1_path.is_file() == False
    assert original_torrent_2_path.is_file() == False

    assert moved_torrent_1_path.is_file() == True
    assert moved_torrent_2_path.is_file() == True
    assert moved_media_path.is_file() == True

# moving torrent
def test_watch_folder_torrent(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_torrent_no_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")

    assert original_media_path.is_file() == True
    assert original_torrent_1_path.is_file() == False
    assert original_torrent_2_path.is_file() == False
 
    assert moved_media_path.is_file() == False
    assert moved_torrent_1_path.is_file() == True
    assert moved_torrent_2_path.is_file() == True

# moving torrent with type based movement
def test_watch_folder_torrent_relative_input_type_happy(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_torrent_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/movie/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/movie/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")

    assert original_media_path.is_file() == True
    assert original_torrent_1_path.is_file() == False
    assert original_torrent_2_path.is_file() == False

    assert moved_media_path.is_file() == False
    assert moved_torrent_1_path.is_file() == True
    assert moved_torrent_2_path.is_file() == True

# moving media
def test_watch_folder_torrent(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_media_no_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")

    assert original_media_path.is_file() == False
    assert original_torrent_1_path.is_file() == True
    assert original_torrent_2_path.is_file() == True
 
    assert moved_media_path.is_file() == True
    assert moved_torrent_1_path.is_file() == False
    assert moved_torrent_2_path.is_file() == False

# moving media with type based movement
def test_watch_folder_torrent_relative_input_type_happy(mocker):
    torrent_info = {}
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "WORKING_FOLDER"
    torrent_info["upload_media"] = "tests/working_folder/media/file.mkv"
    tracker = "TRACKER"

    mocker.patch("os.getenv", side_effect=__watch_folder_media_type_side_effect)
    mocker.patch("glob.glob", return_value=[f"{working_folder}{temp_working_dir}/torrent/test1.torrent", f"{working_folder}{temp_working_dir}/torrent/test2.torrent"])

    perform_post_processing(torrent_info, None, working_folder, tracker)

    moved_media_path = Path(f"{working_folder}{temp_working_dir}/move/media/movie/file.mkv")
    moved_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test1.torrent")
    moved_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/move/torrent/test2.torrent")

    original_media_path = Path(f"{working_folder}{temp_working_dir}/media/file.mkv")
    original_torrent_1_path = Path(f"{working_folder}{temp_working_dir}/torrent/test1.torrent")
    original_torrent_2_path = Path(f"{working_folder}{temp_working_dir}/torrent/test2.torrent")

    assert original_media_path.is_file() == False
    assert original_torrent_1_path.is_file() == True
    assert original_torrent_2_path.is_file() == True

    assert moved_media_path.is_file() == True
    assert moved_torrent_1_path.is_file() == False
    assert moved_torrent_2_path.is_file() == False


def test_check_for_dir_and_extract_rars_file():
    file_path = "tests/working_folder/rar/data.rar"
    assert check_for_dir_and_extract_rars(file_path) == (True, file_path)


def test_check_for_dir_and_extract_rars_non_rar_folder():
    file_path = "tests/working_folder/media/"
    assert check_for_dir_and_extract_rars(file_path) == (True, file_path)


def test_check_for_dir_and_extract_rars_rar_folder():
    file_path = "tests/working_folder/rar/"
    assert check_for_dir_and_extract_rars(file_path) == (True, "tests/working_folder/rar/something.mkv")


def test_check_for_dir_and_extract_rars_no_rar_installed(mocker):
    file_path = "tests/working_folder/rar/"
    mocker.patch('os.path.isfile', return_value=False)
    assert check_for_dir_and_extract_rars(file_path) == (False, file_path)
