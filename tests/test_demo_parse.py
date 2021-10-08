import json
import os
import pytest
import requests

from csgo.parser import DemoParser


class TestDemoParser:
    """Class to test the match parser

    We use the demofiles in test_data.json
    """

    def setup_class(self):
        """Setup class by defining the base parser, demofile list, demofile to use for specific tests"""
        self.parser = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=True,
            demo_id="test",
            parse_rate=256,
        )

        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)

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

    def _get_demofile(self, demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    def _delete_demofile(self, demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    def test_demo_id_inferred(self):
        """Tests if a demo_id is correctly inferred"""
        self.parser_inferred = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
        )
        assert self.parser_inferred.demo_id == "og-vs-natus-vincere-m1-dust2"

    def test_demo_id_inferred_space(self):
        """Tests if a demo_id is correctly inferred"""
        self.parser_inferred_space = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            demo_id="",
            log=False,
        )
        assert self.parser_inferred_space.demo_id == "og-vs-natus-vincere-m1-dust2"

    def test_outpath(self):
        """Tests if the outpath is correctly recorded"""
        self.parser_outpath = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem", log=False, outpath="."
        )
        assert self.parser_outpath.outpath == os.getcwd()

    def test_demo_id_given(self):
        """Tests if a demo_id is correctly inferred"""
        assert self.parser.demo_id == "test"

    def test_wrong_demo_path(self):
        """Tests if failure on wrong demofile path"""
        with pytest.raises(ValueError):
            self.parser_wrong_demo_path = DemoParser(
                demofile="bad.dem",
                log=False,
                demo_id="test",
                parse_rate=128,
            )

    def test_parse_rate_negative(self):
        """Tests if bad parse rates fail"""
        self.parser_bad_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=-1,
        )
        assert self.parser_bad_parse_rate.parse_rate == 128

    def test_parse_rate_float(self):
        """Tests if bad parse rates fail"""
        self.parser_bad_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=64.5,
        )
        assert self.parser_bad_parse_rate.parse_rate == 128

    def test_parse_rate_one(self):
        """Tests if parse rate can be set to 1"""
        self.parser_diff_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=1,
        )
        assert self.parser_diff_parse_rate.parse_rate == 1

    def test_parse_rate_good(self):
        """Tests if good parse rates are set"""
        self.parser_diff_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=16,
        )
        assert self.parser_diff_parse_rate.parse_rate == 16

    def test_parse_rate_inferred(self):
        """Tests if good parse rates are set"""
        self.parser_inferred_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
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
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            trade_time=7,
            buy_style="hltv",
        )
        assert self.parser_opts.trade_time == 7
        assert self.parser_opts.buy_style == "hltv"
        assert self.parser_opts.dmg_rolled == False
        assert self.parser_opts.parse_frames == True

    def test_bad_parse_opts(self):
        """Tests bad parsing options"""
        self.parser_opts = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            trade_time=-2,
            buy_style="test",
        )
        assert self.parser_opts.trade_time == 5
        assert self.parser_opts.buy_style == "hltv"

    def test_parse_output_type(self):
        """Tests if the JSON output from parse is a dict"""
        output_json = self.parser.parse()
        assert type(output_json) is dict
        assert os.path.exists("test.json")
        assert self.parser.output_file == "test.json"

    def test_parse(self):
        parse_errors = 0
        for file in self.demo_data:
            if self.demo_data[file]["useForTests"]:
                self._get_demofile(self.demo_data[file]["url"], file)
                self.parser = DemoParser(
                    demofile=file + ".dem",
                    log=True,
                    demo_id=file,
                    parse_rate=256,
                )
                self.parser.parse()
                if self.parser.parse_error == True:
                    # If error, count it
                    parse_errors += 1
                else:
                    # If not, then add the JSON
                    with open(file + ".json") as f:
                        self.demo_data[file]["json"] = json.load(f)
                self._delete_demofile(file)
        assert parse_errors == 0

    def test_parsed_metadata(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                if self.demo_data[demo]["tickrate"]["test"]:
                    assert (
                        self.demo_data[demo]["tickrate"]["value"]
                        == self.demo_data[demo]["json"]["tickRate"]
                    )

    def test_round_ticks(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    if not r["isWarmup"] and r["roundEndReason"] != "":
                        assert r["startTick"] <= r["freezeTimeEndTick"]
                        assert r["freezeTimeEndTick"] <= r["endTick"]
                        assert r["endTick"] <= r["endOfficialTick"]

    def test_round_winners(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if not r["isWarmup"] and r["roundEndReason"] != "":
                        if i in self.demo_data[demo]["useableRounds"]:
                            if r["winningSide"] == "CT":
                                assert r["winningTeam"] == r["ctTeam"]
                            else:
                                assert r["winningTeam"] == r["tTeam"]

    def test_eq_val(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if not r["isWarmup"]:
                        if i in self.demo_data[demo]["useableRounds"]:
                            assert (
                                r["ctStartEqVal"]
                                <= r["ctRoundStartEqVal"] + r["ctRoundStartMoney"]
                            )
                            assert (
                                r["tStartEqVal"]
                                <= r["tRoundStartEqVal"] + r["tRoundStartMoney"]
                            )

    def test_kill_distances(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if i in self.demo_data[demo]["useableRounds"]:
                        for k in r["kills"]:
                            if not k["isSuicide"]:
                                assert k["distance"] > 0

    def test_damage_amounts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if i in self.demo_data[demo]["useableRounds"]:
                        for d in r["damages"]:
                            assert d["hpDamage"] >= d["hpDamageTaken"]
                            assert d["armorDamage"] >= d["armorDamageTaken"]

    def test_seconds_parsing(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if i in self.demo_data[demo]["useableRounds"]:
                        if r["kills"]:
                            for e in r["kills"]:
                                assert e["seconds"] >= 0
                        if r["damages"]:
                            for e in r["damages"]:
                                assert e["seconds"] >= 0
                        if r["bombEvents"]:
                            for e in r["bombEvents"]:
                                assert e["seconds"] >= 0

    def test_parsed_opts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    self.demo_data[demo]["json"]["parserParameters"]["damagesRolledUp"]
                    == False
                )
                assert (
                    self.demo_data[demo]["json"]["parserParameters"]["tradeTime"] == 5
                )
                assert (
                    self.demo_data[demo]["json"]["parserParameters"]["roundBuyStyle"]
                    == "hltv"
                )
                assert (
                    self.demo_data[demo]["json"]["parserParameters"]["parseRate"] == 256
                )

    def test_frames(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if i in self.demo_data[demo]["useableRounds"]:
                        assert len(r["frames"]) > 0

    def test_player_counts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    if i in self.demo_data[demo]["useableRounds"]:
                        for f in r["frames"]:
                            assert len(f["t"]["players"]) == 5
                            assert len(f["ct"]["players"]) == 5
