import json
import os
import pandas as pd
import pytest
import requests


from csgo.parser import DemoParser


class TestDemoParser:
    """Class to test the match parser

    We use the demofiles in test_data.json
    """

    def setup_class(self):
        """Setup class by defining loading dictionary of test demo files"""
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)
        for file in self.demo_data:
            self._get_demofile(demo_link=self.demo_data[file]["url"], demo_name=file)
        self.parser = DemoParser(demofile="default.dem", log=True, parse_rate=256)

    def teardown_class(self):
        """Set parser to none, deletes all demofiles and JSON"""
        self.parser = None
        files_in_directory = os.listdir()
        filtered_files = [
            file
            for file in files_in_directory
            if file.endswith(".dem") or file.endswith(".json")
        ]
        if len(filtered_files) > 0:
            for f in filtered_files:
                os.remove(f)

    @staticmethod
    def _get_demofile(demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    @staticmethod
    def _delete_demofile(demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    @staticmethod
    def _check_round_scores(rounds):
        for i, r in enumerate(rounds):
            if i == 0:
                assert r["tScore"] == 0
                assert r["ctScore"] == 0
            if i > 0 and i != len(rounds):
                winningSide = rounds[i - 1]["winningSide"]
                if winningSide == "ct":
                    assert r["ctScore"] > rounds[i - 1]["ctScore"]
                    assert r["tScore"] == rounds[i - 1]["tScore"]
                if winningSide == "t":
                    assert r["ctScore"] == rounds[i - 1]["ctScore"]
                    assert r["tScore"] > rounds[i - 1]["tScore"]

    def test_demo_id_inferred(self):
        """Tests if a demo_id is correctly inferred"""
        self.parser_inferred = DemoParser(
            demofile="default.dem",
            log=False,
        )
        assert self.parser_inferred.demo_id == "default"

    def test_outpath(self):
        """Tests if the outpath is correctly recorded"""
        self.parser_outpath = DemoParser(demofile="default.dem", log=False, outpath=".")
        assert self.parser_outpath.outpath == os.getcwd()

    def test_demo_id_given(self):
        """Tests if a demo_id is correctly set"""
        self.parser_inferred = DemoParser(
            demofile="default.dem",
            demo_id="test",
            log=False,
        )
        assert self.parser_inferred.demo_id == "test"

    def test_wrong_demo_path(self):
        """Tests if failure on wrong demofile path"""
        with pytest.raises(FileNotFoundError):
            self.parser_wrong_demo_path = DemoParser(
                demofile="bad.dem",
                log=False,
                demo_id="test",
                parse_rate=128,
            )
            self.parser_wrong_demo_path.parse()

    def test_parse_rate(self):
        """Tests if bad parse rates fail"""
        self.parser_neg_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=-1,
        )
        assert self.parser_neg_parse_rate.parse_rate == 128
        self.parser_float_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=64.5,
        )
        assert self.parser_float_parse_rate.parse_rate == 128
        self.parser_good_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            parse_rate=16,
        )
        assert self.parser_good_parse_rate.parse_rate == 16
        self.parser_inferred_parse_rate = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
        )
        assert self.parser_inferred_parse_rate.parse_rate == 128

    def test_logger_set(self):
        """Tests if log file is created"""
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_demoparser.log")

    def test_parse_opts(self):
        """Tests parsing options"""
        self.parser_opts = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            trade_time=7,
            buy_style="hltv",
        )
        assert self.parser_opts.trade_time == 7
        assert self.parser_opts.buy_style == "hltv"
        assert self.parser_opts.dmg_rolled == False
        assert self.parser_opts.parse_frames == True
        self.bad_parser_opts = DemoParser(
            demofile="default.dem",
            log=False,
            demo_id="test",
            trade_time=-2,
            buy_style="test",
        )
        assert self.bad_parser_opts.trade_time == 5
        assert self.bad_parser_opts.buy_style == "hltv"

    def test_read_json_bad_path(self):
        """Tests if the read_json fails on bad path"""
        p = DemoParser()
        with pytest.raises(FileNotFoundError):
            p.read_json("bad_json.json")

    def test_parse_output_type(self):
        """Tests if the JSON output from parse is a dict"""
        output_json = self.parser.parse()
        assert type(output_json) is dict
        assert os.path.exists("default.json")
        assert self.parser.output_file == "default.json"

    def test_parse_valve_matchmaking(self):
        """Tests if demos parse correctly"""
        self.valve_mm = DemoParser(
            demofile="valve_matchmaking.dem", log=False, parse_rate=256
        )
        self.valve_mm_data = self.valve_mm.parse()
        assert len(self.valve_mm_data["gameRounds"]) == 26

    def test_ot_demos(self):
        """Test overtime demos"""
        self.faceit_ot = DemoParser(
            demofile="faceit_ecs_ot.dem", log=False, parse_rate=256
        )
        self.faceit_ot_data = self.faceit_ot.parse()
        assert len(self.faceit_ot_data["gameRounds"]) > 30

    def test_default_parse(self):
        """Tests default parse"""
        self.default_data = self.parser.parse()
        assert self.default_data["mapName"] == "de_cache"
        assert self.default_data["tickRate"] == 128
        assert self.default_data["clientName"] == "GOTV Demo"
        assert len(self.default_data["gameRounds"]) == 33
        assert self.default_data["parserParameters"]["damagesRolledUp"] == False
        assert self.default_data["parserParameters"]["tradeTime"] == 5
        assert self.default_data["parserParameters"]["roundBuyStyle"] == "hltv"
        assert self.default_data["parserParameters"]["parseRate"] == 256
        for r in self.default_data["gameRounds"]:
            assert type(r["bombEvents"]) == list
            assert type(r["damages"]) == list
            assert type(r["kills"]) == list
            assert type(r["flashes"]) == list
            assert type(r["grenades"]) == list
            assert type(r["weaponFires"]) == list
            assert type(r["frames"]) == list

    def test_default_parse_df(self):
        """Tests default parse to dataframe"""
        self.default_data_df = self.parser.parse(return_type="df")
        assert type(self.default_data_df["rounds"]) == pd.DataFrame
        assert type(self.default_data_df["kills"]) == pd.DataFrame
        assert type(self.default_data_df["damages"]) == pd.DataFrame
        assert type(self.default_data_df["grenades"]) == pd.DataFrame
        assert type(self.default_data_df["flashes"]) == pd.DataFrame
        assert type(self.default_data_df["weaponFires"]) == pd.DataFrame
        assert type(self.default_data_df["bombEvents"]) == pd.DataFrame
        assert type(self.default_data_df["frames"]) == pd.DataFrame
        assert type(self.default_data_df["playerFrames"]) == pd.DataFrame

    def test_wrong_return_type(self):
        """Tests if wrong return type errors out"""
        with pytest.raises(ValueError):
            d = self.parser.parse(return_type="i_am_wrong")

    def test_no_json(self):
        """Tests parsing with no json"""
        self.parser_new = DemoParser(demofile="default.dem", log=False, parse_rate=256)
        with pytest.raises(AttributeError):
            d = self.parser_new._parse_bomb_events()
            d = self.parser_new._parse_flashes()
            d = self.parser_new._parse_damages()
            d = self.parser_new._parse_grenades()
            d = self.parser_new._parse_kills()
            d = self.parser_new._parse_frames()
            d = self.parser_new._parse_player_frames()
            d = self.parser_new._parse_weapon_fires()

    def test_bot_name(self):
        """Tests if bot naming is correct (brought up by Charmees).
        Original error had "Troy" (bot) showing up instead of "Charmees" (player)
        """
        self.bot_name_parser = DemoParser(
            demofile="bot_name_test.dem", log=False, parse_frames=False
        )
        self.bot_name_data = self.bot_name_parser.parse()
        charmees_found = 0
        for r in self.bot_name_data["gameRounds"]:
            if r["damages"]:
                for e in r["damages"]:
                    if e["victimName"] == "Charmees":
                        charmees_found += 1
        assert charmees_found > 0

    def test_warmup(self):
        """Tests if warmup rounds are properly parsing."""
        self.warmup_parser = DemoParser(
            demofile="warmup_test.dem", log=False, parse_frames=False
        )
        self.warmup_data = self.warmup_parser.parse()
        self.warmup_data = self.warmup_parser.clean_rounds(
            remove_no_frames=False,
            remove_excess_players=False,
        )
        assert len(self.warmup_data["gameRounds"]) == 30
        self._check_round_scores(self.warmup_data["gameRounds"])
        self.warmup_parser_sneem = DemoParser(
            demofile="vitality-vs-g2-m2-mirage.dem", log=False, parse_frames=True
        )
        self.warmup_sneem_data = self.warmup_parser_sneem.parse()
        self.warmup_sneem_data = self.warmup_parser_sneem.clean_rounds(
            remove_excess_players=False,
        )
        assert len(self.warmup_sneem_data["gameRounds"]) == 30
        self._check_round_scores(self.warmup_sneem_data["gameRounds"])

    def test_bomb_sites(self):
        """Tests that both bombsite A and B show up."""
        self.bombsite_parser = DemoParser(
            demofile="bombsite_test.dem", log=False, parse_frames=False
        )
        self.bombsite_data = self.bombsite_parser.parse()
        for r in self.bombsite_data["gameRounds"]:
            for e in r["bombEvents"]:
                assert (e["bombSite"] == "A") or (e["bombSite"] == "B")

    def test_phase_lists(self):
        """Tests that phase lists are lists."""
        self.phase_parser = DemoParser(
            demofile="bombsite_test.dem", log=False, parse_frames=False
        )
        self.phase_data = self.phase_parser.parse()
        for phase in self.phase_data["matchPhases"].keys():
            assert type(self.phase_data["matchPhases"][phase]) == list

    def test_round_clean(self):
        """Tests that remove time rounds is working."""
        self.round_clean_parser = DemoParser(
            demofile="round_clean_test.dem", log=False, parse_frames=False
        )
        self.round_clean_data = self.round_clean_parser.parse()
        self.round_clean_parser.remove_time_rounds()
        assert len(self.round_clean_data["gameRounds"]) == 24

    def test_player_clean(self):
        """Tests that remove excess players is working."""
        self.player_clean_parser = DemoParser(
            demofile="pov-clean.dem", log=False, parse_frames=True
        )
        self.player_clean_data = self.player_clean_parser.parse()
        self.player_clean_parser.remove_excess_players()
        assert len(self.player_clean_data["gameRounds"]) == 28
