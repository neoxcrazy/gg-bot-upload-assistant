from utilities.utils import write_file_contents_to_log_as_debug
import os
import re
import shutil
import logging
import subprocess

from rich import box
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def bdinfo_validate_bdinfo_script_for_bare_metal(bdinfo_script):
    # Verify that the bdinfo script exists only when executed on bare metal / VM instead of container
    # The containerized version has bdinfo packed inside.
    if not os.getenv("IS_CONTAINERIZED") == "true" and not os.path.isfile(bdinfo_script):
        logging.critical(
            "[BDInfoUtils] You've specified the '-disc' arg but have not supplied a valid bdinfo script path in config.env")
        logging.info(
            "[BDInfoUtils] Can not upload a raw disc without bdinfo output, update the 'bdinfo_script' path in config.env")
        raise AssertionError(
            f"The bdinfo script you specified: ({bdinfo_script}) does not exist")


def bdinfo_validate_presence_of_bdmv_stream(upload_media):
    if not os.path.exists(f'{upload_media}BDMV/STREAM/'):
        logging.critical(
            "[BDInfoUtils] BD folder not recognized. We can only upload if we detect a '/BDMV/STREAM/' folder")
        raise AssertionError(
            "Currently unable to upload .iso files or disc/folders that does not contain a '/BDMV/STREAM/' folder")


def bdinfo_get_video_codec_from_bdinfo(bdinfo):
    """
        Method to get the video_codec information from the bdinfo.
        The method also checks for the presence of DV layer and any HDR formats.
        The return value is (DV, HDR, VIDEO_CODEC)
    """
    dv = None
    hdr = None
    # for full disks here we identify the video_codec, hdr and dv informations
    for index, video_track in enumerate(bdinfo['video']):
        if "dv_hdr" in video_track and len(video_track["dv_hdr"]) != 0:
            # so hdr or DV is present in this track. next we need to identify which one it is
            logging.debug(
                f"[BDInfoUtils] Detected {video_track['dv_hdr']} from bdinfo in track {index}")
            if "DOLBY" in video_track["dv_hdr"].upper() or "DOLBY VISION" in video_track["dv_hdr"].upper():
                dv = "DV"
            else:
                hdr = video_track["dv_hdr"].strip()
                if "HDR10+" in hdr:
                    hdr = "HDR10+"
                elif "HDR10" in hdr:
                    hdr = "HDR"
                logging.debug(
                    f'[BDInfoUtils] Adding proper HDR Format `{hdr}` to torrent info')
    logging.info(
        f"[BDInfoUtils] `video_codec` identifed from bdinfo as {bdinfo['video'][0]['codec']}")
    # video codec is taken from the first track
    return dv, hdr, bdinfo["video"][0]["codec"]


def bdinfo_get_audio_codec_from_bdinfo(bdinfo, audio_codec_dict):
    """
        Method to get the audio_codec information from the bdinfo.
        The method also checks for the presence of atmos in the audio
        The return value is (ATMOS, AUDIO_CODEC)
    """
    # here we populate the audio_codec and atmos information from bdinfo
    atmos = None
    for audio_track in bdinfo['audio']:
        if "atmos" in audio_track and len(audio_track["atmos"]) != 0:
            logging.info(
                f"[BDInfoUtils] `atmos` identifed from bdinfo as {audio_track['atmos']}")
            atmos = "Atmos"
            break

    logging.info(
        f"[BDInfoUtils] `audio_codec` identifed from bdinfo as {bdinfo['audio'][0]['codec']}")
    for key in audio_codec_dict.keys():
        if str(bdinfo["audio"][0]["codec"].strip()) == key:
            logging.info(
                f'[BDInfoUtils] Used (audio_codec_dict + BDInfo) to identify the audio codec: {audio_codec_dict[bdinfo["audio"][0]["codec"].strip()]}')
            return atmos, audio_codec_dict[bdinfo["audio"][0]["codec"].strip()]
    logging.error(
        f"[BDInfoUtils] Failed to identify audio_codec from audio_codec_dict + BDInfo. Audio Codec from BDInfo {bdinfo['audio'][0]['codec']}")
    return None, None


def bdinfo_get_audio_channels_from_bdinfo(bdinfo):
    # Here we iterate over all the audio track identified and returns the largest channel.
    # 7.1 > 5.1 > 2.0
    # presently the subwoofer channel is not considered
    # if 2.1 and 2.0 tracks are present and we encounter 2.0 first followed by 2.1,
    # we return 2.0 only.
    # # TODO check whether subwoofer or even atmos channels needs to be considered
    audio_channel = None
    for audio_track in bdinfo['audio']:
        if audio_channel is None:
            audio_channel = audio_track["channels"]
        elif int(audio_track["channels"][0:1]) > int(audio_channel[0:1]):
            audio_channel = audio_track["channels"]
    logging.info(
        f"[BDInfoUtils] `audio_channels` identifed from bdinfo as {audio_channel}")
    return audio_channel


def bdinfo_get_largest_playlist(bdinfo_script, auto_mode, upload_media):
    bd_max_size = 0
    bd_max_file = ""  # file with the largest size inside the STEAM folder

    for folder, subfolders, files in os.walk(f'{upload_media}BDMV/STREAM/'):
        # checking the size of each file
        for bd_file in files:
            size = os.stat(os.path.join(folder, bd_file)).st_size
            # updating maximum size
            if size > bd_max_size:
                bd_max_size = size
                bd_max_file = os.path.join(folder, bd_file)

    bdinfo_output_split = str(' '.join(str(subprocess.check_output(
        [bdinfo_script, upload_media, "-l"])).split())).split(' ')
    logging.debug(
        f"[BDInfoUtils] BDInfo output split from of list command: ---{bdinfo_output_split}--- ")
    all_mpls_playlists = re.findall(
        r'\d\d\d\d\d\.MPLS', str(bdinfo_output_split))

    dict_of_playlist_length_size = {}
    dict_of_playlist_info_list = []  # list of dict
    # Still identifying the largest playlist here...
    for index, mpls_playlist in enumerate(bdinfo_output_split):
        if mpls_playlist in all_mpls_playlists:
            playlist_details = {}
            playlist_details["no"] = bdinfo_output_split[index -
                                                         2].replace("\\n", "")
            playlist_details["group"] = bdinfo_output_split[index - 1]
            playlist_details["file"] = bdinfo_output_split[index]
            playlist_details["length"] = bdinfo_output_split[index + 1]
            playlist_details["est_bytes"] = bdinfo_output_split[index + 2]
            playlist_details["msr_bytes"] = bdinfo_output_split[index + 3]
            playlist_details["size"] = int(
                str(bdinfo_output_split[index + 2]).replace(",", ""))
            dict_of_playlist_info_list.append(playlist_details)
            dict_of_playlist_length_size[mpls_playlist] = int(
                str(bdinfo_output_split[index + 2]).replace(",", ""))

    # sorting list based on the `size` key inside the dictionary
    dict_of_playlist_info_list = sorted(
        dict_of_playlist_info_list, key=lambda d: [d["size"]], reverse=True)

    # In auto_mode we just choose the largest playlist
    if auto_mode == 'false':
        # here we display the playlists identified ordered in decending order by size
        # the default choice will be the largest playlist file
        # user will be given the option to choose any different playlist file
        bdinfo_list_table = Table(
            box=box.SQUARE, title='BDInfo Playlists', title_style='bold #be58bf')
        bdinfo_list_table.add_column(
            "Playlist #", justify="center", style='#38ACEC')
        bdinfo_list_table.add_column(
            "Group", justify="center", style='#38ACEC')
        bdinfo_list_table.add_column(
            "Playlist File", justify="center", style='#38ACEC')
        bdinfo_list_table.add_column(
            "Duration", justify="center", style='#38ACEC')
        bdinfo_list_table.add_column(
            "Estimated Bytes", justify="center", style='#38ACEC')
        # bdinfo_list_table.add_column("Measured Bytes", justify="center", style='#38ACEC') # always `-` in the tested BDs

        for playlist_details in dict_of_playlist_info_list:
            bdinfo_list_table.add_row(str(playlist_details['no']), playlist_details['group'], f"[chartreuse1][bold]{str(playlist_details['file'])}[/bold][/chartreuse1]",
                                      playlist_details['length'], playlist_details['est_bytes'], end_section=True)

        console.print(
            "For BluRay disk you need to select which playlist need to be analyzed, by default the largest playlist will be selected\n", style='bold blue')
        console.print("")
        console.print(bdinfo_list_table)

        list_of_num = []
        for i in range(len(dict_of_playlist_info_list)):
            i += 1
            list_of_num.append(str(i))

        user_input_playlist_id_num = Prompt.ask(
            "Choose which `Playlist #` to analyze:", choices=list_of_num, default="1")
        largest_playlist = dict_of_playlist_info_list[int(
            user_input_playlist_id_num) - 1]["file"]
        logging.debug(
            f"[BDInfoUtils] Used decided to select the playlist [{largest_playlist}] with Playlist # [{user_input_playlist_id_num}]")
        logging.info(
            f"[BDInfoUtils] Largest playlist obtained from bluray disc: {largest_playlist}")
        return bd_max_file, largest_playlist
    else:
        largest_playlist_value = max(dict_of_playlist_length_size.values())
        largest_playlist = list(dict_of_playlist_length_size.keys())[list(
            dict_of_playlist_length_size.values()).index(largest_playlist_value)]
        logging.info(
            f"[BDInfoUtils] Largest playlist obtained from bluray disc: {largest_playlist}")
        return bd_max_file, largest_playlist


def bdinfo_generate_and_parse_bdinfo(bdinfo_script, torrent_info, debug):
    """
        Method generates the BDInfo for the full disk and writes to the mediainfo.txt file.
        Once it has been generated the generated BDInfo is parsed using the `parse_bdinfo` method 
        and result is saved in `torrent_info` as `bdinfo`

        It also sets the `mediainfo` key in torrent_info
    """
    # if largest_playlist is already in torrent_info, then why this computation again???
    # Get the BDInfo, parse & save it all into a file called mediainfo.txt (filename doesn't really matter, it gets uploaded to the same place anyways)
    logging.debug(
        f"[BDInfoUtils] `largest_playlist` and `upload_media` from torrent_info :: {torrent_info['largest_playlist']} --- {torrent_info['upload_media']}")
    subprocess.run([bdinfo_script, torrent_info["upload_media"],
                   "--mpls=" + torrent_info['largest_playlist']])

    shutil.move(
        f'{torrent_info["upload_media"]}BDINFO.{torrent_info["raw_file_name"]}.txt', torrent_info["mediainfo"])
    # TODO remove the below sed part
    # if os.path.isfile("/usr/bin/sed"):
    #     sed_path = "/usr/bin/sed"
    # else:
    #     sed_path = "/bin/sed"
    # os.system(f"{sed_path} -i '0,/<---- END FORUMS PASTE ---->/d' {torrent_info['mediainfo']}")
    # displaying bdinfo to log in debug mode
    if debug:
        logging.debug(
            "[BDInfoUtils] ::::::::::::::::::::::::::::: Dumping the BDInfo Quick Summary :::::::::::::::::::::::::::::")
        write_file_contents_to_log_as_debug(torrent_info["mediainfo"])
    return parse_bdinfo(torrent_info["mediainfo"])


def parse_bdinfo(bdinfo_location):
    # TODO add support for .iso extraction
    # TODO add support for 3D bluray disks
    """
        Attributes in returned bdinfo
        -----KEY------------DESCRIPTION-----------------------------EXAMPLE VALUE----------
            playlist: playlist being parsed                     : 00001.MPL
            size    : size of the disk                          : 54.597935752011836
            length  : duration of playback                      : 1:37:17
            title   : title of the disk                         : Venom: Let There Be Carnage - 4K Ultra HD
            label   : label of the disk                         : Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
            video   : {
                "codec"         : video codec                   : MPEG-H HEVC Video
                "bitrate"       : the video bitrate             : 55873 kbps
                "resolution"    : the resolution of the video   : 2160p
                "fps"           : the fps                       : 23.976 fps
                "aspect_ratio"  : the aspect ratio              : 16:9
                "profile"       : the video profile             : Main 10 @ Level 5.1 @ High
                "bit_depth"     : the bit depth                 : 10 bits
                "dv_hdr"        : DV or HDR (if present)        : HDR10
                "color"         : the color parameter           : BT.2020
            }
            audio   : {
                "language"      : the audio language            : English
                "codec"         : the audio codec               : Dolby TrueHD
                "channels"      : the audo channels             : 7.1
                "sample_rate"   : the sample rate               : 48 kHz
                "bitrate"       : the average bit rate          : 4291 kbps
                "bit_depth"     : the bit depth of the audio    : 24-bit
                "atmos"         : whether atmos is present      : Atmos Audio
            }
    """
    bdinfo = dict()
    bdinfo['video'] = list()
    bdinfo['audio'] = list()
    with open(bdinfo_location, 'r') as file_contents:
        lines = file_contents.readlines()
        for line in lines:
            line = line.strip()
            line = line.replace(
                "*", "").strip() if line.startswith("*") else line
            # Playlist: 00001.MPLS              ==> 00001.MPLS
            if line.startswith("Playlist:"):
                bdinfo['playlist'] = line.split(':', 1)[1].strip()
            # Disc Size: 58,624,087,121 bytes   ==> 54.597935752011836
            elif line.startswith("Disc Size:"):
                size = line.split(':', 1)[1].replace(
                    "bytes", "").replace(",", "")
                size = float(size)/float(1 << 30)
                bdinfo['size'] = size
            # Length: 1:37:17.831               ==> 1:37:17
            elif line.startswith("Length:"):
                bdinfo['length'] = line.split(
                    ':', 1)[1].split('.', 1)[0].strip()
            elif line.startswith("Video:"):
                """
                    video_components: examples [video_components_dict is the mapping of these components and their indexes]
                    MPEG-H HEVC Video / 55873 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-H HEVC Video / 2104 kbps / 1080p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / Dolby Vision / BT.2020
                    MPEG-H HEVC Video / 35033 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-4 AVC Video / 34754 kbps / 1080p / 23.976 fps / 16:9 / High Profile 4.1
                """
                video_components_dict = {
                    0: "codec",
                    1: "bitrate",
                    2: "resolution",
                    3: "fps",
                    4: "aspect_ratio",
                    5: "profile",
                    6: "bit_depth",
                    7: "dv_hdr",
                    8: "color",
                }
                video_components = line.split(':', 1)[1].split('/')
                video_metadata = {}
                for loop_variable in range(0, len(video_components)):
                    video_metadata[video_components_dict[loop_variable]
                                   ] = video_components[loop_variable].strip()

                if "HEVC" in video_metadata["codec"]:
                    video_metadata["codec"] = "HEVC"
                elif "AVC" in video_metadata["codec"]:
                    video_metadata["codec"] = "AVC"

                bdinfo["video"].append(video_metadata)
            elif line.startswith("Audio:"):
                """
                    audio_components: examples 
                    English / Dolby TrueHD/Atmos Audio / 7.1 / 48 kHz /  4291 kbps / 24-bit (AC3 Embedded: 5.1 / 48 kHz /   640 kbps / DN -31dB)
                    English / DTS-HD Master Audio / 7.1 / 48 kHz /  5002 kbps / 24-bit (DTS Core: 5.1 / 48 kHz /  1509 kbps / 24-bit)
                    English / Dolby Digital Audio / 5.1 / 48 kHz /   448 kbps / DN -31dB
                    English / DTS Audio / 5.1 / 48 kHz /   768 kbps / 24-bit
                """
                audio_components_dict = {
                    0: "language",
                    1: "codec",  # atmos => added if present optionally
                    2: "channels",
                    3: "sample_rate",
                    4: "bitrate",
                    5: "bit_depth"
                }
                if "(" in line:
                    # removing the contents inside bracket
                    line = line.split("(")[0]
                audio_components = line.split(':', 1)[1].split(
                    '/ ')  # not so sure about this /{space}
                audio_metadata = {}
                for loop_variable in range(0, len(audio_components)):
                    # identifying and tagging atmos audio
                    if "Atmos" in audio_components[loop_variable]:
                        codec_split = audio_components[loop_variable].split(
                            "/")
                        audio_metadata["atmos"] = codec_split[1].strip()
                        audio_components[loop_variable] = codec_split[0].strip()

                    audio_metadata[audio_components_dict[loop_variable]
                                   ] = audio_components[loop_variable].strip()
                bdinfo["audio"].append(audio_metadata)
            # Disc Title: Venom: Let There Be Carnage - 4K Ultra HD
            elif line.startswith("Disc Title:"):
                bdinfo['title'] = line.split(':', 1)[1].strip()
            # Disc Label: Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
            elif line.startswith("Disc Label:"):
                bdinfo['label'] = line.split(':', 1)[1].strip()
    return bdinfo
