import json
import pandas as pd
import pytest
import requests

from csgo.parser import DemoParser
from csgo.analytics.stats import (extract_num_filters, check_filters, 
                                  num_filter_df, filter_df, calc_stats, 
                                  accuracy, kast, kill_stats, adr, 
                                  util_dmg, flash_stats, bomb_stats, 
                                  econ_stats, weapon_type, kill_breakdown, 
                                  util_dmg_breakdown, win_breakdown, 
                                  player_box_score, team_box_score)
                                 
                                  
class TestStats:
    """Class to test the statistics functions.
    
    Uses https://www.hltv.org/matches/2349180/gambit-vs-natus-vincere-blast-premier-spring-final-2021.
    """
    
    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)

        r = requests.get(self.demo_data["gambit-vs-natus-vincere-m1-dust2"]["url"])
        open("gambit-vs-natus-vincere-m1-dust2" + ".dem", "wb").write(r.content)

        self.parser = DemoParser(
            demofile="gambit-vs-natus-vincere-m1-dust2.dem",
            demo_id="test",
            parse_rate=128,
        )

        self.data = self.parser.parse(return_type="df")
        self.data_json = self.parser.parse()
        self.damage_data = self.data["Damages"]
        self.flash_data = self.data["Flashes"]
        self.grenade_data = self.data["Grenades"]
        self.kill_data = self.data["Kills"]
        self.round_data = self.data["Rounds"]
        self.round_data_json = self.data_json["GameRounds"]
        self.invalid_numeric_filter = {"Kills":[10]}
        self.invalid_logical_operator = {"Kills":["=invalid=10"]}
        self.invalid_numeric_value = {"Kills":["==1invalid0"]}
        self.invalid_str_filter = {"AttackerName":[1]}
        self.invalid_bool_filter = {"IsHeadshot":["True"]} 
        self.filters = {
            "AttackerTeam":["Natus Vincere"], 
            "RoundNum":["<16"], 
            "IsHeadshot":[True],
        }
        self.filtered_kill_data = self.kill_data.loc[
            (self.kill_data[("AttackerTeam")]  == "Natus Vincere")  
            & (self.kill_data["RoundNum"] < 16) 
            & (self.kill_data["IsHeadshot"] == True)]
        self.kills = pd.DataFrame({
            "NAVI PlayerName":["Boombl4", "Perfecto", "b1t", "electronic", 
                               "s1mple"],
            "First Half Headshot Kills":[1, 3, 5, 5, 1],
        })
        
    def test_extract_num_filters(self):
        """Tests extract_num_filters function."""
        assert extract_num_filters({"Kills":["==3"]}, "Kills") == (["=="], 
                                                                   [3.0])
        assert extract_num_filters({"Kills":["!=3"]}, "Kills") == (["!="], 
                                                                   [3.0])
        assert extract_num_filters({"Kills":["<=3"]}, "Kills") == (["<="], 
                                                                   [3.0])
        assert extract_num_filters({"Kills":[">=3"]}, "Kills") == ([">="], 
                                                                   [3.0])
        assert extract_num_filters({"Kills":["<3"]}, "Kills") == (["<"], 
                                                                  [3.0])
        assert extract_num_filters({"Kills":[">3"]}, "Kills") == ([">"], 
                                                                  [3.0])
        assert extract_num_filters({"Kills":[">1", "<5"]}, "Kills") == ([">", 
                                                                         "<"], 
                                                                        [1.0, 
                                                                         5.0])
        
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
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", "==", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] == 3])
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", "!=", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] != 3])
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", "<=", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] <= 3])
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", ">=", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] >= 3])
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", "<", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] < 3])
        assert num_filter_df(
            self.kills, "First Half Headshot Kills", ">", 3.0).equals( 
                self.kills.loc[self.kills["First Half Headshot Kills"] > 3])                                 
        
    def test_filter_df(self):
        """Tests filter_df function."""
        assert filter_df(self.kill_data, self.filters).equals( 
            self.filtered_kill_data)
       
    def test_calc_stats(self):
        """Tests calc_stats function."""
        assert calc_stats(self.kill_data, self.filters, ["AttackerName"],
                          ["AttackerName"], [["size"]], 
                          ["NAVI PlayerName", "First Half Headshot Kills"]
        ).equals(self.kills)
       
    def test_accuracy(self):
        """Tests accuracy function."""
        assert (accuracy(self.damage_data, self.round_data_json)["ACC%"].sum() == 
                1.706741391076766)
    
    def test_kast(self):
        """Tests kast function."""
        assert kast(self.kill_data, "KAST")["KAST%"].sum() == 6.6
        
    def test_kill_stats(self):
        """Tests kill_stats function."""
        assert (kill_stats(self.damage_data, self.kill_data, 
                           self.round_data, self.round_data_json)["KDR"].sum() == 
                10.069507101086048)
        
    def test_adr(self):
        """Tests adr function."""
        assert (adr(self.damage_data, self.round_data)["Norm ADR"].sum() == 
                638.4333333333334)
        
    def test_util_dmg(self):
        """Tests util_dmg function."""
        assert (util_dmg(self.damage_data, self.grenade_data)["UD Per Nade"].sum() 
                == 45.03684172740714)
    
    def test_flash_stats(self):
        """Tests flash_stats function."""
        assert flash_stats(self.flash_data, self.grenade_data)["EF"].sum() == 373
        
    def test_bomb_stats(self):
        """Tests bomb_stats function."""
        assert (bomb_stats(self.bomb_data)["Gambit Defuse %"].sum() == 
                1.2777777777777777)
        
    def test_econ_stats(self):
        """Tests econ_stats function."""
        assert (econ_stats(self.round_data, self.round_data_json)["Avg Spend"].sum() 
                == 52312)   
        
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
        assert kill_breakdown(self.kill_data)["Assault Rifle Kills"].sum() == 96
        
    def test_util_dmg_breakdown(self):
        """Tests util_dmg_breakdown function."""  
        assert (util_dmg_breakdown(self.damage_data, self.grenade_data)
                ["UD Per Nade"].sum() == 123.0436702186702)
   
    def test_win_breakdown(self):
        """Tests win_breakdown function."""
        assert win_breakdown(self.round_data)["T CT Elim Wins"].sum() == 5
        
    def test_player_box_score(self):
        """Tests player_box_score function."""
        assert (player_box_score(self.damage_data, self.flash_data,
                                 self.grenade_data, self.kill_data, 
                                 self.round_data, self.round_data_json)["K"].sum() 
                == 166)
        
    def test_team_box_score(self):
        """Tests team_box_score function."""
        assert (team_box_score(self.damage_data, self.flash_data,
                               self.grenade_data, self.kill_data, 
                               self.round_data, self.round_data_json).iloc[3].sum() 
                == 166)