import math
import json

from bson import json_util


TORRENT_DB_KEY_PREFIX = "ReUpload::Torrent"
JOB_REPO_DB_KEY_PREFIX = "ReUpload::JobRepository"


class TorrentStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIALLY_SUCCESSFUL = "PARTIALLY_SUCCESSFUL"
    TMDB_IDENTIFICATION_FAILED = "TMDB_IDENTIFICATION_FAILED"
    PENDING = "PENDING"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
    DUPE_CHECK_FAILED = "DUPE_CHECK_FAILED"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"


class JobStatus():
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Query():
    ALL_FAILED = {'status': {'$in' : [TorrentStatus.FAILED, TorrentStatus.TMDB_IDENTIFICATION_FAILED, TorrentStatus.UNKNOWN_FAILURE, TorrentStatus.DUPE_CHECK_FAILED]}}
    FAILED = {'status': TorrentStatus.FAILED}
    SUCCESS = {'status': TorrentStatus.SUCCESS}
    UNKNOWN_FAILURE = {'status': TorrentStatus.UNKNOWN_FAILURE}
    DUPE_CHECK_FAILED = {'status': TorrentStatus.DUPE_CHECK_FAILED}
    PARTIALLY_SUCCESSFUL = {'status': TorrentStatus.PARTIALLY_SUCCESSFUL}
    TMDB_IDENTIFICATION_FAILED = {'status': TorrentStatus.TMDB_IDENTIFICATION_FAILED}


def __count_torrents_collection(cache, filter_criteria):
    return cache.count(TORRENT_DB_KEY_PREFIX, filter_criteria)


def __get_all_data_from_torrents_collection(cache, page_number, sort_field, items_per_page, filter_query):
    return cache.advanced_get(TORRENT_DB_KEY_PREFIX, items_per_page, page_number, sort_field, filter_query)


def __get_unique_document(cache, info_hash):
    document = cache.get(TORRENT_DB_KEY_PREFIX, { "hash" : { "$regex" : f"^{info_hash}" } } )
    return None if len(document) != 1 else document[0]


def get_torrent_statistics(cache):
    return {
        "all": __count_torrents_collection(cache, {}),
        "successful": __count_torrents_collection(cache, Query.SUCCESS),
        "failed": __count_torrents_collection(cache, Query.ALL_FAILED),
        "partial": __count_torrents_collection(cache, Query.PARTIALLY_SUCCESSFUL)
    }


def failed_torrents_statistics(cache):
    return {
        "all": __count_torrents_collection(cache, {}),
        "partial_failure": __count_torrents_collection(cache, Query.PARTIALLY_SUCCESSFUL),
        "tmdb_failure": __count_torrents_collection(cache, Query.TMDB_IDENTIFICATION_FAILED),
        "unknown_failure": __count_torrents_collection(cache, Query.UNKNOWN_FAILURE),
        "dupe_check_failure": __count_torrents_collection(cache, Query.DUPE_CHECK_FAILED),
        "upload_failure": __count_torrents_collection(cache, Query.FAILED),
    }


def all_torrents(cache, filter_query: dict = None, items_per_page: int = 20, page: int = 1, sort: str = "id"):
    total_number_of_torrents = __count_torrents_collection(cache, filter_query)
    total_pages = math.ceil(total_number_of_torrents/items_per_page)

    return {
        "page": {
            "page_number" : page,
            "total_pages" : total_pages,
            "total_torrents": total_number_of_torrents,
        },
        "torrents" : json.loads(json_util.dumps(__get_all_data_from_torrents_collection(cache, page, sort.lower(), items_per_page, filter_query)))
    }
