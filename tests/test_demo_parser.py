import os
import pytest
import pandas as pd

from csgo.parser import DemoParser


class TestDemoParser:
    """ Class to test the match parser

    Uses https://www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """ Setup class by instantiating parser
        """
        self.parser = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=True,
            demo_id="test",
            parse_rate=128,
        )

    def teardown_class(self):
        """ Set parser to none
        """
        self.parser = None

    def test_demo_id_inferred(self):
        """ Tests if a demo_id is correctly inferred
        """
        self.parser_inferred = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem", log=False,
        )
        assert self.parser_inferred.demo_id == "og-vs-natus-vincere-m1-dust2"

    def test_demo_id_given(self):
        """ Tests if a demo_id is correctly inferred
        """
        assert self.parser.demo_id == "test"

    def test_wrong_demo_path(self):
        """ Tests if failure on wrong demofile path
        """
        with pytest.raises(ValueError):
            self.parser_wrong_demo_path = DemoParser(
                demofile="bad.dem", log=False, demo_id="test", parse_rate=128,
            )

    def test_parse_rate_bad(self):
        """ Tests if bad parse rates fail
        """
        self.parser_bad_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=129,
        )
        assert self.parser_bad_parse_rate.parse_rate == 32

    def test_parse_fail(self):
        """ Tests if parse fails when JSON parsing fails
        """
        self.parser_bad = DemoParser(
            demofile="tests/test.dem", log=False, demo_id="test", parse_rate=128,
        )
        with pytest.raises(AttributeError):
            self.parser.parse()

    def test_parse_rate_good(self):
        """ Tests if good parse rates are set
        """
        self.parser_diff_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=16,
        )
        assert self.parser_diff_parse_rate.parse_rate == 16

    def test_parse_rate_inferred(self):
        """ Tests if good parse rates are set
        """
        self.parser_inferred_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        assert self.parser_inferred_parse_rate.parse_rate == 32

    def test_logger_set(self):
        """ Tests if log file is created
        """
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_demoparser.log")

    def test_parse_demo(self):
        """ Tests if parse actually outputs a file
        """
        self.parser._parse_demo()
        assert os.path.exists("test.json")

    def test_read_json(self):
        """ Tests if the JSON output from _parse_demo() can be read
        """
        self.parser._parse_demo()
        output_json = self.parser._read_json()
        assert type(output_json) is dict

    def test_parse(self):
        """ Tests if the JSON output from parse is a dict
        """
        output_json = self.parser.parse()
        assert type(output_json) is dict

    def test_parsed_json(self):
        """ Tests if the parsed JSON is correct
        """
        data = self.parser.parse()
        assert data["MatchId"] == self.parser.demo_id
        assert data["ClientName"] == "GOTV Demo"
        assert data["MapName"] == "de_dust2"
        assert data["PlaybackTicks"] == 466670
        assert data["ParseRate"] == 128
        assert len(data["GameRounds"]) == 25
        assert data["GameRounds"][0]["RoundNum"] == 1
        assert data["GameRounds"][0]["StartTick"] == 9308
        assert data["GameRounds"][0]["EndTick"] == 43177
        assert data["GameRounds"][0]["TScore"] == 0
        assert data["GameRounds"][0]["CTScore"] == 0
        assert data["GameRounds"][0]["CTBuyType"] == "Pistol"
        assert data["GameRounds"][0]["TBuyType"] == "Pistol"
        assert data["GameRounds"][15]["CTBuyType"] == "Pistol"
        assert data["GameRounds"][15]["TBuyType"] == "Pistol"
        assert data["GameRounds"][0]["RoundEndReason"] == "CTWin"
        assert data["GameRounds"][0]["CTStartEqVal"] == 4400
        assert data["GameRounds"][0]["TStartEqVal"] == 4250
        assert data["GameRounds"][-1]["RoundEndReason"] == "TerroristsWin"
        assert data["GameRounds"][15]["RoundEndReason"] == "BombDefused"

    def test_parsed_kills(self):
        """ Tests if kills parse correctly
        """
        data = self.parser.parse()
        kills_list = self.parser._parse_kills(return_type="list")
        kills_df = self.parser._parse_kills(return_type="df")
        assert type(kills_list) == list
        assert len(kills_list) == 161
        assert type(kills_df) == pd.DataFrame
        assert kills_df.shape[0] == 161
        with pytest.raises(ValueError):
            self.parser._parse_kills(return_type="notalist")

    def test_parsed_kills_not_parsed(self):
        """ Tests if kills parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_kills(return_type="list")

    def test_parsed_damages(self):
        """ Tests if damages parse correctly
        """
        data = self.parser.parse()
        damages_list = self.parser._parse_damages(return_type="list")
        damages_df = self.parser._parse_damages(return_type="df")
        assert type(damages_list) == list
        assert len(damages_list) == 685
        assert type(damages_df) == pd.DataFrame
        assert damages_df.shape[0] == 685
        with pytest.raises(ValueError):
            self.parser._parse_damages(return_type="notalist")

    def test_parsed_damages_not_parsed(self):
        """ Tests if damages parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_damages(return_type="list")

    def test_parsed_grenades(self):
        """ Tests if grenades parse correctly
        """
        data = self.parser.parse()
        grenades_list = self.parser._parse_grenades(return_type="list")
        grenades_df = self.parser._parse_grenades(return_type="df")
        assert type(grenades_list) == list
        assert len(grenades_list) == 701
        assert type(grenades_df) == pd.DataFrame
        assert grenades_df.shape[0] == 701
        with pytest.raises(ValueError):
            self.parser._parse_grenades(return_type="notalist")

    def test_parsed_grenades_not_parsed(self):
        """ Tests if grenades parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_grenades(return_type="list")

    def test_parsed_flashes(self):
        """ Tests if flashes parse correctly
        """
        data = self.parser.parse()
        flashes_list = self.parser._parse_flashes(return_type="list")
        flashes_df = self.parser._parse_flashes(return_type="df")
        assert type(flashes_list) == list
        assert len(flashes_list) == 701
        assert type(flashes_df) == pd.DataFrame
        assert flashes_df.shape[0] == 701
        with pytest.raises(ValueError):
            self.parser._parse_flashes(return_type="notalist")

    def test_parsed_flashes_not_parsed(self):
        """ Tests if flashes parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_flashes(return_type="list")

    def test_generate_stats(self):
        """ Tests if stats are generated correctly
        """
        assert True
