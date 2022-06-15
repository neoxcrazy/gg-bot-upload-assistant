import uuid
import json
import logging
import datetime


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
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE" # unrecoverable error. Needs to check the log or console to resolve them. Not automatic fix available


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
    logging.debug(f'[ReuploadUtils] Intializing torrent data in cache for {torrent["name"]}')
    init_data = {}
    init_data["id"] = get_unique_id()
    init_data["hash"] = torrent["hash"]
    init_data["name"] = torrent["name"]
    init_data["status"] = TorrentStatus.PENDING
    init_data["torrent"] = json.dumps(torrent)
     # when this attempt becomes greater than 3, the torrent will be marked as UNKNOWN_FAILURE
     # TODO convert this to a model class that can be used with GG-Bot Visor as well seamlessly
    init_data["upload_attempt"] = 1
    init_data["movie_db"] = "None"
    init_data["date_created"] = datetime.datetime.now().isoformat()
    init_data["possible_matches"] = "None"
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{torrent["hash"]}', init_data)
    logging.debug(f'[ReuploadUtils] Successfully initialized torrent data in cache for {torrent["name"]}')


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
    logging.debug(f'[ReuploadUtils] Updating status of `{info_hash}` from `{existing_data["status"]}` to `{status}`')
    existing_data["status"]=status
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', existing_data)


def update_field(info_hash, field, data, is_json, cache):
    # data will always be present
    existing_data = cache.get(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}')[0]
    if is_json and data is not None:
        data = json.dumps(data)
    logging.debug(f'[ReuploadUtils] Updating `{field}` of `{info_hash}` from `{existing_data[field]}` to `{data}`')
    existing_data[field]=data
    cache.save(f'{TORRENT_DB_KEY_PREFIX}::{info_hash}', existing_data)


def insert_into_job_repo(job_repo_entry, cache):
    logging.debug(f'[ReuploadUtils] Saving job entry in cache for {job_repo_entry["hash"]}')
    cache.save(f'{JOB_REPO_DB_KEY_PREFIX}::{job_repo_entry["hash"]}::{job_repo_entry["tracker"]}', job_repo_entry)
    logging.debug(f'[ReuploadUtils] Successfully saved job entry in cache for {job_repo_entry["hash"]}')


def cache_tmdb_selection(cache, movie_db):
    cache.save(f'{TMDB_DB_KEY_PREFIX}::{movie_db["title"]}@{movie_db["year"]}', movie_db)


def check_for_tmdb_cached_data(cache, title, year, content_type):
    data = cache.get(f'{TMDB_DB_KEY_PREFIX}', { "$or": [ { "$and": [ { "type": content_type }, { "$and": [ { "title": title }, { "year": year } ] } ] }, { "$and": [ { "type": content_type }, { "title": title } ] } ] } )
    return data[0] if data is not None and len(data) > 0 else None
