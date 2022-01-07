import os
# from pwd import getpwuid
from rich.console import Console
import sys


def find_owner(filename):
    return os.stat(filename)


def assert_readable(path):
    os_supports_effective_ids = os.access in os.supports_effective_ids
    print("os_supports_effective_ids: " + str(os_supports_effective_ids))
    print("os.supports_effective_ids: " + str(os.supports_effective_ids))
    print("os.access: " + str(os.access))
    print("Effective group id: ", os.getegid())
    print("Effective user id: ", os.geteuid())
    print("Real group id: ", os.getgid())
    print("Real user id: ", os.getuid())
    print("List of supplemental group ids: ", os.getgroups())
    print(os.access(path, os.R_OK, effective_ids=os_supports_effective_ids))
    print(os.access(path, os.R_OK))

    if not os.access(path, os.R_OK, effective_ids=os_supports_effective_ids):
        print("Error")
    else:
        print("Success")


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
Testing for env hashing
"""
from dotenv import dotenv_values
from dotenv import load_dotenv

working_folder = os.path.dirname(os.path.realpath(__file__))
sample_env_keys = dotenv_values(f'{working_folder}/config.env.sample').keys()
# load_dotenv(f'{working_folder}/config.env')

for key in sample_env_keys:
    if os.getenv(key) is None:
        print(f"Outdated config.env file. Environment Variable {key} is missing. ")

"""
Testing for env hashing
"""
