import pytest
import datetime

from utilities.utils_basic import *

class MediaInfoVideoTrack:
    
    def __init__(self, type):
        if type == "HDR10__H.265":
            self.source = "Web"
            self.raw_file_name = "Tehran.S02E03.PTSD.2160p.ATVP.WEB-DL.DDP5.1.HDR.H.265-NTb.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = None
            self.hdr_format = "SMPTE ST 2086"
            self.hdr_format_version = None
            self.hdr_format_compatibility = "HDR10"
            self.transfer_characteristics = "PQ"
            self.transfer_characteristics_original = None
        elif type == "HDR10+__H.265":
            self.source = "Web"
            self.raw_file_name = "Kajillionaire.2020.2160p.AMZN.WEB-DL.DDP.5.1.HDR10Plus.HEVC-MiON.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = None
            self.hdr_format = "SMPTE ST 2094 App 4"
            self.hdr_format_version = "1"
            self.hdr_format_compatibility = "HDR10+ Profile B"
            self.transfer_characteristics = "PQ"
            self.transfer_characteristics_original = None
        elif type == "DV__HDR10__HEVC":
            self.source = "BluRay"
            self.raw_file_name = "Ford.v.Ferrari.2019.UHD.BluRay.2160p.TrueHD.Atmos.7.1.DV.HEVC.HYBRID.REMUX-FraMeSToR.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = "ATEME Titan File 3.9.0 (4.9.0.0)"
            self.hdr_format = "Dolby Vision, Version 1.0, dvhe.08.06, BL+RPU"
            self.hdr_format_version = None
            self.hdr_format_compatibility = "HDR10 / SMPTE ST 2086, HDR10"
            self.transfer_characteristics = "PQ"
            self.transfer_characteristics_original = None
        elif type == "DV__HDR10+__HEVC":
            self.source = "Web"
            self.raw_file_name = "Candy.S01E01.Friday.the.13th.2160p.HULU.WEB-DL.DDP.5.1.DV.HDR10Plus.HEVC-MiON.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = None
            self.hdr_format = "Dolby Vision, Version 1.0, dvhe.08.06, BL+RPU"
            self.hdr_format_version = None
            self.hdr_format_compatibility = "HDR10 compatible / SMPTE ST 2094 App 4, Version 1, HDR10+ Profile B compatible"
            self.transfer_characteristics = "PQ"
            self.transfer_characteristics_original = None
        elif type == "PQ10__H.265":
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = "x265 3.5:[Linux][GCC 9.4.0][64 bit] 10bit"
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = "PQ"
            self.transfer_characteristics_original = None
        elif type == "HLG__H.265":
            self.source = "Web"
            self.raw_file_name = "Dynasties.S02E01.Puma.2160p.iP.WEB-DL.AAC2.0.HLG.H.265-playWEB.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = None
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = "BT.2020 (10-bit)"
            self.transfer_characteristics_original = "HLG / BT.2020 (10-bit)"
        elif type == "WCG__HEVC":
            self.source = "BluRay"
            self.raw_file_name = "Evangelion.3.33.You.Can.Not.Redo.2012.REPACK.UHD.BluRay.2160p.DTS-HD.MA.5.1.HEVC.REMUX-FraMeSToR.mkv"
            self.format = "HEVC"
            self.color_primaries = "BT.2020"
            self.writing_library = None
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = "BT.2020 (10-bit)"
            self.transfer_characteristics_original = None
        elif type == "H.264":
            self.source = "Web"
            self.raw_file_name = "Alyam.alyam.1978.720p.WEB-DL.AAC2.0.x264-KG.mkv"
            self.format = "AVC"
            self.color_primaries = None
            self.writing_library = "x264 core 142"
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = None
            self.transfer_characteristics_original = None
        elif type == "H.265":
            self.source = "Web"
            self.raw_file_name = "Conversations.with.Friends.S01E01.2160p.HULU.WEB-DL.DDP.5.1.HEVC-MiON.mkv"
            self.format = "HEVC"
            self.color_primaries = None
            self.writing_library = None
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = None
            self.transfer_characteristics_original = None
        else:
            self.raw_file_name = None
            self.format = None
            self.color_primaries = None
            self.writing_library = None
            self.hdr_format = None
            self.hdr_format_version = None
            self.hdr_format_compatibility = None
            self.transfer_characteristics = None
            self.transfer_characteristics_original = None

    def to_data():
        return ""


@pytest.mark.parametrize(
    ("input", "expected"),
    # expected values format [ s00e00, season_number, episode_number, complete_season, individual_episodes, daily_episodes ]
    (
        pytest.param(
            {
                "season": 1, 
                "episode": 1
            }, 
            ("S01E01", "1", "1", "0", "1", "0" ), id="single_episode"),
        pytest.param(
            {
                "season": 1 
            }, 
            ( "S01", "1", "0", "1", "0", "0" ), id="season_pack"),
        pytest.param(
            {
                "season": 1,
                "episode": [9, 10]
            }, 
            ( "S01E09E10", "1", "9", "0", "1", "0" ), id="multi_episode_release"),
        pytest.param(
            {
                "date": datetime.date(2022, 4, 12)
            }, 
            ( "2022-04-12", "0", "0", "0", "0", "1" ), id="daily_episode")
    )
)
def test_basic_get_episode_basic_details(input, expected):
    assert basic_get_episode_basic_details(input) == expected


def __get_torrent_info(bdinfo, raw_file_name, source):
    torrent_info = {}
    torrent_info["bdinfo"] = bdinfo
    torrent_info["raw_file_name"] = raw_file_name
    if source is not None: # source will either have a value, or the key itself won't be present
        torrent_info["source"] = source
    return torrent_info


"""
    
    "HDR10+__H.265"
    "DV__HDR10__HEVC"
    "DV__HDR10+__HEVC"
    "PQ10__H.265"
    "HLG__H.265"
    "WCG__H.265"
    "H.264"
    "H.265"
"""
@pytest.mark.parametrize(
    ("torrent_info", "is_disc", "media_info_video_track", "force_pymediainfo", "expected"),
    # expected format (dv, hdr, video_codec)
    [
        (
            __get_torrent_info(None, MediaInfoVideoTrack("HDR10__H.265").raw_file_name, MediaInfoVideoTrack("HDR10__H.265").source), 
            False, 
            MediaInfoVideoTrack("HDR10__H.265"), 
            False, 
            (None, "HDR", "H.265")
        )
    ]
)
def test_basic_get_missing_video_codec(torrent_info, is_disc, media_info_video_track, force_pymediainfo, expected):
    assert basic_get_missing_video_codec(torrent_info, is_disc, "false", media_info_video_track, force_pymediainfo) == expected
