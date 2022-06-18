import os
import logging
import functools

from pymongo import MongoClient


class Mongo:

    mongo_client = None
    is_mongo_initalized = False
    database = None

    def __init__(self):
        """
            Method to initialize the connection to a redis database.
        """
        # Provide the mongodb atlas url to connect python to mongodb using pymongo
        if os.getenv('cache_username') is not None and len(os.getenv('cache_username')) > 0:
            CONNECTION_STRING = f"mongodb://{os.getenv('cache_username')}:{os.getenv('cache_password')}@{os.getenv('cache_host')}:{os.getenv('cache_port')}/{os.getenv('cache_database')}"
        else:
            CONNECTION_STRING = f"mongodb://{os.getenv('cache_host')}:{os.getenv('cache_port')}/{os.getenv('cache_database')}"

        if not self.is_mongo_initalized:
            try:
                self.mongo_client = MongoClient(CONNECTION_STRING)
                self.mongo_client.admin.command('ping')
                self.is_mongo_initalized = True
                self.database = self.mongo_client[os.getenv('cache_database')]
            except Exception as ex:
                logging.fatal(
                    f'[Cache] Failed to connect to Mongo DB. Error: {ex}')
                raise Exception(f"Failed to connect to Mongo DB. Error: {ex}")

    def map_cursor_to_list(function):
        @functools.wraps(function)
        def decorator(*args, **kwargs):
            return list(map(lambda d: d, function(*args, **kwargs)))
        return decorator

    def hello(self):
        if self.is_mongo_initalized:
            # print("Initialzed connection to the redis server configured")
            self.mongo_client.admin.command('ping')
            # print("Successfully established the connection to the server")
            print(f'Mongo Server Connection Established Successfully')
        else:
            print("Failed to initialize connection to Mongo server")

    def __get_collection(self, key):
        if not self.is_mongo_initalized:
            raise Exception(
                "Mongo client has not been initalized yet. Use the init() to initalize connection.")
        key = key.split("::")
        return self.database[key[0] + "_" + key[1]]

    def save(self, key, data):
        collection = self.__get_collection(key)
        if "_id" not in data:
            collection.insert_one(data)
        else:
            collection.replace_one({"_id": data['_id']}, data, upsert=True)

    def delete(self, key, query=None):
        """
            Method to delete data from the cache stored against a key 
        """
        collection = self.__get_collection(key)
        if len(key.split("::")) <= 2:
            # no hash provided in key. hence we need to use the user provided query
            # if user has not provided any query then we'll raise an exception
            if query is None:
                raise Exception(
                    "No hash or query provided. Cannot delete document")
            # returns the number of documents deleted
            return collection.delete_many(query)
        else:
            collection.delete_one({"hash": key.split("::")[2]})
            return 1

    @map_cursor_to_list
    def get(self, key, filter=None):
        collection = self.__get_collection(key)
        # <=2 because keys are in the form of GROUP::COLLECTION::KEY
        filter = ({} if filter is None else filter) if len(
            key.split("::")) <= 2 else {"hash": key.split("::")[2]}
        return collection.find(filter)

    @map_cursor_to_list
    def advanced_get(self, key, limit, page_number, sort_field, filter={}):
        collection = self.__get_collection(key)
        return collection.find(filter).skip((page_number - 1) * limit).limit(limit).sort(sort_field, -1)

    def count(self, key, filter=None):
        collection = self.__get_collection(key)
        return collection.count_documents(filter if filter is not None else {})

    def close(self):
        """
            Method to close the connection to the redis server
            This is a wrapper around the redis `hgetall` operation
        """
        if not self.is_mongo_initalized:
            raise Exception(
                "Redis client has not been initalized yet. Use the init() to initalize connection.")
        self.mongo_client.close()
