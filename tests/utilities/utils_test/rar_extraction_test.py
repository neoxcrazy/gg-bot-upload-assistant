import os
import shutil
import pytest
import logging

from pathlib import Path
from pytest_mock import mocker
from unittest.mock import MagicMock
import utilities.utils as utils


working_folder = Path(__file__).resolve().parent.parent.parent.parent
temp_working_dir = "/tests/working_folder"
rar_file_source = "/tests/resources/rar/data.rar" # this file already exists
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
    folder = f"{working_folder}{temp_working_dir}"

    if Path(folder).is_dir():
        clean_up(folder)
    else:
        Path(f"{folder}/rar").mkdir(parents=True, exist_ok=True) # rar folder
        Path(f"{folder}/media").mkdir(parents=True, exist_ok=True) # rar folder
    
    shutil.copy(f"{working_folder}{rar_file_source}", f"{working_folder}{rar_file_target}")
    yield
    clean_up(folder)


def test_check_for_dir_and_extract_rars_file():
    file_path = "tests/working_folder/rar/data.rar"
    assert utils.check_for_dir_and_extract_rars(file_path) == (True, file_path)


def test_check_for_dir_and_extract_rars_non_rar_folder():
    file_path = "tests/working_folder/media/"
    assert utils.check_for_dir_and_extract_rars(file_path) == (True, file_path)


def test_check_for_dir_and_extract_rars_rar_folder():
    file_path = "tests/working_folder/rar/"
    assert utils.check_for_dir_and_extract_rars(file_path) == (True, "tests/working_folder/rar/something.mkv")


def test_check_for_dir_and_extract_rars_no_rar_installed(mocker):
    file_path = "tests/working_folder/rar/"
    mocker.patch('os.path.isfile', return_value=False)
    assert utils.check_for_dir_and_extract_rars(file_path) == (False, file_path)