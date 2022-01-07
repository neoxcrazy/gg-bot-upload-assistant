import os
# from pwd import getpwuid
from rich.console import Console
import sys


# def find_owner(filename):
#     return os.stat(filename)


# def assert_readable(path):
#     os_supports_effective_ids = os.access in os.supports_effective_ids
#     print("os_supports_effective_ids: " + str(os_supports_effective_ids))
#     print("os.supports_effective_ids: " + str(os.supports_effective_ids))
#     print("os.access: " + str(os.access))
#     print("Effective group id: ", os.getegid())
#     print("Effective user id: ", os.geteuid())
#     print("Real group id: ", os.getgid())
#     print("Real user id: ", os.getuid())
#     print("List of supplemental group ids: ", os.getgroups())
#     print(os.access(path, os.R_OK, effective_ids=os_supports_effective_ids))
#     print(os.access(path, os.R_OK))

#     if not os.access(path, os.R_OK, effective_ids=os_supports_effective_ids):
#         print("Error")
#     else:
#         print("Success")


# assert_readable("/data/downloads/TVSeries/Money Heist.S03E01.The End of the Road.Netflix.WEBDL.1080p.WhiteHat.mkv")
# print(find_owner("/data/downloads/TVSeries/Money Heist.S03E01.The End of the Road.Netflix.WEBDL.1080p.WhiteHat.mkv"))


"""
Testing for multiline inputs from console
"""
console = Console()

# console.print("start")
# inputData = console.input("provide an input??")
# console.print("end")
# console.print(inputData)


# console.print("Provide inputs: ")
# msg = sys.stdin.readlines()
# print(msg)
# for item in msg:
#     print(item)
"""
Testing for multiline inputs from console
"""


"""
Screenshot Table
"""

import os
import base64
import asyncio
import logging
import pyimgbox
import requests
from ffmpy import FFmpeg
from datetime import datetime
from dotenv import load_dotenv
from rich.progress import track
from rich.console import Console
from rich.table import Table
from rich import box

console.line(count=2)
console.rule(f"Screenshots", style='red', align='center')
console.line(count=1)

screenshot_config = Table(show_header=True, header_style="bold cyan", box=box.HEAVY, border_style="dim")
screenshot_config.add_column("# of Screenshots", justify="center")
screenshot_config.add_column("Thumbnail Size", justify="center")
screenshot_config.add_column("Avoid Spoilers", justify="center")
screenshot_config.add_column("Screenshot Timestamps", justify="center")
screenshot_config.add_column("Image Hosts Order", justify="center")

timestamps = [10,20,30,40,50]
hosts=["freeimage","imgbb","imgbox", "ptpimg"]

screenshot_config.add_row(str(10), str(350), str(True), "\n".join(map(str, timestamps)), "\n".join(hosts))


# tmdb_search_results.add_row(
# f"[chartreuse1][bold]{str(result_num)}[/bold][/chartreuse1]",
# title_match_result,
# f"themoviedb.org/{content_type}/{str(possible_match['id'])}",
# str(year),
# possible_match["original_language"],
# overview,
# end_section=True
# )

console.print(screenshot_config, justify="center")

