import enum

from modules.torrent_clients.client_qbittorrent import Qbittorrent
from modules.torrent_clients.client_rtorrent import Rutorrent

# Using enum class create enumerations
class Clients(enum.Enum):
    Qbittorrent = 1
    Rutorrent = 2
    Deluge = 3


class TorrentClientFactory():

    def create(self, type):
        targetclass = type.name.capitalize()
        return TorrentClient(globals()[targetclass]())


class TorrentClient:
    
    client = None

    def __init__(self, client):
        self.client = client

    def hello(self):
        self.client.hello()
    
    def list_torrents(self):
        return self.client.list_torrents()
    
    def upload_torrent(self, torrent, save_path, use_auto_torrent_management, is_skip_checking, category=None):
        self.client.upload_torrent(torrent, save_path, use_auto_torrent_management, is_skip_checking, category)
    
    def update_torrent_category(self, info_hash, category_name=None):
        self.client.update_torrent_category(info_hash, category_name)
        