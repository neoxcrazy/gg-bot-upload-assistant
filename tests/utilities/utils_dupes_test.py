import json
import shutil
import pytest
import threading

from pathlib import Path
from pytest_mock import mocker
from werkzeug.serving import make_server
from flask import Flask, jsonify, request, abort

from utilities.utils_dupes import *


working_folder = Path(__file__).resolve().parent.parent.parent
tracker_api_key = "TRACKER_API_DUMMY"

"""
     HOW IS THIS TESTS SETUP?
    ----------------------------------------------


"""

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


    # api_key based search endpoint
    @app.route('/api/torrents/filter', methods = ['GET'])
    def filter_torrents_dummy():
        sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/server_responses/{request.args.get("imdbId")}.json'))
        api_key = request.args.get("api_token")
        if api_key == tracker_api_key:
            return jsonify(sample_data)
        else:
            abort(403) 
    

    # Bearer Token based search endpoint
    @app.route('/api/torrents/filter/bearer', methods = ['GET'])
    def filter_torrents_dummy_bearer():
        sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/server_responses/{request.args.get("imdbId")}.json'))
        token = request.headers.get('Authorization')
        logging.info(f"Token: {token}")
        if token == f'Bearer {tracker_api_key}':
            return jsonify(sample_data)
        else:
            abort(403) 
    
    
    # Header based search endpoint
    @app.route('/api/torrents/filter/header', methods = ['GET'])
    def filter_torrents_dummy_header():
        sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/server_responses/{request.args.get("imdbId")}.json'))
        token = request.headers.get('X-API-KEY')
        logging.info(f"Token: {token}")
        if token == tracker_api_key:
            return jsonify(sample_data)
        else:
            abort(403) 


    server = ServerThread(app)
    server.start()


def stop_server():
    global server
    logging.info("Stopping dummy server")
    server.shutdown()


@pytest.fixture(scope="module", autouse=True)
def run_around_tests():
    source_destination_api_key_based = f'{working_folder}/tests/resources/dupes/templates/api_key_based.json'
    destination_api_key_based = f'{working_folder}/site_templates/api_key_based.json'
    shutil.copy(source_destination_api_key_based, destination_api_key_based)

    source_destination_token_based = f'{working_folder}/tests/resources/dupes/templates/token_based.json'
    destination_token_based = f'{working_folder}/site_templates/token_based.json'
    shutil.copy(source_destination_token_based, destination_token_based)

    source_destination_header_based = f'{working_folder}/tests/resources/dupes/templates/header_based.json'
    destination_header_based = f'{working_folder}/site_templates/header_based.json'
    shutil.copy(source_destination_header_based, destination_header_based)

    start_server()

    yield

    stop_server()
    Path(destination_api_key_based).unlink()
    Path(destination_token_based).unlink()
    Path(destination_header_based).unlink()


def __fetch_dupe_check_test_data():
    sample_data = json.load(open(f'{working_folder}/tests/resources/dupes/test_data.json'))
    test_cases = []

    for case in sample_data:
        test_cases.append(pytest.param(case["site_template"], case["imdb"], case["tmdb"], case["tvmaze"], case["auto_mode"], case["torrent_info"], case["expected"], id=case["name"]))

    return test_cases
    

@pytest.mark.parametrize( ( "site_template", "imdb", "tmdb", "tvmaze", "auto_mode", "torrent_info", "expected" ), __fetch_dupe_check_test_data() )
def test_search_for_dupes_api_api_key_based(site_template, imdb, tmdb, tvmaze, auto_mode, torrent_info, expected, mocker):
    # hardcoding 
    #   `debug` to False 
    #   `tracker_api` to TRACKER_API_DUMMY (tracker_api_key)
    mocker.patch("os.getenv", return_value=80)
    assert search_for_dupes_api(site_template, imdb, tmdb, tvmaze, torrent_info, tracker_api_key, auto_mode, working_folder, "true") == expected
