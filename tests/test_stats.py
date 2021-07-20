import json
import pandas as pd
import pytest
import requests

from csgo.parser import DemoParser

from csgo.analytics.stats import (extract_num_filters, check_filters, 
                                  num_filter_df, filter_df, calc_stats, kdr,
                                  adr, headshot_pct, util_dmg, weapon_type, 
                                  kills_by_weapon_type)
                                 
                                  
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

        self.invalid_numeric_filter = {"Kills":[10]}
        self.invalid_logical_operator = {"Kills":["=invalid=10"]}
        self.invalid_numeric_value = {"Kills":["==1invalid0"]}
        self.invalid_str_filter = {"AttackerName":[1]}
        self.invalid_bool_filter = {"IsHeadshot":["True"]} 
        self.kill_data = self.data["Kills"]
        self.round_data = self.data["Rounds"]
        self.damage_data = self.data["Damages"]
        self.grenade_data = self.data["Grenades"]
        self.filters = {
            "AttackerTeam":["Natus Vincere"], 
            "RoundNum":["<16"], 
            "IsHeadshot":[True],
        }
        self.filtered__kill_data = self.kill_data.loc[
            (self.kill_data[("AttackerTeam")]  == "Natus Vincere")  
            & (self.kill_data["RoundNum"] < 16) 
            & (self.kill_data["IsHeadshot"] == True)]
        self.kill_stats = pd.DataFrame({
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
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", "==", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   == 3]
        )
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", "!=", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   != 3]
        )
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", "<=", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   <= 3]
        )
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", ">=", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   >= 3]
        )
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", "<", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   < 3]
        )
        assert (num_filter_df(
            self.kill_stats, "First Half Headshot Kills", ">", 3.0) 
            == self.kill_stats.loc[self.kill_stats["First Half Headshot Kills"] 
                                   > 3]                                  
        )
        
    def test_filter_df(self):
        """Tests filter_df function."""
        assert filter_df(self.kill_data, self.filters).equals( 
            self.filtered_kill_data)
       
    def test_calc_stats(self):
        """Tests calc_stats function."""
        assert calc_stats(self.kill_data, self.filters, ["AttackerName"],
                          ["AttackerName"], [["size"]], 
                          ["NAVI PlayerName", "First Half Headshot Kills"]
        ).equals(self.kill_stats)
        
    def test_kdr(self):
        """Tests kdr function."""
        assert kdr(self.kill_data)["KDR"].sum() == 10.125062656641605
        
    def test_adr(self):
        """Tests adr function."""
        assert (adr(self.round_data, self.damage_data)["RawADR"].sum() 
            == 926.8666666666667)
        
    def test_headshot_pct(self):
        """Tests headshot_pct function."""
        assert (headshot_pct(self.kill_data)["HeadshotPct"].sum()
            == 4.500685425685426)
        
    def test_util_dmg(self):
        """Tests util_dmg function."""
        assert (util_dmg(self.damage_data, self.grenade_data)
            ["DamagePerNade"].sum() == 72.93796930324726)
        
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
      
    def test_kills_by_weapon_type(self):
        """Tests kills_by_weapon_type function."""  
        assert (kills_by_weapon_type(self.kill_data)
            ["Assault Rifle Kills"].sum() == 96)