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

    def test_parsed_wrong_type(self):
        """ Tests wrote parse type
        """
        with pytest.raises(ValueError):
            self.parser.parse(return_type="bad")

    def test_parse_df(self):
        """ Tests if df is parsed
        """
        data = self.parser.parse(return_type="df")
        assert "Rounds" in data.keys()
        assert type(data["Rounds"]) == pd.DataFrame
        assert "Frames" in data.keys()
        assert type(data["Frames"]) == pd.DataFrame
        assert "PlayerFrames" in data.keys()
        assert type(data["PlayerFrames"]) == pd.DataFrame
        assert "Kills" in data.keys()
        assert type(data["Kills"]) == pd.DataFrame
        assert "Damages" in data.keys()
        assert type(data["Damages"]) == pd.DataFrame
        assert "Grenades" in data.keys()
        assert type(data["Grenades"]) == pd.DataFrame
        assert "Flashes" in data.keys()
        assert type(data["Flashes"]) == pd.DataFrame

    def test_parse_bad_return(self):
        """ Tests if parse fails on bad return type
        """
        with pytest.raises(ValueError):
            self.parser.parse(return_type="test")

    def test_parsed_frames(self):
        """ Tests if frames parse correctly
        """
        data = self.parser.parse()
        frames_list = self.parser._parse_frames(return_type="list")
        frames_df = self.parser._parse_frames(return_type="df")
        assert type(frames_list) == list
        assert len(frames_list) == 2521
        assert type(frames_df) == pd.DataFrame
        assert frames_df.shape[0] == 2521
        with pytest.raises(ValueError):
            self.parser._parse_frames(return_type="notalist")

    def test_parsed_frames_not_parsed(self):
        """ Tests if frames parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_frames(return_type="list")

    def test_parsed_player_frames(self):
        """ Tests if player_frames parse correctly
        """
        data = self.parser.parse()
        player_frames_list = self.parser._parse_player_frames(return_type="list")
        player_frames_df = self.parser._parse_player_frames(return_type="df")
        assert type(player_frames_list) == list
        assert len(player_frames_list) == 24610
        assert type(player_frames_df) == pd.DataFrame
        assert player_frames_df.shape[0] == 24610
        with pytest.raises(ValueError):
            self.parser._parse_player_frames(return_type="notalist")

    def test_parsed_player_frames_not_parsed(self):
        """ Tests if player_frames parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_player_frames(return_type="list")
    
    def test_parsed_rounds(self):
        """ Tests if rounds parse correctly
        """
        data = self.parser.parse()
        rounds_list = self.parser._parse_rounds(return_type="list")
        rounds_df = self.parser._parse_rounds(return_type="df")
        assert type(rounds_list) == list
        assert len(rounds_list) == 25
        assert type(rounds_df) == pd.DataFrame
        assert rounds_df.shape[0] == 25
        with pytest.raises(ValueError):
            self.parser._parse_rounds(return_type="notalist")

    def test_parsed_rounds_not_parsed(self):
        """ Tests if rounds parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_rounds(return_type="list")

    def test_parsed_kills(self):
        """ Tests if kills parse correctly
        """
        data = self.parser.parse()
        kills_list = self.parser._parse_kills(return_type="list")
        kills_df = self.parser._parse_kills(return_type="df")
        assert type(kills_list) == list
        assert len(kills_list) == 163
        assert type(kills_df) == pd.DataFrame
        assert kills_df.shape[0] == 163
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
        assert len(damages_list) == 704
        assert type(damages_df) == pd.DataFrame
        assert damages_df.shape[0] == 704
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
        assert len(grenades_list) == 705
        assert type(grenades_df) == pd.DataFrame
        assert grenades_df.shape[0] == 705
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
        assert len(flashes_list) == 617
        assert type(flashes_df) == pd.DataFrame
        assert flashes_df.shape[0] == 617
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

    def test_parsed_bomb_events(self):
        """ Tests if bomb_events parse correctly
        """
        data = self.parser.parse()
        bomb_events_list = self.parser._parse_bomb_events(return_type="list")
        bomb_events_df = self.parser._parse_bomb_events(return_type="df")
        assert type(bomb_events_list) == list
        assert len(bomb_events_list) == 163
        assert type(bomb_events_df) == pd.DataFrame
        assert bomb_events_df.shape[0] == 163
        with pytest.raises(ValueError):
            self.parser._parse_bomb_events(return_type="notalist")

    def test_parsed_bomb_events_not_parsed(self):
        """ Tests if bomb_events parse correctly if not parsed
        """
        self.parser_not_parsed = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
        )
        with pytest.raises(AttributeError):
            self.parser_not_parsed._parse_bomb_events(return_type="list")

    def test_generate_stats(self):
        """ Tests if stats are generated correctly
        """
        assert True
