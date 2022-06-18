import enum
from modules.cache_vendors.cache_mongo import Mongo


class CacheVendor(enum.Enum):
    Mongo = 1


class CacheFactory():

    def create(self, type):
        targetclass = type.name.capitalize()
        return Cache(globals()[targetclass]())


class Cache:

    cache_client = None

    def __init__(self, cache_client):
        self.cache_client = cache_client

    def hello(self):
        self.cache_client.hello()

    def save(self, key, data):
        self.cache_client.save(key, data)

    def save_or_update(self, key, data):
        self.cache_client.save_or_update(key, data)

    def delete(self, key, query=None):
        return self.cache_client.delete(key, query)

    def count(self, key, filter=None):
        return self.cache_client.count(key, filter)

    def get(self, key, filter=None):
        return self.cache_client.get(key, filter)

    def get_all(self, key):
        return self.cache_client.get_all(key)

    def close(self):
        self.cache_client.close()

    def filter(self, key, filter):
        return self.cache_client.filter(key, filter)
