import json
import shutil
import pytest
import threading

from pathlib import Path
from pytest_mock import mocker
from werkzeug.serving import make_server
from flask import Flask, jsonify, request

from utilities.search_for_dupes import *


working_folder = Path(__file__).resolve().parent.parent.parent


"""
    Creating and starting a simple web-server. 
    The dupe check request will be sent to this server, and it'll return the hard-coded response.
"""
class ServerThread(threading.Thread):
    
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()


    def run(self):
        self.server.serve_forever()


    def shutdown(self):
        self.server.shutdown()


def start_server():
    global server
    app = Flask('gg-bot-upload-assistant-dummy')
    # App routes defined here

    @app.route('/api/torrents/filter', methods = ['GET'])
    def filter_torrents_dummy():
        sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/server_responses/{request.args.get("imdbId")}.json'))
        return jsonify(sample_data)

    server = ServerThread(app)
    server.start()


def stop_server():
    global server
    logging.info("Stopping dummy server")
    server.shutdown()


@pytest.fixture(autouse=True)
def run_around_tests():
    source = f'{working_folder}/tests/resources/dupes/imaginary.json'
    destination = f'{working_folder}/site_templates/imaginary.json'
    shutil.copy(source, destination)
    start_server()

    yield

    stop_server()
    Path(destination).unlink()


def __fetch_dupe_check_test_data():
    sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/data.json'))
    test_cases = []

    for case in sample_data:
        test_cases.append(pytest.param(case["imdb"], case["tmdb"], case["tvmaze"], case["torrent_info"], case["expected"], id=case["name"]))

    return test_cases
    

@pytest.mark.parametrize( ( "imdb", "tmdb", "tvmaze", "torrent_info", "expected" ), __fetch_dupe_check_test_data() )
def test_search_for_dupes_api(imdb, tmdb, tvmaze, torrent_info, expected, mocker):
    # hardcoding 
    #   `debug` to False 
    #   `auto_mode` to true
    #   `search_site` to imaginary
    #   `tracker_api` to TRACKER_API_DUMMY
    mocker.patch("os.getenv", return_value=80)
    assert search_for_dupes_api("imaginary", imdb, tmdb, tvmaze, torrent_info, "TRACKER_API_DUMMY", False, working_folder, "true") == expected