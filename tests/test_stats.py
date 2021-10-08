import json
import pandas as pd
import pytest
import requests

from csgo.parser import DemoParser
from csgo.analytics.stats import (
    extract_num_filters,
    check_filters,
    num_filter_df,
    filter_df,
    calc_stats,
    accuracy,
    kast,
    kill_stats,
    adr,
    util_dmg,
    flash_stats,
    bomb_stats,
    econ_stats,
    weapon_type,
    kill_breakdown,
    util_dmg_breakdown,
    win_breakdown,
    player_box_score,
    team_box_score,
)
from csgo.analytics.utils import agg_damages


class TestStats:
    """Class to test the statistics functions.

    Uses https://www.hltv.org/matches/2337844/astralis-vs-liquid-blast-pro-series-global-final-2019.
    """

    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)

        r = requests.get(self.demo_data["astralis-vs-liquid-m2-nuke"]["url"])
        open("astralis-vs-liquid-m2-nuke" + ".dem", "wb").write(r.content)

        self.parser = DemoParser(
            demofile="astralis-vs-liquid-m2-nuke.dem",
            demo_id="test",
            parse_rate=256,
        )

        self.data = self.parser.parse(return_type="df")
        self.damage_data = self.data["damages"]
        self.flash_data = self.data["flashes"]
        self.grenade_data = self.data["grenades"]
        self.kill_data = self.data["kills"]
        self.bomb_data = self.data["bombEvents"]
        self.round_data = self.data["rounds"]
        self.weapon_fire_data = self.data["weaponFires"]
        self.invalid_numeric_filter = {"Kills": [10]}
        self.invalid_logical_operator = {"Kills": ["=invalid=10"]}
        self.invalid_numeric_value = {"Kills": ["==1invalid0"]}
        self.invalid_str_filter = {"attackerName": [1]}
        self.invalid_bool_filter = {"isHeadshot": ["True"]}
        self.filters = {
            "attackerTeam": ["Astralis"],
            "roundNum": ["<16"],
            "isHeadshot": [True],
        }
        self.filtered_kill_data = self.kill_data.loc[
            (self.kill_data[("attackerTeam")] == "Astralis")
            & (self.kill_data["roundNum"] < 16)
            & (self.kill_data["isHeadshot"] == True)
        ]
        self.kills = pd.DataFrame(
            {
                "Astralis Player": [
                    "Magisk",
                    "Xyp9x",
                    "device",
                    "dupreeh",
                    "gla1ve",
                ],
                "1st Half HS Kills": [3, 2, 7, 5, 2],
            }
        )

    def test_extract_num_filters(self):
        """Tests extract_num_filters function."""
        assert extract_num_filters({"Kills": ["==3"]}, "Kills") == (["=="], [3.0])
        assert extract_num_filters({"Kills": [">1", "<5"]}, "Kills") == (
            [">", "<"],
            [1.0, 5.0],
        )

    def test_extract_num_filters_invalid_type(self):
        """Tests extract_num_filters function with an invalid numeric filter."""
        with pytest.raises(ValueError):
            extract_num_filters(self.invalid_numeric_filter, "Kills")

    def test_extract_num_filters_invalid_operator(self):
        """Tests extract_num_filters function with an invalid logical operator."""
        with pytest.raises(Exception):
            extract_num_filters(self.invalid_logical_operator, "Kills")

    def test_extract_num_filters_invalid_numeric_value(self):
        """Tests extract_num_filters function with an invalid numeric value."""
        with pytest.raises(Exception):
            extract_num_filters(self.invalid_numeric_value, "Kills")

    def test_check_filters_invalid_str_filters(self):
        """Tests check_filters function with an invalid string filter."""
        with pytest.raises(ValueError):
            check_filters(self.kill_data, self.invalid_str_filter)

    def test_check_filters_invalid_bool_filters(self):
        """Tests check_filters function with an invalid boolean filter."""
        with pytest.raises(ValueError):
            check_filters(self.kill_data, self.invalid_bool_filter)
