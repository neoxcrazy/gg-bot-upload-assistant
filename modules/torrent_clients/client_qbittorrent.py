import os
import logging
import qbittorrentapi

from datetime import datetime


qbt_keys = ["category", "completed", "content_path", "hash", "name", "save_path", "size", "tracker"]


class Qbittorrent:
    """
        Client Specific Configurations
        Host, Port, Username, Password
    """

    def __init__(self):
        logging.info("[Qbittorrent] Connecting to the qbittorrent instance...")
        self.qbt_client = qbittorrentapi.Client(
            host=os.getenv('client_host'),
            port=os.getenv('client_port'),
            username=os.getenv('client_username'),
            password=os.getenv('client_password'),
        )
        # `target_label` is the label of the torrents that we are interested in
        self.target_label = os.getenv('reupload_label', '')
        # `seed_label` is the label which will be added to the cross-seeded torrents
        self.seed_label = os.getenv('cross_seed_label', 'GGBotCrossSeed')
        # `source_label` is thelabel which will be added to the original torrent in the client
        self.source_label = f"{self.seed_label}_Source"

        try:
            logging.info("[Qbittorrent] Authenticating with the qbittorrent instance...")
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as err:
            logging.fatal("[Qbittorrent] Authentication with qbittorrent instance failed")
            raise err

    def hello(self):
        logging.info(f"[Qbittorrent] Hello from qbittorrent {self.qbt_client.app.version} and web api {self.qbt_client.app.web_api_version}")
        print(f'qBittorrent: {self.qbt_client.app.version}')
        print(f'qBittorrent Web API: {self.qbt_client.app.web_api_version}')

    def __match_label(self, torrent):
        # we don't want to consider cross-seeded torrents uploaded by the bot
        if self.seed_label == torrent.category:
            return False
        # user wants to ignore labels, hence we'll consider all the torrents
        if self.target_label == "IGNORE_LABEL":
            return True
        return torrent.category == self.target_label

    def __extract_necessary_keys(self, torrent):
        return {key: value for key, value in torrent.items() if key in qbt_keys}

    # torrents_set_category
    def __list_categories(self):
        return self.__get_torrent_categories().categories

    def __get_torrent_categories(self):
        return self.qbt_client.torrent_categories

    def __create_category(self, name, save_path):
        self.__get_torrent_categories().create_category(name=name, save_path=save_path)

    def list_torrents(self):
        logging.debug(f"[Qbittorrent] Listing torrents at {datetime.now()}")
        return list(map(self.__extract_necessary_keys, filter(self.__match_label, self.qbt_client.torrents_info())))

    def upload_torrent(self, torrent_path, save_path, use_auto_torrent_management, is_skip_checking, category=None):
        self.qbt_client.torrents_add(
            torrent_files=torrent_path,
            save_path=save_path,
            category=category if category is not None else self.seed_label,
            use_auto_torrent_management=use_auto_torrent_management,
            is_skip_checking=is_skip_checking
        )
        # self.qbt_client.torrents_resume(info_hash)

    def update_torrent_category(self, info_hash, category_name):
        category_name = category_name if category_name is not None else self.source_label
        if category_name not in list(self.__list_categories()):
            # if the category  `category_name` doesn't exist we create it
            self.__create_category(category_name, None)
        self.qbt_client.torrents_set_category(
            category=category_name, torrent_hashes=info_hash)
