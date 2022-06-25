import os
import uuid
import json
import logging
import datetime

from pprint import pformat
from utilities.utils import get_and_validate_configured_trackers


TORRENT_DB_KEY_PREFIX = "ReUpload::Torrent"
JOB_REPO_DB_KEY_PREFIX = "ReUpload::JobRepository"
TMDB_DB_KEY_PREFIX = "MetaData::TMDB"
UPLOAD_RETRY_LIMIT = 3


class TorrentStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"
    TMDB_IDENTIFICATION_FAILED = "TMDB_IDENTIFICATION_FAILED"
    PENDING = "PENDING"
    DUPE_CHECK_FAILED = "DUPE_CHECK_FAILED"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"
    # unrecoverable error. Needs to check the log or console to resolve them. Not automatic fix available
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class JobStatus():
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def get_unique_id():
    return str(uuid.uuid4())


def get_torrent_status(info_hash, cache):
    data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}')
    return data[0]["status"] if data is not None and len(data) > 0 else None


def is_unprocessable_data_present_in_cache(info_hash, cache):
    """
        cached_data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', "status")
        return cached_data is not None and cached_data not in [TorrentStatus.READY_FOR_PROCESSING, TorrentStatus.PENDING]

    """
    # torrents in pending or ready for processing can be uploaded again.
    # torrents that are in other statuses needs no more processing
    torrent_status = get_torrent_status(info_hash, cache)
    # status that are not mentioned below cannot be processed again by the uploader automatically
    return torrent_status is not None and torrent_status not in [TorrentStatus.READY_FOR_PROCESSING, TorrentStatus.PENDING]


def initialize_torrent_data(torrent, cache):
    logging.debug(
        f'[ReuploadUtils] Intializing torrent data in cache for {torrent["name"]}')
    init_data = {}
    init_data["id"] = get_unique_id()
    init_data["hash"] = torrent["hash"]
    init_data["name"] = torrent["name"]
    init_data["status"] = TorrentStatus.PENDING
    init_data["torrent"] = json.dumps(torrent)
    # when this attempt becomes greater than 3, the torrent will be marked as UNKNOWN_FAILURE
    init_data["upload_attempt"] = 1
    init_data["movie_db"] = "None"
    init_data["date_created"] = datetime.datetime.now().isoformat()
    init_data["possible_matches"] = "None"
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{torrent["hash"]}', init_data)
    logging.debug(
        f'[ReuploadUtils] Successfully initialized torrent data in cache for {torrent["name"]}')
    return init_data  # adding return for testing


def should_upload_be_skipped(cache, torrent):
    logging.info(f'[ReuploadUtils] Updating upload attempt for torrent {torrent["name"]}')
    torrent["upload_attempt"] = torrent["upload_attempt"] + 1
    if torrent["upload_attempt"] > UPLOAD_RETRY_LIMIT:
        torrent["status"] = TorrentStatus.UNKNOWN_FAILURE
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{torrent["hash"]}', torrent)
    return torrent["upload_attempt"] > UPLOAD_RETRY_LIMIT


def get_cached_data(info_hash, cache):
    data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}')
    return data[0] if data is not None and len(data) > 0 else None


def update_torrent_status(info_hash, status, cache):
    # data will always be present
    existing_data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}')[0]
    logging.debug(
        f'[ReuploadUtils] Updating status of `{info_hash}` from `{existing_data["status"]}` to `{status}`')
    existing_data["status"] = status
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', existing_data)
    return existing_data  # returning data for testing


def update_field(info_hash, field, data, is_json, cache):
    # data will always be present
    existing_data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}')[0]
    if is_json and data is not None:
        data = json.dumps(data)
    logging.debug(
        f'[ReuploadUtils] Updating `{field}` of `{info_hash}` from `{existing_data[field]}` to `{data}`')
    existing_data[field] = data
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', existing_data)
    return existing_data  # returning data for testing


def insert_into_job_repo(job_repo_entry, cache):
    logging.debug(
        f'[ReuploadUtils] Saving job entry in cache for {job_repo_entry["hash"]}')
    cache.save(
        f'{JOB_REPO_DB_KEY_PREFIX}::{job_repo_entry["hash"]}::{job_repo_entry["tracker"]}', job_repo_entry)
    logging.debug(
        f'[ReuploadUtils] Successfully saved job entry in cache for {job_repo_entry["hash"]}')
    return job_repo_entry  # returning data for testing


def _cache_tmdb_selection(cache, movie_db):
    cache.save(
        f'{TMDB_DB_KEY_PREFIX}::{movie_db["title"]}@{movie_db["year"]}', movie_db)


def _check_for_tmdb_cached_data(cache, title, year, content_type):
    data = cache.get(f'{TMDB_DB_KEY_PREFIX}', {"$or": [{"$and": [{"type": content_type}, {"$and": [
                     {"title": title}, {"year": year}]}]}, {"$and": [{"type": content_type}, {"title": title}]}]})
    return data[0] if data is not None and len(data) > 0 else None


def reupload_get_movie_db_from_cache(cache, cached_data, title, year, upload_type):
    movie_db = _check_for_tmdb_cached_data(cache, title, year, upload_type)
    logging.debug(
        f"[Main] MovieDB data obtained from cache: {pformat(movie_db)}")

    # if we don't have any movie_db data cached in tmdb repo, repo then we'll initialize the movie_db dictionary.cache
    # similarly if there is a user provided tmdb id (from gg-bot-visor) then we'll give higher priority to users choice and clear the cached movie_db
    if movie_db is None or (cached_data is not None and "tmdb_user_choice" in cached_data):
        return dict()
    return movie_db


def reupload_persist_updated_moviedb_to_cache(cache, movie_db, torrent_info, torrent_hash, original_title, original_year):
    # checking whether we got any data or whether it was a empty dict
    cache_tmdb_metadata = "tmdb" not in movie_db

    movie_db["tmdb"] = torrent_info["tmdb"] if "tmdb" in torrent_info else "0"
    movie_db["imdb"] = torrent_info["imdb"] if "imdb" in torrent_info else "0"
    movie_db["tvmaze"] = torrent_info["tvmaze"] if "tvmaze" in torrent_info else "0"
    movie_db["tvdb"] = torrent_info["tvdb"] if "tvdb" in torrent_info else "0"
    movie_db["mal"] = torrent_info["mal"] if "mal" in torrent_info else "0"
    movie_db["title"] = original_title
    movie_db["year"] = original_year
    movie_db["type"] = torrent_info["type"]
    backup_id = None

    if "_id" in movie_db:
        backup_id = movie_db["_id"]
        del movie_db['_id']

    update_field(torrent_hash, "movie_db", movie_db, True, cache)

    if cache_tmdb_metadata:
        if backup_id is not None:
            movie_db['_id'] = backup_id
        _cache_tmdb_selection(cache, movie_db)

    return movie_db


def reupload_get_external_id_based_on_priority(movie_db, torrent_info, cached_data, required_id):
    # in case of tmdb id, we need to give highest priority to the golden data obtained from the user via GG-BOT Visor
    # If bot wants tmdb id and we have data in cached data (for currently uploading torrent) then we return it.
    # Other wise we go for the cached movieDB data (from another torrent)
    # and finally we get the data from media_info_summary
    if required_id == "tmdb":
        if cached_data is not None and "tmdb_user_choice" in cached_data:
            # this is value provided by the user. This will never be None and is considered as ~~ GOLDEN ~~
            # TMDB id from GG-BOT Visor
            return str(cached_data["tmdb_user_choice"])

    external_db_id = ""
    if required_id in movie_db:  # TODO need to figure out why None is saved in metadata db
        external_db_id = str(
            movie_db[required_id]) if movie_db[required_id] is not None else ""
    elif required_id in torrent_info:
        external_db_id = str(
            torrent_info[required_id]) if torrent_info[required_id] is not None else ""
    return external_db_id


def reupload_get_processable_torrents(torrent_client, cache):
    logging.info('[Main] Listing latest torrents status from client')
    # listing all the torrents that needs to be re-uploaded
    torrents = torrent_client.list_torrents()

    # Attributes present in the torrent list
    # "category", "completed", "content_path", "hash", "name", "save_path", "size", "tracker"
    logging.info(f'[Main] Total number of torrents that needs to be reuploaded are {len(torrents)}')

    # listing out only the completed torrents and eliminating unprocessable torrents based on cached data
    logging.debug(f'[Main] Torrent data from client: {pformat(torrents)}')
    torrents = list(
        filter(lambda torrent: not is_unprocessable_data_present_in_cache(torrent["hash"], cache),
               filter(
            lambda torrent: torrent["completed"] == torrent["size"], torrents)
        )
    )
    logging.info(f'[Main] Total number of completed torrents that needs to be reuploaded are {len(torrents)}')
    return torrents


def reupload_get_translated_torrent_path(torrent_path):
    if str(os.getenv('translation_needed', 'false')).lower() == 'true':
        logging.info('[Main] Translating paths... ("translation_needed" flag set to True in reupload.config.env) ')

        # Just in case the user didn't end the path with a forward slash...
        host_path = f"{os.getenv('uploader_path', '')}/".replace('//', '/')
        remote_path = f"{os.getenv('torrent_client_path', '')}/".replace('//', '/')

        translated_path = str(torrent_path).replace(remote_path, host_path)
        # And finally log the changes
        logging.info(f'[Main] Remote path of the torrent: {torrent_path}')
        logging.info(f'[Main] Translated path of the torrent: {translated_path}')
        torrent_path = translated_path
    return torrent_path


def get_available_dynamic_trackers(torrent_client, torrent, upload_to_trackers, api_keys_dict, all_trackers_list):
    # we first try to dynamically select the trackers to upload to from the torrent label. (if the feature is enabled.)
    if bool(os.getenv("dynamic_tracker_selection", False)) == True:
        try:
            dynamic_trackers = torrent_client.get_dynamic_trackers(torrent)
            return get_and_validate_configured_trackers(
                trackers = dynamic_trackers,
                all_trackers = False,
                api_keys_dict = api_keys_dict,
                all_trackers_list = all_trackers_list
            )
        except AssertionError:
            logging.error(f"[Main] None of the trackers dynamic trackers {dynamic_trackers} have a valid configuration. Proceeding with fall back trackers {upload_to_trackers}")

    # well, no need to select trackers dynamically or no valid dynamic trackers (exception case)
    return upload_to_trackers