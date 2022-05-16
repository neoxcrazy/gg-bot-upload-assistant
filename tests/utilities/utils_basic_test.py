import pytest
import datetime

from pathlib import Path
from pprint import pformat
from pymediainfo import MediaInfo
from utilities.utils_basic import *


working_folder = Path(__file__).resolve().parent.parent.parent
mediainfo_xml = "/tests/resources/mediainfo/xml/"
mediainfo_summary = "/tests/resources/mediainfo/summary/"

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


def __get_media_info_video_track(raw_file_name):
    return MediaInfo(__get_file_contents(raw_file_name)).tracks[1]


def __get_media_info_data(raw_file_name):
    return MediaInfo(__get_file_contents(raw_file_name)).to_data()


def __get_file_contents(raw_file_name):
    return open(raw_file_name, encoding="utf-8").read()


"""
    Mediainfo Available
        H.264
        H.265
        DV -> H.265
        DV -> HDR10+ -> H.265
        DV -> HDR10 -> HEVC
        HDR -> H.265
        PQ10 -> H.265
        HDR10+ -> H.265
        HLG -> H.265

    Missing:
        "WCG__H.265"
"""
@pytest.mark.parametrize(
    ("torrent_info", "is_disc", "media_info_video_track", "force_pymediainfo", "expected"),
    # expected format (dv, hdr, video_codec)
    [
        pytest.param(
            __get_torrent_info(None, "Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.xml"), 
            False, # force pymediainfo
            (None, "PQ10", "H.265"), id="PQ10_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.xml"), 
            True, # force pymediainfo
            (None, "PQ10", "x265"), id="PQ10_x265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"), 
            False, # force pymediainfo
            ("DV", "HDR10+", "HEVC"), id="DV_HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"), 
            True, # force pymediainfo
            ("DV", "HDR10+", "H.265"), id="DV_HDR10+_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.xml"), 
            False, # force pymediainfo
            (None, "HDR10+", "HEVC"), id="HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.xml"), 
            True, # force pymediainfo
            (None, "HDR10+", "H.265"), id="HDR10+_HEVC_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.xml"), 
            False, # force pymediainfo
            ("DV", None, "HEVC"), id="DV_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.xml"), 
            True, # force pymediainfo
            ("DV", None, "H.265"), id="DV_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.xml"), 
            False, # force pymediainfo
            (None, None, "H.265"), id="H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"), 
            False, # force pymediainfo
            (None, "HDR", "HEVC"), id="HDR_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"), 
            True, # force pymediainfo
            (None, "HDR", "H.265"), id="HDR_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"), 
            False, # force pymediainfo
            (None, None, "H.264"), id="H.264"
        ),
        pytest.param(
            __get_torrent_info(None, "Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.xml"), 
            False, # force pymediainfo
            (None, "HLG", "H.265"), id="HLG_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.mkv", "BluRay"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"), 
            False, # force pymediainfo
            ("DV", "HDR", "HEVC"), id="DV_HDR10_H.265"
        ),
    ]
)
def test_basic_get_missing_video_codec(torrent_info, is_disc, media_info_video_track, force_pymediainfo, expected):
    assert basic_get_missing_video_codec(torrent_info, is_disc, "false", media_info_video_track, force_pymediainfo) == expected


@pytest.mark.parametrize(
    ("torrent_info", "is_disc", "media_info_video_track", "expected"),
    # TODO add test for 480p, 1080i etc
    [
        pytest.param(
            __get_torrent_info(None, "Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.mkv", None),
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"), 
            "2160p" , id="resolution_2160p"
        ),
        pytest.param(
            __get_torrent_info(None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", None), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"), 
            "1080p", id="resolution_1080p"
        ),
        pytest.param(
            __get_torrent_info(None, "Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.mkv", None), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"), 
            "576p", id="resolution_576p"
        ),
    ]
)
def test_basic_get_missing_screen_size(torrent_info, is_disc, media_info_video_track, expected):
    assert basic_get_missing_screen_size(torrent_info, is_disc, media_info_video_track, "false", "screen_size") == expected


@pytest.mark.parametrize(
    ("media_info_result", "expected"),
    [
        pytest.param(
            __get_media_info_data(f"{working_folder}{mediainfo_xml}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"),
            (__get_file_contents(f"{working_folder}{mediainfo_summary}Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.summary"), "0", "0", "0"),
            id="summary_without_id"
        ),
        pytest.param(
            __get_media_info_data(f"{working_folder}{mediainfo_xml}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"),
            (__get_file_contents(f"{working_folder}{mediainfo_summary}Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.summary"), "movie/580489", "tt7097896", "0"),
            id="summary_with_imdb_tmdb_movie"
        ),
        pytest.param(
            __get_media_info_data(f"{working_folder}{mediainfo_xml}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.xml"),
            (__get_file_contents(f"{working_folder}{mediainfo_summary}Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.summary"), "tv/60574", "tt2442560", "0"),
            id="summary_with_imdb_tmdb_tv"
        ),
        pytest.param(
            __get_media_info_data(f"{working_folder}{mediainfo_xml}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"),
            (__get_file_contents(f"{working_folder}{mediainfo_summary}The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.summary"), "tv/93812", "tt2235759", "369301"),
            id="summary_with_imdb_tmdb__tvdb"
        ),
    ]
)
def test_basic_get_mediainfo_summary(media_info_result, expected):
    assert basic_get_mediainfo_summary(media_info_result) == expected