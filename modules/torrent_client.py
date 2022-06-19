import enum

from modules.torrent_clients.client_deluge import Deluge
from modules.torrent_clients.client_qbittorrent import Qbittorrent
from modules.torrent_clients.client_rutorrent import Rutorrent
from modules.torrent_clients.client_transmission import Transmission


# Using enum class create enumerations
class Clients(enum.Enum):
    Qbittorrent = 1
    Rutorrent = 2
    Deluge = 3
    Transmission = 4


class TorrentClientFactory():

    def create(self, client_type):
        targetclass = client_type.name.capitalize()
        return TorrentClient(globals()[targetclass]())


class TorrentClient:

    client = None

    def __init__(self, client):
        """
            Class will contain a torrent client that is created based on the `client_type` provided by the user.
            TorrentClients are created via the TorrentClientFactory.
        """
        self.client = client

    def hello(self):
        self.client.hello()

    def list_torrents(self):
        return self.client.list_torrents()

    def upload_torrent(self, torrent, save_path, use_auto_torrent_management, is_skip_checking, category=None):
        self.client.upload_torrent(
            torrent, save_path, use_auto_torrent_management, is_skip_checking, category)

    def update_torrent_category(self, info_hash, category_name=None):
        self.client.update_torrent_category(info_hash, category_name)
