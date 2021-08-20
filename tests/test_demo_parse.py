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
        """ Setup class by defining the base parser, demofile list, demofile to use for specific tests
        """
        self.parser = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=True,
            demo_id="test",
            parse_rate=128,
        )
        
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)

    def teardown_class(self):
        """ Set parser to none, deletes all demofiles and JSON
        """
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
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem", log=False,
        )
        assert self.parser_inferred.demo_id == "og-vs-natus-vincere-m1-dust2"

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
                demofile="bad.dem", log=False, demo_id="test", parse_rate=128,
            )

    def test_parse_rate_bad(self):
        """Tests if bad parse rates fail"""
        self.parser_bad_parse_rate = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=False,
            demo_id="test",
            parse_rate=129,
        )
        assert self.parser_bad_parse_rate.parse_rate == 32

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
        assert self.parser_inferred_parse_rate.parse_rate == 32

    def test_logger_set(self):
        """Tests if log file is created"""
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_demoparser.log")

    def test_parse_demo(self):
        """Tests if parse actually outputs a file"""
        self.parser._parse_demo()
        assert os.path.exists("test.json")
        assert self.parser.output_file == "test.json"

    def test_read_json(self):
        """Tests if the JSON output from _parse_demo() can be read"""
        self.parser._parse_demo()
        output_json = self.parser._read_json()
        assert type(output_json) is dict

    def test_parse(self):
        """Tests if the JSON output from parse is a dict"""
        output_json = self.parser.parse()
        assert type(output_json) is dict

    def test_parse(self):
        parse_errors = 0
        for file in self.demo_data:
            if self.demo_data[file]["useForTests"]:
                self._get_demofile(self.demo_data[file]["url"], file)
                self.parser = DemoParser(
                    demofile=file + ".dem", log=True, demo_id=file, parse_rate=128,
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

    def test_parsed_json_rounds(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    len(self.demo_data[demo]["json"]["GameRounds"])
                    == self.demo_data[demo]["rounds"]
                )

    def _count_deaths(self, json):
        total_deaths = 0
        for r in json["GameRounds"]:
            for _ in r["Kills"]:
                total_deaths += 1
        return total_deaths

    def test_parsed_deaths(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_deaths = self._count_deaths(self.demo_data[demo]["json"])
                real_deaths = self.demo_data[demo]["totalDeaths"]
                print(
                    "[{0}] Parsed {1} deaths, real deathss are {2}".format(
                        demo, demo_deaths, real_deaths
                    )
                )
                assert demo_deaths == real_deaths

    def _count_kills(self, json):
        total_kills = 0
        for r in json["GameRounds"]:
            for k in r["Kills"]:
                if not k["IsTeamkill"] and not k["IsSuicide"]:
                    total_kills += 1
        return total_kills

    def test_parsed_kills(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_kills = self._count_kills(self.demo_data[demo]["json"])
                real_kills = self.demo_data[demo]["totalKills"]
                print(
                    "[{0}] Parsed {1} kills, real kills are {2}".format(
                        demo, demo_kills, real_kills
                    )
                )
                assert demo_kills == real_kills

    def _count_teamkills(self, json):
        total_teamkills = 0
        for r in json["GameRounds"]:
            for k in r["Kills"]:
                if k["IsTeamkill"]:
                    total_teamkills += 1
        return total_teamkills

    def test_parsed_teamkills(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_tk = self._count_teamkills(self.demo_data[demo]["json"])
                real_tk = self.demo_data[demo]["totalTeamkills"]
                print(
                    "[{0}] Parsed {1} teamkills, real teamkills are {2}".format(
                        demo, demo_tk, real_tk
                    )
                )
                assert demo_tk == real_tk

    def _count_firstkills(self, json):
        total_firstkills = 0
        for r in json["GameRounds"]:
            for k in r["Kills"]:
                if k["IsFirstKill"]:
                    total_firstkills += 1
        return total_firstkills

    def test_parsed_firstkills(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_fk = self._count_firstkills(self.demo_data[demo]["json"])
                real_fk = self.demo_data[demo]["totalFirstKills"]
                print(
                    "[{0}] Parsed {1} firstkills, real firstkills are {2}".format(
                        demo, demo_fk, real_fk
                    )
                )
                assert demo_fk == real_fk

    def _count_headshots(self, json):
        total_hs = 0
        for r in json["GameRounds"]:
            for k in r["Kills"]:
                if k["IsHeadshot"]:
                    total_hs += 1
        return total_hs

    def test_parsed_headshots(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_hs = self._count_headshots(self.demo_data[demo]["json"])
                real_hs = self.demo_data[demo]["totalHeadshots"]
                print(
                    "[{0}] Parsed {1} headshots, real headshots are {2}".format(
                        demo, demo_hs, real_hs
                    )
                )
                assert demo_hs == real_hs

    def _count_assists(self, json):
        total_ast = 0
        for r in json["GameRounds"]:
            for k in r["Kills"]:
                if k["AssisterName"] is not None:
                    total_ast += 1
        return total_ast

    def test_parsed_assists(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_ast = self._count_assists(self.demo_data[demo]["json"])
                real_ast = self.demo_data[demo]["totalAssists"]
                print(
                    "[{0}] Parsed {1} assists, real assists are {2}".format(
                        demo, demo_ast, real_ast
                    )
                )
                assert demo_ast == real_ast

    def test_parsed_roundendreasons(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["GameRounds"]):
                    assert r["RoundEndReason"] == self.demo_data[demo]["roundEndReasons"][i]
