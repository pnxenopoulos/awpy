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
        with pytest.raises(ValueError):
            self.parser_wrong_demo_path = DemoParser(
                demofile="bad.dem",
                log=False,
                demo_id="test",
                parse_rate=128,
            )

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
