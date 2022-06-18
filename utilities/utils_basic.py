import re
import os
import sys
import glob
import json
import time
import logging

from ffmpy import FFprobe
from pprint import pformat
from pymediainfo import MediaInfo

from rich.console import Console
from rich.prompt import Prompt, Confirm

from utilities.utils_bdinfo import *

console = Console()


def quit_log_reason(reason, missing_value):
    logging.critical(f"[BasicUtils] auto_mode is enabled (no user input) & we can not auto extract the {missing_value}")
    logging.critical(f"[BasicUtils] Exit Reason: {reason}")
    # let the user know the error/issue
    console.print(f"\nCritical error when trying to extract: {missing_value}", style='red bold')
    console.print(f"Exit Reason: {reason}")
    # and finally exit since this will affect all trackers we try and upload to, so it makes no sense to try the next tracker
    sys.exit() # TODO handle this somehow for the re uploader without stopping the program


def _get_dv_hdr(media_info_video_track):
    hdr = None
    dv = None
    try:
        logging.debug(f"[BasicUtils] Logging video track atrtibutes used to detect HDR type")
        logging.debug(f"[BasicUtils] Video track info from mediainfo \n {pformat(media_info_video_track.to_data())}")
        color_primaries = media_info_video_track.color_primaries
        if color_primaries is not None and color_primaries in ("BT.2020", "REC.2020"):
            hdr_format = f"{media_info_video_track.hdr_format}, {media_info_video_track.hdr_format_version}, {media_info_video_track.hdr_format_compatibility}"
            if "HDR10" in hdr_format:
                hdr = "HDR"
            
            if "HDR10+" in hdr_format:
                hdr = "HDR10+"
            elif media_info_video_track.hdr_format is None and "PQ" in (media_info_video_track.transfer_characteristics, media_info_video_track.transfer_characteristics_original):
                hdr = "PQ10"
            
            if media_info_video_track.transfer_characteristics_original is not None and "HLG" in media_info_video_track.transfer_characteristics_original:
                hdr = "HLG"
            elif media_info_video_track.transfer_characteristics_original is not None and "BT.2020 (10-bit)" in media_info_video_track.transfer_characteristics_original:
                hdr = "WCG"
    except Exception as e:
        logging.exception(f"[BasicUtils] Error occured while trying to parse HDR information from mediainfo.", e)
    
    if media_info_video_track.hdr_format is not None and "Dolby Vision" in media_info_video_track.hdr_format:
        dv = "DV"
        logging.info("[BasicUtils] Identified 'Dolby Vision' from mediainfo.")

    logging.info(f"[BasicUtils] HDR Format identified from mediainfo is '{hdr}'")
    return dv, hdr


def basic_get_missing_video_codec(torrent_info, is_disc, auto_mode, media_info_video_track, force_pymediainfo):
    """
        along with video_codec extraction the HDR format and DV is also updated from here.
        Steps:
        get Color primaries from MediaInfo
        if it is one of "BT.2020", "REC.2020" then
            if HDR10 is present in HDR Format then 
                HDR = HDR
            if HDR10+ is present in HDR Format then 
                HDR = HDR10+
            confirm the HDRFormat doesn't exist in the media info 
            check whether its PQ is present in Transfer characteristics or transfer_characteristics_Original from MediaInfo 
                HDR = PQ10 
            get transfer_characteristics_Original from media info
            if HLG is present in that then 
                HDR = HLG
            else if "BT.2020 (10-bit)" is present then 
                HDR = WCG
        
        if Dolby Vision is present in HDR Format then mark present of DV 

        Return value (dv, hdr, video_codec)
    """
    logging.debug(f"[BasicUtils] Dumping torrent_info before video_codec identification. {pformat(torrent_info)}")
    if is_disc and torrent_info["bdinfo"] is not None: 
        return bdinfo_get_video_codec_from_bdinfo(torrent_info["bdinfo"])
   
    dv, hdr = _get_dv_hdr(media_info_video_track)

    # First try to use our own Regex to extract it, if that fails then we can ues ffprobe/mediainfo
    filename_video_codec_regex = re.search(r'(?P<HEVC>HEVC)|(?P<AVC>AVC)|'
                                            r'(?P<H265>H(.265|265))|'
                                            r'(?P<H264>H(.264|264))|'
                                            r'(?P<x265>x265)|(?P<x264>x264)|'
                                            r'(?P<MPEG2>MPEG(-2|2))|'
                                            r'(?P<VC1>VC(-1|1))', torrent_info["raw_file_name"], re.IGNORECASE)
    regex_video_codec = None
    if filename_video_codec_regex is not None:
        rename_codec = {'VC1': 'VC-1', 'MPEG2': 'MPEG-2', 'H264': 'H.264', 'H265': 'H.265'}

        for video_codec in ["HEVC", "AVC", "H265", "H264", "x265", "x264", "MPEG2", "VC1"]:
            if filename_video_codec_regex.group(video_codec) is not None:
                # Now check to see if the 'codec' is in the rename_codec dict we created earlier
                if video_codec in rename_codec.keys():
                    regex_video_codec = rename_codec[video_codec]
                else:
                    # if this executes its AVC/HEVC or x265/x264
                    regex_video_codec = video_codec
        if "source" in torrent_info and torrent_info["source"] == "Web":
            if regex_video_codec == "HEVC":
                regex_video_codec = 'H.265'
            elif regex_video_codec == "AVC":
                regex_video_codec = 'H.264'

    # If the regex didn't work and the code has reached this point, we will now try pymediainfo
    # If video codec is HEVC then depending on the specific source (web, bluray, etc) we might need to format that differently
    if "HEVC" in media_info_video_track.format:
        # Removing the writing library based codec selection
        # if media_info_video_track.writing_library is not None:
        #     pymediainfo_video_codec = 'x265'
        # Possible video_codecs now are either H.265 or HEVC
        # If the source is WEB I think we should use H.265 & leave HEVC for bluray discs/remuxs (encodes would fall under x265)
        if "source" in torrent_info and torrent_info["source"] == "Web":
            pymediainfo_video_codec = 'H.265'
        # for everything else we can just default to 'HEVC' since it'll technically be accurate no matter what
        else:
            logging.info(f"[BasicUtils] Defaulting video_codec as HEVC because writing library is missing and source is {torrent_info['source']}")
            pymediainfo_video_codec = 'HEVC'
    # Now check and assign AVC based codecs
    elif "AVC" in media_info_video_track.format:
        if media_info_video_track.writing_library is not None:
            pymediainfo_video_codec = 'x264'
        # Possible video_codecs now are either H.264 or AVC
        # If the source is WEB we should use H.264 & leave AVC for bluray discs/remuxs (encodes would fall under x265)
        elif "source" in torrent_info and torrent_info["source"] == "Web":
            pymediainfo_video_codec = 'H.264'
        # for everything else we can just default to 'AVC' since it'll technically be accurate no matter what
        else:
            logging.info(f"[BasicUtils] Defaulting video_codec as AVC because writing library is missing and source is {torrent_info['source']}")
            pymediainfo_video_codec = 'AVC'
    # For anything else we'll just use whatever pymediainfo returned for 'format'
    else:
        pymediainfo_video_codec = media_info_video_track.format

    # Log it!
    logging.info(f"[BasicUtils] Regex identified the video_codec as: {regex_video_codec}")
    logging.info(f"[BasicUtils] Pymediainfo identified the video_codec as: {pymediainfo_video_codec}")
    if regex_video_codec != pymediainfo_video_codec:
        logging.error(f"[BasicUtils] Regex extracted video_codec [{regex_video_codec}] and pymediainfo extracted video_codec [{pymediainfo_video_codec}] doesn't match!!")
        logging.info(f"[BasicUtils] If `--force_pymediainfo` or `-fpm` is provided as argument, PyMediaInfo video_codec will be used, else regex extracted video_codec will be used")
        if force_pymediainfo:
            return dv, hdr, pymediainfo_video_codec

    logging.debug(f"[BasicUtils] Regex extracted video_codec [{regex_video_codec}] and pymediainfo extracted video_codec [{pymediainfo_video_codec}] matches")
    return dv, hdr, regex_video_codec


def basic_get_missing_audio_codec(torrent_info, is_disc, auto_mode, audio_codec_file_path, media_info_audio_track, parse_me, missing_value):
    """
        Returns (audio_codec, atmos)
    """
    # We store some common audio code translations in this dict
    audio_codec_dict = json.load(open(audio_codec_file_path))

    # TODO handle returning atmos from here
    if is_disc and torrent_info["bdinfo"] is not None:
        atmos, audio_codec = bdinfo_get_audio_codec_from_bdinfo(torrent_info['bdinfo'], audio_codec_dict)
        return audio_codec, atmos
    
    # First check to see if GuessIt inserted an audio_codec into torrent_info and if it did then we can verify its formatted correctly
    elif "audio_codec" in torrent_info:
        logging.debug(f"[BasicUtils] audio_codec is present in the torrent info [{torrent_info['audio_codec']}]. Trying to match it with audio_codec_dict")
        for key in audio_codec_dict.keys():
            if str(torrent_info["audio_codec"]) == key:
                logging.info(f'[BasicUtils] Used (audio_codec_dict + GuessIt) to identify the audio codec: {audio_codec_dict[torrent_info["audio_codec"]]}')
                return audio_codec_dict[torrent_info["audio_codec"]], None
    
    # This regex is mainly for bluray_discs
    # TODO rewrite this to be more inclusive of other audio codecs
    bluray_disc_audio_codec_regex = re.search(r'(?P<TrueHD>TrueHD)|(?P<DTSHDMA>DTS-HD.MA)', torrent_info["raw_file_name"].replace(".", " "), re.IGNORECASE)
    if bluray_disc_audio_codec_regex is not None:
        for audio_codec in ["TrueHD", "DTSHDMA"]:
            # Yeah I've kinda given up here, this is mainly to avoid mediainfo running on full bluray discs since TrueHD is really just AC3 which historically I assumed was Dolby Digital...
            #  Don't really wanna deal with that ^^ so we try to match the 2 most popular Bluray Disc audio codecs (DTS-HD.MA & TrueHD) and move on
            if bluray_disc_audio_codec_regex.group(audio_codec) is not None:
                if audio_codec == "DTSHDMA": 
                    audio_codec = "DTS-HD MA"
                logging.info(f'[BasicUtils] Used regex to identify the audio codec: {audio_codec}')
                return audio_codec, None
    
     # Now we try to identify the audio_codec using pymediainfo
    if media_info_audio_track is not None:
        logging.debug(f'[BasicUtils] Audio track info from mediainfo\n {pformat(media_info_audio_track.to_data())}')
        if media_info_audio_track.codec_id is not None:
            # The release "La.La.Land.2016.1080p.UHD.BluRay.DDP7.1.HDR.x265-NCmt.mkv" when using media_info_audio_track.codec shows the codec as AC3 not EAC3..
            # so well try to use media_info_audio_track.codec_id first
            # Damn, another file has "mp4a-40-2" under codec_id. Pretty sure that's just standard AAC so we'll just use that
            if media_info_audio_track.codec_id == "mp4a-40-2":
                audio_codec = "AAC"
            else:
                audio_codec = media_info_audio_track.codec_id
        elif media_info_audio_track.codec is not None:
            # On rare occasion *.codec is not available and we need to use *.format
            audio_codec = media_info_audio_track.codec
        elif media_info_audio_track.format is not None:
            # Only use *.format if *.codec is unavailable
            audio_codec = media_info_audio_track.format
        # Set audio_codec equal to None if neither of those three ^^ exist and we'll move onto user input
        else:
            audio_codec = None
    else:
        audio_codec = None
    
    # If we got something from pymediainfo we can try to analyze it now
    if audio_codec:
        if "AAC" in audio_codec:
            # AAC gets its own 'if' statement because 'audio_codec' can return something like 'AAC LC-SBR' or 'AAC-HE/LC'
            # Its unnecessary for a torrent title and we only need the "AAC" part
            logging.info(f'[BasicUtils] Used pymediainfo to identify the audio codec: {audio_codec}')
            return "AAC", None
        
        if "FLAC" in audio_codec:
            # This is similar to the AAC situation right above ^^, on a recent upload I got the value "A_FLAC" which can be shortened to 'FLAC'
            logging.info(f'[BasicUtils] Used pymediainfo to identify the audio codec: FLAC')
            return "FLAC", None

        if "DTS" in audio_codec:
            # DTS audio is a bit "special" and has a few possible profiles so we deal with that here
            # We'll first try to extract it all via regex, should that fail we can use ffprobe
            match_dts_audio = re.search(r'DTS(-HD(.MA.)|-ES.|(.[xX].|[xX].)|(.HD.|HD.)|)', torrent_info["raw_file_name"].replace(" ", "."), re.IGNORECASE)
            if match_dts_audio is not None:
                # Some releases have DTS-X-RELEASE_GROUP, in this case we only need DTS-X
                return_value =str(match_dts_audio.group()).upper().replace(".", " ").strip()
                if return_value.endswith("-"):
                    return_value = return_value[:len(return_value)-1]
                
                logging.info(f'[BasicUtils] Used (pymediainfo + regex) to identify the audio codec: {return_value}')
                if return_value in audio_codec_dict.keys():
                    # Now its a bit of a Hail Mary and we try to match whatever pymediainfo returned to our audio_codec_dict/translation
                    logging.info(f'[BasicUtils] Used (pymediainfo + regex + audio_codec_dict) to identify the audio codec: {audio_codec_dict[return_value]}')
                    return audio_codec_dict[return_value], None
                return return_value, None

            # If the regex failed we can try ffprobe
            audio_info_probe = FFprobe( inputs={parse_me: None}, 
                global_options=['-v', 'quiet', '-print_format', 'json', '-select_streams a:0', '-show_format', '-show_streams']).run(stdout=subprocess.PIPE)
            audio_info = json.loads(audio_info_probe[0].decode('utf-8'))

            for stream in audio_info["streams"]:
                logging.info(f'[BasicUtils] Used ffprobe to identify the audio codec: {stream["profile"]}')
                return stream["profile"], None
        
        logging.debug(f"[BasicUtils] Pymediainfo extracted audio_codec as {audio_codec}")
        
        if audio_codec in audio_codec_dict.keys():
            # Now its a bit of a Hail Mary and we try to match whatever pymediainfo returned to our audio_codec_dict/translation
            logging.info(f'[BasicUtils] Used (pymediainfo + audio_codec_dict) to identify the audio codec: {audio_codec_dict[audio_codec]}')
            return audio_codec_dict[audio_codec], None

    # If the audio_codec has not been extracted yet then we try user_input
    if auto_mode == 'false':
        while True:
            audio_codec_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g.  DTS | DDP | FLAC | TrueHD | Opus  )')
            if len(str(audio_codec_input)) < 2:
                logging.error(f'[BasicUtils] User enterted an invalid input `{str(audio_codec_input)}` for {missing_value}. Attempting to read again.')
                console.print(f'[red]Invalid input provided. Please provide a valid {missing_value}[/red]')
            else:
                logging.info(f"[BasicUtils] Used user_input to identify the {missing_value}: {audio_codec_input}")
                return str(audio_codec_input), None

    # -- ! This runs if auto_mode == true !
    # We could technically upload without the audio codec in the filename, check to see what the user wants
    if str(os.getenv('force_auto_upload')).lower() == 'true':  # This means we will still force an upload without the audio_codec
        logging.info("[BasicUtils] force_auto_upload=true so we'll upload without the audio_codec in the torrent title")
        return "", None
    
    # Well shit, if nothing above returned any value then it looks like this is the end of our journey :(
    # Exit the script now
    quit_log_reason(reason="Could not detect audio_codec via regex, pymediainfo, & ffprobe. force_auto_upload=false so we quit now", missing_value=missing_value)


def basic_get_missing_audio_channels(torrent_info, is_disc, auto_mode, parse_me, media_info_audio_track, missing_value):
    if is_disc and torrent_info["bdinfo"] is not None:
        return bdinfo_get_audio_channels_from_bdinfo(torrent_info["bdinfo"])
    
    # First try detecting the 'audio_channels' using regex
    if "raw_file_name" in torrent_info:
        # First split the filename by '-' & '.'
        file_name_split = re.sub(r'[-.]', ' ', str(torrent_info["raw_file_name"]))
        # Now search for the audio channels
        re_extract_channels = re.search(r'\s[0-9]\s[0-9]\s', file_name_split)
        if re_extract_channels is not None:
            # Because this isn't something I've tested extensively I'll only consider it a valid match if its a super common channel layout (e.g.  7.1  |  5.1  |  2.0  etc)
            re_extract_channels = re_extract_channels.group().split()
            mid_pos = len(re_extract_channels) // 2
            # joining and construction using single line
            possible_audio_channels = str(' '.join(re_extract_channels[:mid_pos] + ["."] + re_extract_channels[mid_pos:]).replace(" ", ""))
            # Now check if the regex match is in a list of common channel layouts
            if possible_audio_channels in ['1.0', '2.0', '5.1', '7.1']:
                # It is! So return the regex match and skip over the ffprobe process below
                logging.info(f"[BasicUtils] Used regex to identify audio channels: {possible_audio_channels}")
                return possible_audio_channels

    # If the regex failed ^^ (Likely) then we use ffprobe to try and auto detect the channels
    audio_info_probe = FFprobe(inputs={parse_me: None}, 
        global_options=['-v', 'quiet', '-print_format', 'json', '-select_streams a:0', '-show_format', '-show_streams']).run(stdout=subprocess.PIPE)

    audio_info = json.loads(audio_info_probe[0].decode('utf-8'))
    for stream in audio_info["streams"]:
        if "channel_layout" in stream:  # make sure 'channel_layout' exists first (on some amzn webdls it doesn't)
            # convert the words 'mono, stereo, quad' to work with regex below
            ffmpy_channel_layout_translation = {'mono': '1.0', 'stereo': '2.0', 'quad': '4.0'}
            
            if str(stream["channel_layout"]) in ffmpy_channel_layout_translation.keys():
                stream["channel_layout"] = ffmpy_channel_layout_translation[stream["channel_layout"]]

            # Make sure what we got back from the ffprobe search fits into the audio_channels 'format' (num.num)
            audio_channel_layout = re.search(r'\d\.\d', str(stream["channel_layout"]).replace("(side)", ""))
            if audio_channel_layout is not None:
                audio_channels_ff = str(audio_channel_layout.group())
                logging.info(f"[BasicUtils] Used ffmpy.ffprobe to identify audio channels: {audio_channels_ff}")
                return audio_channels_ff
    
    # Another thing we can try is pymediainfo and count the 'Channel layout' then subtract 1 depending on if 'LFE' is one of them
    if media_info_audio_track.channel_layout is not None:
        channel_total = str(media_info_audio_track.channel_layout).split(" ")
        if 'LFE' in channel_total:
            audio_channels_pymedia = f'{int(len(channel_total)) - 1}.1'
        else:
            audio_channels_pymedia = f'{int(len(channel_total))}.0'

        logging.info(f"[BasicUtils] Used pymediainfo to identify audio channels: {audio_channels_pymedia}")
        return audio_channels_pymedia

    # If no audio_channels have been extracted yet then we try user_input next
    if auto_mode == 'false':
        while True:
            audio_channel_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g.  5.1 | 2.0 | 7.1  )')
            if len(str(audio_channel_input)) < 2:
                logging.error(f'[BasicUtils] User enterted an invalid input `{str(audio_channel_input)}` for {missing_value}. Attempting to read again.')
                console.print(f'[red]Invalid input provided. Please provide a valid {missing_value}[/red]')
            else:
                logging.info(f"[BasicUtils] Used user_input to identify {missing_value}: {audio_channel_input}")
                return str(audio_channel_input)

    # -- ! This runs if auto_mode == true !
    # We could technically upload without the audio channels in the filename, check to see what the user wants
    if str(os.getenv('force_auto_upload')).lower() == 'true':  # This means we will still force an upload without the audio_channels
        logging.info("[BasicUtils] force_auto_upload=true so we'll upload without the audio_channels in the filename")
        return ""

    # Well shit, if nothing above returned any value then it looks like this is the end of our journey :(
    # Exit the script now
    quit_log_reason(reason="Audio_Channels are not in the filename, and we can't extract it using regex or ffprobe. force_auto_upload=false so we quit now", missing_value=missing_value)
    

def basic_get_missing_screen_size(torrent_info, is_disc, media_info_video_track, auto_mode, missing_value):
    width_to_height_dict = {"720": "576", "960": "540", "1280": "720", "1920": "1080", "4096": "2160", "3840": "2160", "692": "480", "1024" : "576"}
    logging.debug(f"[BasicUtils] Attempting to identify the resolution")

    if is_disc and torrent_info["bdinfo"] is not None:
        logging.info(f"[BasicUtils] `screen_size` identifed from bdinfo as {torrent_info['bdinfo']['video'][0]['resolution']}")
        return torrent_info["bdinfo"]["video"][0]["resolution"]
    
    # First we use attempt to use "width" since its almost always constant (Groups like to crop black bars so "height" is always changing)
    if str(media_info_video_track.width) != "None":
        track_width = str(media_info_video_track.width)
        if track_width in width_to_height_dict:
            height = width_to_height_dict[track_width]
            logging.info(f"[BasicUtils] Used pymediainfo 'track.width' to identify a resolution of: {str(height)}p")
            return f"{str(height)}p"
    
    # If "Width" somehow fails its unlikely that "Height" will work but might as well try
    if str(media_info_video_track.height) != "None":
        logging.info(f"[BasicUtils] Used pymediainfo 'track.height' to identify a resolution of: {str(media_info_video_track.height)}p")
        return f"{str(media_info_video_track.height)}p"
    
    # User input as a last resort
    else:
        # If auto_mode is enabled we can prompt the user for input
        if auto_mode == 'false':
            while True:
                screen_size_input = Prompt.ask(f'\n[red]We could not auto detect the {missing_value}[/red], [bold]Please input it now[/bold]: (e.g. 720p, 1080p, 2160p) ')
                if len(str(screen_size_input)) < 2:
                    logging.error(f'[BasicUtils] User enterted an invalid input `{str(screen_size_input)}` for {missing_value}. Attempting to read again.')
                    console.print(f'[red]Invalid input provided. Please provide a valid {missing_value}[/red]')
                else:
                    logging.info(f"[BasicUtils] Used user_input to identify the {missing_value}: {str(screen_size_input)}")
                    return str(screen_size_input)
        else:
            # If we don't have the resolution we can't upload this media since all trackers require the resolution in the upload form
            quit_log_reason(reason="Resolution not in filename, and we can't extract it using pymediainfo. Upload form requires the Resolution", missing_value=missing_value)


def basic_get_missing_source(torrent_info, is_disc, auto_mode, missing_value):
    # for disc uploads / currently only bluray is supported so we can use that
    # TODO update this to handle DVDs in the future
    if is_disc and torrent_info["bdinfo"] is not None:
        if "screen_size" in torrent_info and torrent_info["screen_size"] == "2160p":
            torrent_info['uhd'] = 'UHD'
        return "bluray", "bluray_disc"
    
    # Well shit, this is a problem and I can't think of a good way to consistently & automatically get the right result
    # if auto_mode is set to false we can ask the user but if auto_mode is set to true then we'll just need to quit since we can't upload without it
    if auto_mode == 'false':
        console.print(f"Can't auto extract the [bold]{missing_value}[/bold] from the filename, you'll need to manually specify it", style='red', highlight=False)

        basic_source_to_source_type_dict = {
            # this dict is used to associate a 'parent' source with one if its possible final forms
            'bluray': ['disc', 'remux', 'encode'],
            'web': ['rip', 'dl'],
            'hdtv': 'hdtv',
            'dvd': ['disc', 'remux', 'rip'],
            'pdtv': 'pdtv',
            'sdtv': 'sdtv'
        }
        # First get a basic source into the torrent_info dict, we'll prompt the user for a more specific source next (if needed, e.g. 'bluray' could mean 'remux', 'disc', or 'encode')
        source = Prompt.ask("Input one of the following: ", choices=["bluray", "web", "hdtv", "dvd", "pdtv", "sdtv"])
        # Since the parent source isn't the filename we know that the 'final form' definitely won't be so we don't return the 'parent source' yet
        # We instead prompt the user again to figure out if its a remux, encode, webdl, rip, etc etc
        # Once we figure all that out we can return the 'parent source'

        # Now that we have the basic source we can prompt for a more specific source
        if isinstance(basic_source_to_source_type_dict[source], list):
            specific_source_type = Prompt.ask(f"\nNow select one of the following 'formats' for [green]'{source}'[/green]: ",
                choices=basic_source_to_source_type_dict[source])
            # The user is given a list of options that are specific to the parent source they choose earlier (e.g.  bluray --> disc, remux, encode )
            source_type = f'{source}_{specific_source_type}'
        else:
            # Right now only HDTV doesn't have any 'specific' variation so this will only run if HDTV is the source
            source_type = f'{source}'

        # Now that we've got all the source related info, we can return the 'parent source' and move on
        return source, source_type
    else:# shit
        quit_log_reason(reason="auto_mode is enabled & we can't auto detect the source (e.g. bluray, webdl, dvd, etc). Upload form requires the Source", missing_value=missing_value)


def basic_get_missing_mediainfo(torrent_info, parse_me, working_folder):
    logging.info("[BasicUtils] Generating mediainfo.txt")
    # If its not a bluray disc we can get mediainfo, otherwise we need BDInfo
    if "largest_playlist" not in torrent_info:
        # We'll remove the full file path for privacy reasons and only show the file (or folder + file) path in the "Complete name" of media_info_output
        if 'raw_video_file' in torrent_info:
            essential_path = f"{torrent_info['raw_file_name']}/{os.path.basename(torrent_info['raw_video_file'])}"
        else:
            essential_path = f"{os.path.basename(torrent_info['upload_media'])}"
        # depending on if the user is uploading a folder or file we need for format it correctly so we replace the entire path with just media file/folder name
        logging.info(f"[BasicUtils] Using the following path in mediainfo.txt: {essential_path}")
        media_info_output = str(MediaInfo.parse(parse_me, output="text", full=False)).replace(parse_me, essential_path)
        save_location = f'{working_folder}/temp_upload/{torrent_info["working_folder"]}mediainfo.txt'
        logging.info(f'[BasicUtils] Saving mediainfo to: {save_location}')
        logging.debug(":::::::::::::::::::::::::::: MediaInfo Output ::::::::::::::::::::::::::::")
        logging.debug(f'\n{media_info_output}')

        with open(save_location, 'w+') as f:
            f.write(media_info_output)
        # now save the mediainfo txt file location to the dict
        # torrent_info["mediainfo"] = save_location
        return save_location
    else:
        pass # this is a full disc and it needs bdinfo


def basic_get_mediainfo(raw_file):
    logging.debug(f"[BasicUtils] Mediainfo will parse the file: {raw_file}")
    meddiainfo_start_time = time.perf_counter()
    media_info_result = MediaInfo.parse(raw_file)
    meddiainfo_end_time = time.perf_counter()
    logging.debug(f"[BasicUtils] Time taken for mediainfo to parse the file {raw_file} :: {(meddiainfo_end_time - meddiainfo_start_time)}")
    return media_info_result


def basic_get_raw_video_file(upload_media):
    raw_video_file = None
    for individual_file in sorted(glob.glob(f"{upload_media}/*")):
        found = False  # this is used to break out of the double nested loop
        logging.info(f"[BasicUtils] Checking to see if {individual_file} is a video file")
        if os.path.isfile(individual_file):
            logging.info(f"[BasicUtils] Using {individual_file} for mediainfo tests")
            file_info = MediaInfo.parse(individual_file)
            for track in file_info.tracks:
                if track.track_type == "Video":
                    logging.info(f"[BasicUtils] Identified a video track in {individual_file}")
                    raw_video_file = individual_file
                    found = True
                    break
            if found:
                break
    return raw_video_file


def basic_get_episode_basic_details(guess_it_result):
    season_number = "0"
    episode_number = "0"
    complete_season = "0"
    individual_episodes = "0"
    daily_episodes = "0"
    s00e00 = "0"

    if 'season' not in guess_it_result:
        logging.error("[BasicUtils] Could not detect the 'season' using guessit")
        if 'date' in guess_it_result:  # we can replace the S**E** format with the daily episodes date
            daily_episode_date = str(guess_it_result["date"])
            logging.info(f'[BasicUtils] Detected a daily episode, using the date ({daily_episode_date}) instead of S**E**')
            s00e00 = daily_episode_date
            daily_episodes = "1"
        else:
            logging.critical("[BasicUtils] Could not detect Season or date (daily episode) so we can not upload this")
            sys.exit(console.print("\ncould not detect the 'season' or 'date' (daily episode). Cannot upload this.. quitting now\n", style="bold red"))
    else:
        # This else is for when we have a season number, so we can immediately assign it to the torrent_info dict
        season_number = int(guess_it_result["season"])
        # check if we have an episode number
        if 'episode' in guess_it_result:
            if type(guess_it_result["episode"]) is list:
                episode_number = int(guess_it_result["episode"][0])
                s00e00 = f'S{season_number:02d}'
                for episode in guess_it_result["episode"]:
                    s00e00 = f'{s00e00}E{episode:02d}'
            else:
                episode_number = int(guess_it_result["episode"])
                s00e00 = f'S{season_number:02d}E{episode_number:02d}'
            individual_episodes = "1"
        else:
            # if we don't have an episode number we will just use the season number
            s00e00 = f'S{season_number:02d}'
            # marking this as full season
            complete_season = "1"
    return s00e00, str(season_number), str(episode_number), complete_season, individual_episodes, daily_episodes


def get(_this, _or, _from, _default = ""):
    return _from[_this][0] if _this is not None and _this in _from else _from[_or] if _or is not None and _or in _from else _default


def prepare_mediainfo_summary(media_info_result):
    mediainfo_summary = dict()
    mediainfo_summary["Video"] = []
    mediainfo_summary["Audio"] = []
    mediainfo_summary["Text"] = []
    
    for track in media_info_result["tracks"]:
        if track["track_type"] == "General":
            general = dict()
            general["Container"] = get(_this="other_format", _or="format", _from=track)
            general["Size"] = get(_this="other_file_size", _or="file_size", _from=track)
            general["Duration"] = get(_this="other_duration", _or="duration", _from=track)
            general["Bit Rate"] = get(_this="other_overall_bit_rate", _or="overall_bit_rate", _from=track)
            general["Frame Rate"] = get(_this="other_frame_rate", _or="frame_rate", _from=track)
            general["tmdb"] = get(_this=None, _or="tmdb", _from=track, _default="0")
            general["imdb"] = get(_this=None, _or="imdb", _from=track, _default="0")
            general["tvdb"] = get(_this=None, _or="tvdb", _from=track, _default="0")
            mediainfo_summary["General"] = general
        elif track["track_type"] == "Video":
            video = dict()
            video["Codec"] = get(_this="other_format", _or="format", _from=track)
            video["Bit Rate"] = get(_this="other_bit_rate", _or="bit_rate", _from=track)
            video["Frame Rate"] = get(_this="other_frame_rate", _or="frame_rate", _from=track)
            video["Bit Depth"] = get(_this="other_bit_depth", _or="bit_depth", _from=track)
            video["Language"] = get(_this="other_language", _or="language", _from=track)
            video["Aspect Ratio"] = get(_this="other_display_aspect_ratio", _or="display_aspect_ratio", _from=track)
            video["Resolution"] = f'{get(_this="sampled_width", _or="width", _from=track)}x{get(_this="sampled_height", _or="height", _from=track)}'
            mediainfo_summary["Video"].append(video)
        elif track["track_type"] == "Audio":
            audio = dict()
            audio["Format"] = get(_this="other_commercial_name", _or="commercial_name", _from=track)
            audio["Channels"] = get(_this="other_channel_s", _or="channel_s", _from=track)
            audio["Sampling Rate"] = get(_this="other_sampling_rate", _or="sampling_rate", _from=track)
            audio["Compression"] = get(_this="other_compression_mode", _or="compression_mode", _from=track)
            audio["Language"] = get(_this="other_language", _or="title", _from=track)
            audio["Bit Rate"] = get(_this="other_bit_rate", _or="bit_rate", _from=track)
            audio["Bit Rate Mode"] = get(_this="other_bit_rate_mode", _or="bit_rate_mode", _from=track)
            mediainfo_summary["Audio"].append(audio)
        elif track["track_type"] == "Text":
            text = dict()
            text["Language"] = get(_this="other_language", _or="title", _from=track)
            text["Format"] = get(_this="other_format", _or="format", _from=track)
            mediainfo_summary["Text"].append(text)
        elif track["track_type"] == "Menu":
            pass
    
    summary = "---(GENERAL)----" + "\n"
    summary += '\n'.join(f'{key.ljust(15, ".")}: {value}' for key, value in mediainfo_summary["General"].items())

    if len(mediainfo_summary["Video"]) > 0:
        for video_track in mediainfo_summary["Video"]:
            summary += "\n\n"
            summary += "----(VIDEO)-----" + "\n"
            summary += '\n'.join(f'{key.ljust(15, ".")}: {value}' for key, value in video_track.items())

    if len(mediainfo_summary["Audio"]) > 0:
        for audio_track in mediainfo_summary["Audio"]:
            summary += "\n\n"
            summary += "----(AUDIO)-----" + "\n"
            summary += '\n'.join(f'{key.ljust(15, ".")}: {value}' for key, value in audio_track.items())

    if len(mediainfo_summary["Text"]) > 0:
        summary += "\n\n"
        summary += "--(SUBTITLES)---" + "\n"
        summary += f'{"Format".ljust(15, ".")}: {mediainfo_summary["Text"][0]["Format"]}' + "\n"
        summary += f'{"Language".ljust(15, ".")}: '
        for text_track in mediainfo_summary["Text"]:
            text_track = {k: v for k, v in text_track.items() if k.startswith('Language')}
            summary += ''.join(f'{value}, ' for value in text_track.values())
    
    return summary, general["tmdb"], general["imdb"], general["tvdb"]


def basic_get_mediainfo_summary(media_info_result):
    meddiainfo_start_time = time.perf_counter()
    mediainfo_summary, tmdb, imdb, tvdb = prepare_mediainfo_summary(media_info_result)
    meddiainfo_end_time = time.perf_counter()
    logging.debug(f"[BasicUtils] Time taken for mediainfo summary generation :: {(meddiainfo_end_time - meddiainfo_start_time)}")
    logging.debug(f'[BasicUtils] Generated MediaInfo summary :: \n {pformat(mediainfo_summary)}')
    return mediainfo_summary, tmdb, imdb, tvdb
