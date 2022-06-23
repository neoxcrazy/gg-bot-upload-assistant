import enum

from modules.cache_vendors.cache_mongo import Mongo


class CacheVendor(enum.Enum):
    Mongo = 1


class CacheFactory():

    def create(self, cache_type):
        targetclass = cache_type.name.capitalize()
        return Cache(globals()[targetclass]())


class Cache:

    cache_client = None

    def __init__(self, cache_client):
        """ Cache is wrapper ever the differnet cache_clients that can be created.

            Caches are created by the CacheFactory based on the users configuration.
            Currently only Mongo Cache is available
        """
        self.cache_client = cache_client

    def hello(self):
        self.cache_client.hello()

    def save(self, key, data):
        self.cache_client.save(key, data)

    def delete(self, key, query=None):
        return self.cache_client.delete(key, query)

    def count(self, key, filter=None):
        return self.cache_client.count(key, filter)

    def get(self, key, filter=None):
        return self.cache_client.get(key, filter)

    def close(self):
        self.cache_client.close()

    def advanced_get(self, key, limit, page_number, sort_field=None, filter=None):
        return self.cache_client.advanced_get(key, limit, page_number, sort_field, filter)
