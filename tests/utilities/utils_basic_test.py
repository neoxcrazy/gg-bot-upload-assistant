import pytest
import datetime

from utilities.utils_basic import *


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