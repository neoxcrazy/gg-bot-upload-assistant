import os
import glob
import math
import logging

from torf import Torrent
from pathlib import Path
from datetime import datetime


class GGBOTTorrent(Torrent):
    piece_size_max = 32 * 1024 * 1024 # 32MB as max piece size


def callback_progress(torrent, filepath, pieces_done, pieces_total):
    calculate_percentage = 100 * float(pieces_done) / float(pieces_total)
    print_progress_bar(calculate_percentage, 100, prefix='Creating .torrent file:', suffix='Complete', length=30)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


def get_piece_size_for_mktorrent(size):
    """
        How pieces are calclated when using mktorrent...

        2^19 = 524 288 = 512 KiB for filesizes between 512 MiB - 1024 MiB
        2^20 = 1 048 576 = 1024 KiB for filesizes between 1 GiB - 2 GiB
        2^21 = 2 097 152 = 2048 KiB for filesizes between 2 GiB - 4 GiB
        2^22 = 4 194 304 = 4096 KiB for filesizes between 4 GiB - 8 GiB
        2^23 = 8 388 608 = 8192 KiB for filesizes between 8 GiB - 16 GiB
        2^24 = 16 777 216 = 16384 KiB for filesizes between 16 GiB - 512 GiB This is the max you should ever have to use.
        2^25 = 33 554 432 = 32768 KiB (note that utorrent versions before 3.x CANNOT load torrents with this or higher piece-size)
    """
    if size <= 2**30:           # < 1024 MiB
        return 19
    elif size <= 2 * 2**30:     # 1 GiB - 2 GiB
        return 20
    elif size <= 4 * 2**30:     # 2 GiB - 4 GiB
        return 21
    elif size <= 8 * 2**30:     # 4 GiB - 8 GiB
        return 22
    elif size <= 16 * 2**30:    # 8 GiB - 16 GiB
        return 23
    elif size <= 64 * 2**30:    # 16 GiB - 64 GiB
        return 24
    else:                       # anything > 32 GiB
        return 25


def calculate_piece_size(size):
    """
    Return the piece size for a total torrent size of ``size`` bytes

    For torrents up to 1 GiB, the maximum number of pieces is 1024 which
    means the maximum piece size is 1 MiB.  With increasing torrent size
    both the number of pieces and the maximum piece size are gradually
    increased up to 10,240 pieces of 8 MiB.  For torrents larger than 80 GiB
    the piece size is :attr:`piece_size_max` with as many pieces as
    necessary.

    It is safe to override this method to implement a custom algorithm.

    :return: calculated piece size
    """
    if size <= 1 * 2**30:      # 1 GiB / 1024 pieces = 1 MiB max
        pieces = size / 1024
    elif size <= 2 * 2**30:    # 2 GiB / 2048 pieces = 2 MiB max
        pieces = size / 1024
    elif size <= 4 * 2**30:    # 4 GiB / 2048 pieces = 2 MiB max
        pieces = size / 1024
    elif size <= 8 * 2**30:    # 8 GiB / 2048 pieces = 4 MiB max
        pieces = size / 2048
    elif size <= 16 * 2**30:   # 16 GiB / 2048 pieces = 8 MiB max
        pieces = size / 2048
    elif size <= 32 * 2**30:   # 32 GiB / 2048 pieces = 16 MiB max
        pieces = size / 2048
    elif size <= 64 * 2**30:   # 64 GiB / 4096 pieces = 16 MiB max
        pieces = size / 4096
    elif size > 64 * 2**30:
        pieces = size / 4096  # 32 MiB max
    # Math is magic!
    # piece_size_max :: 32 * 1024 * 1024 => 16MB
    return int(min(max(1 << max(0, math.ceil(math.log(pieces, 2))), 16 * 1024), 32 * 1024 * 1024))



def generate_dot_torrent(media, announce, source, working_folder, use_mktorrent, tracker, torrent_title,torrent, hash_prefix=""):
    """
        media : the -p path param passed to GGBot. (dot torrent will be created for this path or file)
    """
    logging.info("[DotTorrentGeneration] Creating the .torrent file now")
    logging.info(f"[DotTorrentGeneration] Primary announce url: {announce[0]}")
    logging.info(f"[DotTorrentGeneration] Source field in info will be set as `{source}`")

    if len(glob.glob(torrent)) == 0:
        return 'skip_to_next_file'
        # we need to actually generate a torrent file "from scratch"
        logging.info("[DotTorrentGeneration] Generating new .torrent file since old ones doesn't exist")
        if use_mktorrent:
            print("Using mktorrent to generate the torrent")
            logging.info("[DotTorrentGeneration] Using MkTorrent to generate the torrent")
            """
            mktorrent options
                -v => Be verbose.
                -p => Set the private flag.
                -a => Specify the full announce URLs.  Additional -a adds backup trackers.
                -o => Set the path and filename of the created file.  Default is <name>.torrent.
                -c => Add a comment to the metainfo.
                -s => Add source string embedded in infohash.
                -l => piece size (potency of 2)

                -e *.txt,*.jpg,*.png,*.nfo,*.svf,*.rar,*.screens,*.sfv # TODO to be added when supported mktorrent is available in alpine
            current version of mktorrent pulled from alpine package doesn't have the -e flag.
            Once an updated version is available, the flag can be added
            """
            torrent_size = sum(f.stat().st_size for f in Path(media).glob('**/*') if f.is_file()) if os.path.isdir(media) else os.path.getsize(media)
            piece_size = get_piece_size_for_mktorrent(torrent_size)
            logging.info(f'[DotTorrentGeneration] Size of the torrent: {torrent_size}')
            logging.info(f'[DotTorrentGeneration] Piece Size of the torrent: {piece_size}')

            os.system(
                f"mktorrent -v -p -l {piece_size} -c \"Torrent created by GG-Bot Upload Assistant\" -s '{source}' -a '{announce[0]}' -o \"{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent\" \"{media}\"")

            logging.info("[DotTorrentGeneration] Mktorrent .torrent write into {}".format("[" + source + "]" + torrent_title + ".torrent"))

            logging.info("[DotTorrentGeneration] Using torf to do some cleanup on the created torrent")
            edit_torrent = GGBOTTorrent.read(glob.glob(f'{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent')[0])
            edit_torrent.created_by = "GG-Bot Upload Assistant"
            edit_torrent.metainfo['created by'] = "GG-Bot Upload Assistant"

            if len(announce) > 1:
                # multiple announce urls
                edit_torrent.metainfo['announce-list'] = []
                for announce_url in announce:
                    edit_torrent.metainfo['announce-list'].append([announce_url])

            GGBOTTorrent.copy(edit_torrent).write(filepath=f'{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent', overwrite=True)
        else:
            print("Using python torf to generate the torrent")
            torrent = GGBOTTorrent(media,
                              trackers=announce,
                              source=source,
                              comment="Torrent created by GG-Bot Upload Assistant",
                              created_by="GG-Bot Upload Assistant",
                              exclude_globs=["*.txt", "*.jpg", "*.png", "*.nfo", "*.svf", "*.rar", "*.screens", "*.sfv"],
                              private=True,
                              creation_date=datetime.now())
            torrent.piece_size = calculate_piece_size(torrent.size)
            logging.info(f'[DotTorrentGeneration] Size of the torrent: {torrent.size}')
            logging.info(f'[DotTorrentGeneration] Piece Size of the torrent: {torrent.piece_size}')

            torrent.generate(callback=callback_progress)
            torrent.write(f'{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent')
            torrent.verify_filesize(media)
            logging.info("[DotTorrentGeneration] Trying to write into {}".format("[" + source + "]" + torrent_title + ".torrent"))
    else:
        print("Editing previous .torrent file to work with {} instead of generating a new one".format(source))
        logging.info("[DotTorrentGeneration] Editing previous .torrent file to work with {} instead of generating a new one".format(source))

        # just choose whichever, doesn't really matter since we replace the same info anyways
        edit_torrent = GGBOTTorrent.read(torrent)

        if len(announce) == 1:
            logging.debug(f"[DotTorrentGeneration] Only one announce url provided for tracker {tracker}.")
            logging.debug("[DotTorrentGeneration] Removing announce-list if present in existing torrent.")
            edit_torrent.metainfo.pop('announce-list', "")
        else:
            logging.debug(f"[DotTorrentGeneration] Multiple announce urls provided for tracker {tracker}. Updating announce-list")
            edit_torrent.metainfo.pop('announce-list', "")
            edit_torrent.metainfo['announce-list'] = list()
            for announce_url in announce:
                logging.debug(f"[DotTorrentGeneration] Adding secondary announce url {announce_url}")
                announce_list = list()
                announce_list.append(announce_url)
                edit_torrent.metainfo['announce-list'].append(announce_list)
            logging.debug(f"[DotTorrentGeneration] Final announce-list in torrent metadata {edit_torrent.metainfo['announce-list']}")

        edit_torrent.metainfo['announce'] = announce[0]
        edit_torrent.metainfo['info']['source'] = source
        # Edit the previous .torrent and save it as a new copy
        GGBOTTorrent.copy(edit_torrent).write(filepath=f'{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent', overwrite=True)

    if os.path.isfile(f'{working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent'):
        logging.info(f'[DotTorrentGeneration] Successfully created the following file: {working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent')
    else:
        logging.error(f'[DotTorrentGeneration] The following .torrent file was not created: {working_folder}/temp_upload/{hash_prefix}{tracker}-{torrent_title}.torrent')
