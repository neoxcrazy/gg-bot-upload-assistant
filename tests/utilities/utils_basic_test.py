import pytest
import datetime

from pathlib import Path
from pymediainfo import MediaInfo
from utilities.utils_basic import *


working_folder = Path(__file__).resolve().parent.parent.parent


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
    return MediaInfo(open(raw_file_name, encoding="utf-8").read()).tracks[1]

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
            __get_media_info_video_track(f"{working_folder}/tests/resources/Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.xml"), 
            False, # force pymediainfo
            (None, "PQ10", "H.265"), id="PQ10_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Monsters.at.Work.S01E10.Its.Laughter.Theyre.After.2160p.WEB-DL.DDP5.1.HDR.H.265-FLUX.xml"), 
            True, # force pymediainfo
            (None, "PQ10", "x265"), id="PQ10_x265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"), 
            False, # force pymediainfo
            ("DV", "HDR10+", "HEVC"), id="DV_HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/The.Great.S02E10.Wedding.2160p.HULU.WEB-DL.DDP5.1.DV.HEVC-NOSiViD.xml"), 
            True, # force pymediainfo
            ("DV", "HDR10+", "H.265"), id="DV_HDR10+_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.xml"), 
            False, # force pymediainfo
            (None, "HDR10+", "HEVC"), id="HDR10+_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Why.Women.Kill.S02E10.The.Lady.Confesses.2160p.WEB-DL.DD5.1.HDR.HEVC-TEPES.xml"), 
            True, # force pymediainfo
            (None, "HDR10+", "H.265"), id="HDR10+_HEVC_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.xml"), 
            False, # force pymediainfo
            ("DV", None, "HEVC"), id="DV_HEVC"
        ),
        pytest.param(
            __get_torrent_info(None, "What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/What.If.2021.S01E01.What.If.Captain.Carter.Were.The.First.Avenger.REPACK.2160p.WEB-DL.DDP5.1.Atmos.DV.HEVC-FLUX.xml"), 
            True, # force pymediainfo
            ("DV", None, "H.265"), id="DV_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/1883.S01E01.1883.2160p.WEB-DL.DDP5.1.H.265-NTb.xml"), 
            False, # force pymediainfo
            (None, None, "H.265"), id="H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"), 
            False, # force pymediainfo
            (None, "HDR", "HEVC"), id="HDR_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Arcane.S01E01.Welcome.to.the.Playground.1080p.NF.WEB-DL.DDP5.1.HDR.HEVC-TEPES.xml"), 
            True, # force pymediainfo
            (None, "HDR", "H.265"), id="HDR_H.265_pymediainfo"
        ),
        pytest.param(
            __get_torrent_info(None, "Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Dragon.Booster.S01E01.The.Choosing.Part.1.AMZN.WEB-DL.DDP2.0.H.264-DRAGONE.xml"), 
            False, # force pymediainfo
            (None, None, "H.264"), id="H.264"
        ),
        pytest.param(
            __get_torrent_info(None, "Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.mkv", "Web"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Peaky.Blinders.S06E01.Black.Day.2160p.iP.WEB-DL.DDP5.1.HLG.H.265-FLUX.xml"), 
            False, # force pymediainfo
            (None, "HLG", "H.265"), id="HLG_H.265"
        ),
        pytest.param(
            __get_torrent_info(None, "Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.mkv", "BluRay"), 
            False, # is_disc
            __get_media_info_video_track(f"{working_folder}/tests/resources/Venom.Let.There.Be.Carnage.2021.2160p.UHD.BluRay.REMUX.DV.HDR.HEVC.Atmos-TRiToN.xml"), 
            False, # force pymediainfo
            ("DV", "HDR", "HEVC"), id="DV_HDR10_H.265"
        ),
    ]
)
def test_basic_get_missing_video_codec(torrent_info, is_disc, media_info_video_track, force_pymediainfo, expected):
    assert basic_get_missing_video_codec(torrent_info, is_disc, "false", media_info_video_track, force_pymediainfo) == expected
