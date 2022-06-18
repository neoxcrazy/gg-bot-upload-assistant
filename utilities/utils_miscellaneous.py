import re
import sys
import json
import logging

from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt


console = Console()


def miscellaneous_perform_scene_group_capitalization(scene_groups_path, release_group):
    # Scene releases after they unrared are all lowercase (usually) so we fix the torrent title here (Never rename the actual file)
    # new groups can be added in the `scene_groups.json`
    scene_group_capitalization = json.load(open(scene_groups_path))

    # compare the release group we extracted to the groups in the dict above ^^
    if str(release_group).lower() in scene_group_capitalization.keys():
        # replace the "release_group" with the dict value we have
        # Also save the fact that this is a scene group for later (we can add a 'scene' tag later to BHD)
        return 'true', scene_group_capitalization[str(release_group).lower()]
    return 'false', release_group


def miscellaneous_identify_bluray_edition(upload_media):
    # use regex (sourced and slightly modified from official radarr repo) to find torrent editions (Extended, Criterion, Theatrical, etc)
    # https://github.com/Radarr/Radarr/blob/5799b3dc4724dcc6f5f016e8ce4f57cc1939682b/src/NzbDrone.Core/Parser/Parser.cs#L21
    try:
        torrent_editions = re.search(
            r"((Recut.|Extended.|Ultimate.|Criterion.|International.)?(Director.?s|Collector.?s|Theatrical|Ultimate|Final|Criterion|International(?=(.(Cut|Edition|Version|Collection)))|Extended|Rogue|Special|Despecialized|\d{2,3}(th)?.Anniversary)(.(Cut|Edition|Version|Collection))?(.(Extended|Uncensored|Remastered|Unrated|Uncut|IMAX|Fan.?Edit))?|(Uncensored|Remastered|Unrated|Uncut|IMAX|Fan.?Edit|Edition|Restored|(234)in1))", upload_media)
        logging.info(f"[MiscellaneousUtils] extracted '{str(torrent_editions.group()).replace('.', ' ')}' as the 'edition' for the final torrent name")
        return str(torrent_editions.group()).replace(".", " ")
    except AttributeError:
        logging.error("[MiscellaneousUtils] No custom 'edition' found for this torrent")
    return None


def miscellaneous_identify_bluray_disc_type(screen_size, upload_media, test_size=None):
    # This is just based on resolution & size so we just match that info up to the key we create below
    possible_types = [25, 50, 66, 100]
    bluray_prefix = 'uhd' if screen_size == "2160p" else 'bd'
    if test_size is not None:
        total_size = test_size
    else:
        total_size = sum(f.stat().st_size for f in Path(
            upload_media).glob('**/*') if f.is_file())

    for possible_type in possible_types:
        if total_size < int(possible_type * 1000000000):
            return str(f'{bluray_prefix}_{possible_type}')
    return None


def miscellaneous_identify_repacks(raw_file_name):
    match_repack = re.search(
        r'RERIP|PROPER2|PROPER3|PROPER4|PROPER|REPACK2|REPACK3|REPACK4|REPACK', raw_file_name, re.IGNORECASE)
    if match_repack is not None:
        logging.info(f'[MiscellaneousUtils] Used Regex to extract: "{match_repack.group()}" from the filename')
        return match_repack.group()
    return None


def miscellaneous_identify_web_streaming_source(streaming_services, raw_file_name, guess_it_result):
    """
        First priority is given to guessit
        If guessit can get the `streaming_service`, then we'll use that
        Otherwise regex is used to detect the streaming service
    """
    # reading stream sources param json.
    # You can add more streaming platforms to the json file.
    # The value of the json keys will be used to create the torrent file name.
    # the keys are used to match the output from guessit
    streaming_sources = json.load(open(streaming_services))
    web_source = guess_it_result.get('streaming_service', '')

    if type(web_source) is list:
        logging.info(f"[MiscellaneousUtils] GuessIt identified multiple streaming services [{web_source}]. Proceeding with the first in the list.")
        web_source = web_source[0]
    guessit_output = streaming_sources.get(web_source)

    if guessit_output is not None:
        logging.info(f'[MiscellaneousUtils] Used guessit to extract the WEB Source: {guessit_output}')
        return guessit_output
    else:
        source_regex = "[\.|\ ](" + "|".join(streaming_sources.values()) + ")[\.|\ ]"
        match_web_source = re.search(source_regex, raw_file_name.upper())
        if match_web_source is not None:
            logging.info(f'[MiscellaneousUtils] Used Regex to extract the WEB Source: {match_web_source.group().replace(".", "").strip()}')
            return match_web_source.group().replace('.', '').strip()
        else:
            logging.error("[MiscellaneousUtils] Not able to extract the web source information from REGEX and GUESSIT")
    return None


def miscellaneous_identify_source_type(raw_file_name, auto_mode, source):
    logging.debug(f'[MiscellaneousUtils] Source type is not available. Trying to identify source type')
    match_source = re.search(r'(?P<bluray_remux>.*blu(.ray|ray).*remux.*)|'
                             r'(?P<bluray_disc>.*blu(.ray|ray)((?!x(264|265)|h.(265|264)|H.(265|264)|H(265|264)).)*$)|'
                             r'(?P<webrip>.*web(.rip|rip).*)|'
                             r'(?P<webdl>.*web(.dl|dl|).*)|'
                             r'(?P<bluray_encode>.*blu(.ray|ray).*|x(264|265)|h.(265|264)|H.(265|264)|H(265|264)|x.(265|264))|'
                             r'(?P<dvd>HD(.DVD|DVD)|.*DVD.*)|'
                             r'(?P<hdtv>.*HDTV.*)', raw_file_name, re.IGNORECASE)
    return_source_type = None
    if match_source is not None:
        for source_type in ["bluray_disc", "bluray_remux", "bluray_encode", "webdl", "webrip", "dvd", "hdtv"]:
            if match_source.group(source_type) is not None:
                return_source_type = source_type

    # Well firstly if we got this far with auto_mode enabled that means we've somehow figured out the 'parent' source but now can't figure out its 'final form'
    # If auto_mode is disabled we can prompt the user
    elif auto_mode == 'false':
        # Yeah yeah this is just copy/pasted from the original user_input source code, it works though ;)
        basic_source_to_source_type_dict = {
            # this dict is used to associate a 'parent' source with one if its possible final forms
            'bluray': ['disc', 'remux', 'encode'],
            'web': ['rip', 'dl'],
            'hdtv': 'hdtv',
            'dvd': ['disc', 'remux', 'rip'],
            'pdtv': 'pdtv',
            'sdtv': 'sdtv'
        }
        # Since we already know the 'parent source' from an earlier function we don't need to prompt the user for it twice
        if str(source).lower() in basic_source_to_source_type_dict and isinstance(basic_source_to_source_type_dict[str(source).lower()], list):
            console.print(
                "\nError: Unable to detect this medias 'format'", style='red')
            console.print(
                f"\nWe've successfully detected the 'parent source': [bold]{source}[/bold] but are unable to detect its 'final form'", highlight=False)
            logging.error(
                f"[MiscellaneousUtils] We've successfully detected the 'parent source': [bold]{source}[/bold] but are unable to detect its 'final form'")

            # Now prompt the user
            specific_source_type = Prompt.ask(f"\nNow select one of the following 'formats' for [green]'{source}'[/green]: ",
                                              choices=basic_source_to_source_type_dict[source])
            # The user is given a list of options that are specific to the parent source they choose earlier (e.g.  bluray --> disc, remux, encode )
            return_source_type = f'{source}_{specific_source_type}'
        else:
            # Right now only HDTV doesn't have any 'specific' variation so this will only run if HDTV is the source
            return_source_type = f'{source}'

    # Well this sucks, we got pretty far this time but since 'auto_mode=true' we can't prompt the user & it probably isn't a great idea to start making assumptions about a media files source,
    # that seems like a good way to get a warning/ban so instead we'll just quit here and let the user know why
    else:
        logging.critical(
            "[MiscellaneousUtils] auto_mode is enabled (no user input) & we can not auto extract the 'source_type'")
        # let the user know the error/issue
        console.print(
            "\nCritical error when trying to extract: 'source_type' (more specific version of 'source', think bluray_remux & just bluray) ", style='red bold')
        console.print("Quitting now..")
        # and finally exit since this will affect all trackers we try and upload to, so it makes no sense to try the next tracker
        sys.exit()
    logging.debug(
        f'[MiscellaneousUtils] Source type identified as {return_source_type}')
    return return_source_type
