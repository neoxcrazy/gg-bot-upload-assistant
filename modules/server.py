import os
import time
import hashlib
import functools

from threading import Thread
from flask import Flask, Response, request

import utilities.utils_visor_server as visor


stored_key = hashlib.sha3_256(os.getenv("server_secret_key", "secret").encode()).hexdigest()


def is_valid(api_key):
    return stored_key == hashlib.sha3_256(api_key.encode()).hexdigest()


def api_required(function):
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        api_key = request.args.get("api_key", None)
        if api_key is None:
            return {"status": "UNAUTHORIZED", "message": "Please provide an api key"}, 403

        if not is_valid(api_key):
            return {"status": "UNAUTHORIZED", "message": "Unauthorized Access"}, 403

        return function(*args, **kwargs)
    return decorator


def gg_bot_response(function):
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        return { "status" : "OK", "data" : function(*args, **kwargs) }, 200
    return decorator


class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    def __call__(self, *args, **kwargs):
        return self.action(*args, **kwargs)


class Server(object):
    app = None
    cache = None


    def __init__(self, cache):
        self.app = Flask('GG-BOT Auto-ReUploader')
        self.cache = cache
        self.add_endpoint(endpoint='/status', endpoint_name='GG-BOT Status', handler=self.status)
        self.add_endpoint(endpoint='/torrents/', endpoint_name='Get All Torrents', handler=self.torrents)
        self.add_endpoint(endpoint='/torrents/statistics', endpoint_name='Torrent Statistics', handler=self.torrent_statistics)
        self.add_endpoint(endpoint='/torrents/success', endpoint_name='Get All Successful Torrents', handler=self.successful_torrents)
        self.add_endpoint(endpoint='/torrents/failed', endpoint_name='Get All Failed Torrents', handler=self.failed_torrents)
        self.add_endpoint(endpoint='/torrents/failed/statistics', endpoint_name='Get Failed Torrents Statistics', handler=self.failed_torrents_statistics)
        self.add_endpoint(endpoint='/torrents/partial', endpoint_name='Get All Partially Successful Torrents', handler=self.partially_successful_torrents)


    def run(self):
        self.app.run(port=5001, host="0.0.0.0")


    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler))


    def start(self, detached=False):
        kwargs = {'host': '127.0.0.1', 'port': 5001, 'threaded': True, 'use_reloader': False, 'debug': False}
        Thread(target=self.run, daemon=True, kwargs=kwargs).start() if detached == True else self.run()


    @api_required
    def status(self):
        return {'status': 'OK', "message": "GG-BOT Auto-ReUploader"}, 200


    @api_required
    @gg_bot_response
    def torrent_statistics(self):
        return visor.get_torrent_statistics(self.cache)


    @api_required
    @gg_bot_response
    def failed_torrents_statistics(self):
        return visor.failed_torrents_statistics(self.cache)


    @api_required
    @gg_bot_response
    def torrents(self):
        sort = request.args.get("sort", "id")
        page = int(request.args.get("page", 1))
        items_per_page = int(request.args.get("items_per_page", 20))

        # validating user provided params
        if sort.lower() not in ["id", "name", "hash", "status", "date_created"]:
            return {"message": "Invalid sort option provided"}

        return visor.all_torrents(cache=self.cache, sort=sort.lower(), page=page, items_per_page=items_per_page)


    @api_required
    @gg_bot_response
    def successful_torrents(self):
        sort = request.args.get("sort", "id")
        page = int(request.args.get("page", 1))
        items_per_page = int(request.args.get("items_per_page", 20))

        # validating user provided params
        if sort.lower() not in ["id", "name", "hash", "status", "date_created"]:
            return {"message": "Invalid sort option provided"}

        return visor.all_torrents(cache=self.cache, sort=sort.lower(), page=page, items_per_page=items_per_page, filter_query=visor.Query.SUCCESS)


    @api_required
    @gg_bot_response
    def failed_torrents(self):
        sort = request.args.get("sort", "id")
        page = int(request.args.get("page", 1))
        items_per_page = int(request.args.get("items_per_page", 20))

        # validating user provided params
        if sort.lower() not in ["id", "name", "hash", "status", "date_created"]:
            return {"message": "Invalid sort option provided"}

        return visor.all_torrents(cache=self.cache, sort=sort.lower(), page=page, items_per_page=items_per_page, filter_query=visor.Query.ALL_FAILED)


    @api_required
    @gg_bot_response
    def partially_successful_torrents(self):
        sort = request.args.get("sort", "id")
        page = int(request.args.get("page", 1))
        items_per_page = int(request.args.get("items_per_page", 20))

        # validating user provided params
        if sort.lower() not in ["id", "name", "hash", "status", "date_created"]:
            return {"message": "Invalid sort option provided"}

        return visor.all_torrents(cache=self.cache, sort=sort.lower(), page=page, items_per_page=items_per_page, filter_query=visor.Query.PARTIALLY_SUCCESSFUL)