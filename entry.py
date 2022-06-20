import os

from modules.cache import CacheFactory, CacheVendor
from dotenv import load_dotenv
from modules.server import Server

working_folder = os.path.dirname(os.path.realpath(__file__))
load_dotenv(f'{working_folder}/reupload.config.env')

cache_client_factory = CacheFactory()
# creating the torrent client using the factory based on the users configuration
cache = cache_client_factory.create(CacheVendor[os.getenv('cache_type')])
# checking whether the cache connection has been created successfully or not
cache.hello()

server = Server(cache)
server.start()
