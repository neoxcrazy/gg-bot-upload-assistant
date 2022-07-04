import pytest

from pathlib import Path
from pytest_mock import mocker
import utilities.utils as utils


working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"


@pytest.fixture(scope="function", autouse=True)
def run_around_tests():
    # temp working folder inside tests
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)

    Path(f"{folder}/temp_upload/test_working_folder").mkdir(parents=True, exist_ok=True)  # temp_upload folder

    # created torrents for cross-seeding tests
    touch(f'{folder}/temp_upload/test_working_folder/TRACKER-Some Title different from torrent_title.torrent')
    touch(f'{folder}/temp_upload/test_working_folder/TRACKER2-Some Title different from torrent_title.torrent')
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
    elif param == "uploader_accessible_path":
        return "/gg-bot-upload-assistant/files"
    elif param == "client_accessible_path":
        return "/some/folder/accessible/by/client/data"
    elif param == "post_processing_mode":
        return "CROSS_SEED"
    else:
        return default


def __mock_upload_torrent(torrent, save_path, use_auto_torrent_management, is_skip_checking):
    return (torrent, save_path, use_auto_torrent_management, is_skip_checking)


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

    mocker.patch(
        "os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/some/folder/accessible/by/client/data/',
        False,
        True
    )
    assert utils.perform_post_processing(
        torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected


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

    mocker.patch(
        "os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/some/folder/accessible/by/client/data/Arcane.S01.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES/',
        False,
        True
    )
    assert utils.perform_post_processing(
        torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected


def test_client_upload_movie_folder_with_translation(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch(
        "os.getenv", side_effect=__cross_seed_with_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/some/folder/accessible/by/client/data/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/',
        False,
        True
    )
    assert utils.perform_post_processing(
        torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected


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
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/',
        False,
        True
    )
    assert utils.perform_post_processing(torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected


def test_client_upload_movie_folder_allow_multiple_files(mocker):
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
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/gg-bot-upload-assistant/files/',
        False,
        True
    )
    assert utils.perform_post_processing(torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker, True) == expected


def test_client_upload_movie_folder_torrent_upload_failed(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA"
    torrent_info["raw_video_file"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA/"
    torrent_info[f"TRACKER_upload_status"] = False
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch(
        "os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    assert utils.perform_post_processing(
        torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == False


def test_client_upload_movie_file(mocker):
    torrent_info = {}
    torrent_info["raw_file_name"] = "Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info["upload_media"] = "/gg-bot-upload-assistant/files/Varathan.2018.1080p.Blu-ray.Remux.AVC.DTS-HD.MA.5.1-FAFDA.mkv"
    torrent_info[f"TRACKER_upload_status"] = True
    torrent_info["type"] = "movie"
    torrent_info["working_folder"] = "test_working_folder/"
    tracker = "TRACKER"

    mocker.patch(
        "os.getenv", side_effect=__cross_seed_no_translation_side_effect)
    mock_client = mocker.patch('modules.torrent_client.TorrentClient')
    mock_client.upload_torrent = __mock_upload_torrent

    expected = (
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        '/gg-bot-upload-assistant/files/',
        False,
        True
    )
    assert utils.perform_post_processing(
        torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected


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
        f'{working_folder}{temp_working_dir}/temp_upload/{torrent_info["working_folder"]}TRACKER-Some Title different from torrent_title.torrent',
        f'{working_folder}{temp_working_dir}/files/',
        False,
        True
    )
    assert utils.perform_post_processing(torrent_info, mock_client, f"{working_folder}{temp_working_dir}", tracker) == expected
