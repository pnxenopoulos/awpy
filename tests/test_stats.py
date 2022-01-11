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
    rating,
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

    def clean(df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        df_copy = df_copy.loc[
            (df_copy["roundNum"] > 3) & (df_copy["roundNum"] < 32)
        ].copy()
        df_copy.reset_index(inplace=True, drop=True)
        df_copy["roundNum"] = df_copy["roundNum"] - 3
        return df_copy

    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)
        r = requests.get(self.demo_data["astralis-vs-liquid-m2-nuke"]["url"])
        open("astralis-vs-liquid-m2-nuke" + ".dem", "wb").write(r.content)
        self.parser = DemoParser(
            demofile="astralis-vs-liquid-m2-nuke.dem",
            demo_id="test",
            parse_frames=False,
        )
        self.data = self.parser.parse(return_type="df")
        self.bomb_data = self.clean(self.data["bombEvents"])
        self.damage_data = self.clean(self.data["damages"])
        self.flash_data = self.clean(self.data["flashes"])
        self.grenade_data = self.clean(self.data["grenades"])
        self.kill_data = self.clean(self.data["kills"])
        self.round_data = self.clean(self.data["rounds"])
        self.weapon_fire_data = self.clean(self.data["weaponFires"])
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
        self.hs = pd.DataFrame(
            {
                "Astralis Player": ["Magisk", "Xyp9x", "device", "dupreeh", "gla1ve",],
                "1st Half HS": [3, 2, 7, 5, 2],
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

    def test_num_filter_df(self):
        """Tests num_filter_df function."""
        assert num_filter_df(self.hs, "1st Half HS", "==", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] == 3]
        )
        assert num_filter_df(self.hs, "1st Half HS", "!=", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] != 3]
        )
        assert num_filter_df(self.hs, "1st Half HS", "<=", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] <= 3]
        )
        assert num_filter_df(self.hs, "1st Half HS", ">=", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] >= 3]
        )
        assert num_filter_df(self.hs, "1st Half HS", "<", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] < 3]
        )
        assert num_filter_df(self.hs, "1st Half HS", ">", 3.0).equals(
            self.hs.loc[self.hs["1st Half HS"] > 3]
        )

    def test_filter_df(self):
        """Tests filter_df function."""
        assert filter_df(self.kill_data, self.filters).equals(self.filtered_kill_data)

    def test_calc_stats(self):
        """Tests calc_stats function."""
        assert calc_stats(
            self.kill_data,
            self.filters,
            ["attackerName"],
            ["attackerName"],
            [["size"]],
            ["Astralis Player", "1st Half HS"],
        ).equals(self.hs)

    def test_accuracy(self):
        """Tests accuracy function."""
        assert (
            round(accuracy(self.damage_data, self.weapon_fire_data)["ACC%"].sum(), 2)
            == 1.83
        )

    def test_kast(self):
        """Tests kast function."""
        assert round(kast(self.kill_data)["T"].sum(), 2) == 22

    def test_kill_stats(self):
        """Tests kill_stats function."""
        assert (
            round(
                kill_stats(
                    self.damage_data,
                    self.kill_data,
                    self.round_data,
                    self.weapon_fire_data,
                )["KDR"].sum(),
                2,
            )
            == 10.1
        )

    def test_adr(self):
        """Tests adr function."""
        assert (
            round(adr(self.damage_data, self.round_data)["Norm ADR"].sum(), 2) == 729.07
        )

    def test_util_dmg(self):
        """Tests util_dmg function."""
        assert (
            round(util_dmg(self.damage_data, self.grenade_data)["UD Per Nade"].sum(), 2)
            == 48.4
        )

    def test_rating(self):
        """Tests rating function."""
        assert (
            round(
                rating(self.damage_data, self.kill_data, self.round_data)[
                    "Rating"
                ].sum(),
                2,
            )
            == 9.82
        )

    def test_flash_stats(self):
        """Tests flash_stats function."""
        assert (
            flash_stats(self.flash_data, self.grenade_data, self.kill_data)["EF"].sum()
            == 114
        )

    def test_bomb_stats(self):
        """Tests bomb_stats function."""
        assert bomb_stats(self.bomb_data)["Astralis Defuses"].sum() == 8

    def test_econ_stats(self):
        """Tests econ_stats function."""
        assert econ_stats(self.round_data)["Avg Spend"].sum() == 53371

    def test_weapon_type(self):
        """Tests weapon_type function."""
        assert weapon_type("Knife") == "Melee Kills"
        assert weapon_type("CZ-75 Auto") == "Pistol Kills"
        assert weapon_type("MAG-7") == "Shotgun Kills"
        assert weapon_type("MAC-10") == "SMG Kills"
        assert weapon_type("AK-47") == "Assault Rifle Kills"
        assert weapon_type("M249") == "Machine Gun Kills"
        assert weapon_type("AWP") == "Sniper Rifle Kills"
        assert weapon_type("Molotov") == "Utility Kills"

    def test_kill_breakdown(self):
        """Tests kill_breakdown function."""
        assert kill_breakdown(self.kill_data)["Assault Rifle Kills"].sum() == 127

    def test_util_dmg_breakdown(self):
        """Tests util_dmg_breakdown function."""
        assert (
            round(
                util_dmg_breakdown(self.damage_data, self.grenade_data)[
                    "UD Per Nade"
                ].sum(),
                2,
            )
            == 120.02
        )

    def test_win_breakdown(self):
        """Tests win_breakdown function."""
        assert win_breakdown(self.round_data)["T CT Elim Wins"].sum() == 6

    def test_player_box_score(self):
        """Tests player_box_score function."""
        assert (
            player_box_score(
                self.damage_data,
                self.flash_data,
                self.grenade_data,
                self.kill_data,
                self.round_data,
                self.weapon_fire_data,
            )["K"].sum()
            == 179
        )

    def test_team_box_score(self):
        """Tests team_box_score function."""
        assert (
            team_box_score(
                self.damage_data,
                self.flash_data,
                self.grenade_data,
                self.kill_data,
                self.round_data,
                self.weapon_fire_data,
            )
            .iloc[4]
            .sum()
            == 180
        )

    def test_agg_damages(self):
        """Tests agg_damages function."""
        assert len(agg_damages(self.damage_data.copy(),) == 820)

    def test_rating(self):
        """Tests rating function."""
        rating_df = rating(self.damage_data, self.kill_data, self.round_data)
        assert rating_df.iloc[0].Rating < 1.3
        assert rating_df.iloc[0].Rating > 1.2
