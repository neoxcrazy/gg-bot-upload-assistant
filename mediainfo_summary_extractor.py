def get(_this, _or, _from):
    return _from[_this][0] if _this in _from else _from[_or] if _or in _from else ""


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
            mediainfo_summary["General"] = general
        elif track["track_type"] == "Video":
            video = dict()
            video["Codec"] = get(_this="other_format", _or="format", _from=track)
            video["Bit Rate"] = get(_this="other_bit_rate", _or="bit_rate", _from=track)
            video["Frame Rate"] = get(_this="other_frame_rate", _or="frame_rate", _from=track)
            video["Bit Depth"] = get(_this="other_bit_depth", _or="bit_depth", _from=track)
            video["Language"] = get(_this="other_language", _or="language", _from=track)
            video["Aspect Ratio"] = get(_this="other_display_aspect_ratio", _or="display_aspect_ratio", _from=track)
            video["Resolution"] = f'{track["sampled_width"]}x{track["sampled_height"]}'
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
    
    return summary
