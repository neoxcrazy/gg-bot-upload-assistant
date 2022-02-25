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
            line = line.replace("*", "").strip() if line.startswith("*") else line
            if line.startswith("Playlist:"):                        # Playlist: 00001.MPLS              ==> 00001.MPLS
                bdinfo['playlist'] = line.split(':', 1)[1].strip() 
            elif line.startswith("Disc Size:"):                     # Disc Size: 58,624,087,121 bytes   ==> 54.597935752011836
                size = line.split(':', 1)[1].replace("bytes", "").replace(",", "")
                size = float(size)/float(1<<30)
                bdinfo['size'] = size                              
            elif line.startswith("Length:"):                        # Length: 1:37:17.831               ==> 1:37:17
                bdinfo['length'] = line.split(':', 1)[1].split('.',1)[0].strip()
            elif line.startswith("Video:"):
                """
                    video_components: examples [video_components_dict is the mapping of these components and their indexes]
                    MPEG-H HEVC Video / 55873 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-H HEVC Video / 2104 kbps / 1080p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / Dolby Vision / BT.2020
                    MPEG-H HEVC Video / 35033 kbps / 2160p / 23.976 fps / 16:9 / Main 10 @ Level 5.1 @ High / 10 bits / HDR10 / BT.2020
                    MPEG-4 AVC Video / 34754 kbps / 1080p / 23.976 fps / 16:9 / High Profile 4.1
                """
                video_components_dict = {
                    0 : "codec",
                    1 : "bitrate",
                    2 : "resolution",
                    3 : "fps",
                    4 : "aspect_ratio",
                    5 : "profile",
                    6 : "bit_depth",
                    7 : "dv_hdr",
                    8 : "color",
                }
                video_components = line.split(':', 1)[1].split('/')
                video_metadata = {}
                for loop_variable in range(0, len(video_components)):
                    video_metadata[video_components_dict[loop_variable]] = video_components[loop_variable].strip()

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
                    0 : "language",
                    1 : "codec", # atmos => added if present optionally
                    2 : "channels",
                    3 : "sample_rate",
                    4 : "bitrate",
                    5 : "bit_depth" 
                }
                if "(" in line:
                    line = line.split("(")[0] # removing the contents inside bracket
                audio_components = line.split(':', 1)[1].split('/ ') # not so sure about this /{space}
                audio_metadata = {}
                for loop_variable in range(0, len(audio_components)):
                    if "Atmos" in audio_components[loop_variable]: # identifying and tagging atmos audio
                        codec_split = audio_components[loop_variable].split("/")
                        audio_metadata["atmos"] = codec_split[1].strip()
                        audio_components[loop_variable] = codec_split[0].strip()

                    audio_metadata[audio_components_dict[loop_variable]] = audio_components[loop_variable].strip()
                bdinfo["audio"].append(audio_metadata)
            elif line.startswith("Disc Title:"):        # Disc Title: Venom: Let There Be Carnage - 4K Ultra HD
                bdinfo['title'] = line.split(':', 1)[1].strip()
            elif line.startswith("Disc Label:"):        # Disc Label: Venom.Let.There.Be.Carnage.2021.UHD.BluRay.2160p.HEVC.Atmos.TrueHD7.1-MTeam
                bdinfo['label'] = line.split(':', 1)[1].strip()
    return bdinfo