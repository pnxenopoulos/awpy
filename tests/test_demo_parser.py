import os
import pytest
import pandas as pd

from csgo.parser import DemoParser


class TestDemoParser:
    """ Class to test the match parser
    """

    def setup_class(self):
        """ Setup class by instantiating parser
        """
        self.parser = DemoParser(
            demofile="tests/natus-vincere-vs-astralis-m1-dust2.dem",
            log=True,
            match_id="natus-vincere-vs-astralis-m1-dust2",
        )

    def teardown_class(self):
        """ Set parser to none
        """
        self.parser = None

    def test_match_id(self):
        """ Tests if a match_id is not given is parsed properly
        """
        self.parser = DemoParser(
            demofile="tests/natus-vincere-vs-astralis-m1-dust2.dem", log=True,
        )
        assert self.parser.match_id == "natus-vincere-vs-astralis-m1-dust2"

    def test_demo_error(self):
        """ Tests if the parser encountered a corrupted demofile. If it did, the
        parser would set the `demo_error` attribute to True. Since this demofile is
        not corrupted, this test should have parser.demo_error as FALSE
        """
        self.parser._parse_demofile()
        assert not self.parser.demo_error

    def test_logger(self):
        """ Tests if the parser logs correctly.
        """
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_parser.log")

    def test_parse_match(self):
        """ Tests if the parser parses the match without issue. Our test demo had 21 total rounds.
        """
        self.parser._parse_match()
        assert len(self.parser.rounds) == 21

    def test_parse(self):
        """ Tests if parse wrapper method works
        """
        output = self.parser.parse()
        assert not self.parser.demo_error
        assert len(self.parser.rounds) == 21
        assert len(output.keys()) == 7

    def test_clean_match(self):
        """ Tests if the clean_rounds works. Should still return 21.
        """
        self.parser._clean_rounds()
        assert len(self.parser.rounds) == 21

    def test_last_round_reason(self):
        """ Tests if the last round had the correct win reason. It should be "CTWin".
        """
        assert self.parser.rounds[-1].reason == "CTWin"

    def test_round_cash_eq(self):
        """ Tests if cash and equipment values are parsing properly.
        """
        assert self.parser.rounds[0].t_eq_val == 4050
        assert self.parser.rounds[0].ct_eq_val == 4400
        assert self.parser.rounds[0].t_cash_spent_total == 3550
        assert self.parser.rounds[0].ct_cash_spent_total == 3650
        assert self.parser.rounds[0].t_cash_spent_round == 3550
        assert self.parser.rounds[0].ct_cash_spent_round == 3650

    def test_round_type(self):
        """ Tests if round types are properly functioning.
        """
        assert self.parser.rounds[0].ct_round_type == "Pistol"
        assert self.parser.rounds[0].t_round_type == "Pistol"
        assert self.parser.rounds[1].ct_round_type == "Half Buy"
        assert self.parser.rounds[2].ct_round_type == "Eco"

    def test_kills_total(self):
        """ Tests if the kill totals are correct. s1mple should have 25 kills.
        """
        self.parser.write_kills()
        kills_df = self.parser.kills_df.groupby("AttackerName").size().reset_index()
        kills_df.columns = ["AttackerName", "Kills"]
        assert kills_df[kills_df["AttackerName"] == "s1mple"].Kills.values[0] == 25

    def test_bomb_plant(self):
        """ Tests for bomb plant events. There should be a plant and a defuse event for this round.
        """
        self.parser.write_bomb_events()
        bomb_df = self.parser.bomb_df
        assert (
            bomb_df.loc[bomb_df["RoundNum"] == 16, ["Tick", "EventType"]].shape[0] == 2
        )

    def test_damage_total(self):
        """ Tests for correct damage per round.
        """
        self.parser.write_damages()
        damage_df = self.parser.damages_df
        damage_df["Damage"] = damage_df["HpDamage"] + damage_df["ArmorDamage"]
        damage_df["KillDamage"] = damage_df["KillHpDamage"] + damage_df["ArmorDamage"]
        dmg = (
            (damage_df.groupby(["AttackerName"]).Damage.sum() / 21)
            .reset_index()
            .iloc[0, 1]
        )
        kill_dmg = (
            (damage_df.groupby(["AttackerName"]).KillDamage.sum() / 21)
            .reset_index()
            .iloc[0, 1]
        )
        assert (dmg == 94.9047619047619) and (kill_dmg == 88.23809523809524)

    def test_grenade_total(self):
        """ Tests for correct number of grenade events.
        """
        self.parser.write_grenades()
        grenades_df = self.parser.grenades_df
        assert grenades_df.shape[0] == 550

    def test_footsteps(self):
        """ Tests for correct trajectory parsing.
        """
        self.parser.write_footsteps()
        footsteps_df = self.parser.footsteps_df
        assert footsteps_df.iloc[777, :].X == 583.253906
        assert footsteps_df.iloc[777, :].Y == 592.542297
        assert footsteps_df.iloc[777, :].Z == 2.59956
        assert footsteps_df.iloc[777, :].XViz == 695.284979
        assert footsteps_df.iloc[777, :].YViz == -601.46766
        assert footsteps_df.iloc[777, :].AreaId == 1432
        assert footsteps_df.iloc[777, :].AreaName == "LongDoors"

    def test_write_data(self):
        """ Tests write data method.
        """
        df_dict = self.parser.write_data()
        assert len(df_dict.keys()) == 7
        assert df_dict["Rounds"].shape[0] == 21

    def test_parse_error(self):
        """ Tests if parser errors on bad file
        """
        self.parser = DemoParser(demofile="tests/file-no-exist.dem", match_id="test",)
        self.parser._parse_demofile()
        assert self.parser.demo_error == True

    def test_json_write(self):
        """ Tests if parser can write to JSON
        """
        self.parser.write_json()
        assert os.path.exists("natus-vincere-vs-astralis-m1-dust2_de_dust2.json")
        assert (
            os.path.getsize("natus-vincere-vs-astralis-m1-dust2_de_dust2.json")
            < 10000000
        )

    def test_json_write_with_footsteps(self):
        """ Tests if parser can write to JSON, including footsteps
        """
        self.parser.write_json(write_footsteps=True)
        assert os.path.exists("natus-vincere-vs-astralis-m1-dust2_de_dust2.json")
        assert (
            os.path.getsize("natus-vincere-vs-astralis-m1-dust2_de_dust2.json")
            > 10000000
        )

    def test_write_map_name(self):
        """ Tests if the parser writes the map name to a dictionary
        """
        df_dict = self.parser.write_data()
        assert df_dict["Map"] == "de_dust2"
