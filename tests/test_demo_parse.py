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
                assert (
                    self.demo_data[demo]["json"]["tickRate"]
                    == self.demo_data[demo]["tickRate"]
                )
                assert (
                    self.demo_data[demo]["json"]["serverVars"]["maxRounds"]
                    == self.demo_data[demo]["maxRounds"]
                )

    def test_round_ticks(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    assert r["startTick"] <= r["freezeTimeEndTick"]
                    assert r["freezeTimeEndTick"] <= r["endTick"]
                    assert r["endTick"] <= r["endOfficialTick"]

    def test_half_side_switch(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][15]["ctTeam"]
                    == self.demo_data[demo]["json"]["gameRounds"][14]["tTeam"]
                )

    def test_round_winners(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    if r["winningSide"] == "CT":
                        assert r["winningTeam"] == r["ctTeam"]
                    else:
                        assert r["winningTeam"] == r["tTeam"]

    def test_pistol_rounds(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["ctBuyType"]
                    == "Pistol"
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["tBuyType"]
                    == "Pistol"
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][15]["ctBuyType"]
                    == "Pistol"
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][15]["tBuyType"]
                    == "Pistol"
                )

    def test_start_money(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["ctRoundStartEqVal"]
                    == 1000
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["ctRoundStartMoney"]
                    == 4000
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["tRoundStartEqVal"]
                    == 1000
                )
                assert (
                    self.demo_data[demo]["json"]["gameRounds"][0]["tRoundStartMoney"]
                    == 4000
                )

    def test_eq_val(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
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
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    for k in r["Kills"]:
                        if not k["isSuicide"]:
                            assert k["distance"] > 0

    def test_damage_amounts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    for d in r["damages"]:
                        assert d["hpDamage"] >= d["hpDamageTaken"]
                        assert d["armorDamage"] >= d["armorDamageTaken"]

    def test_parsed_json_rounds(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    len(self.demo_data[demo]["json"]["gameRounds"])
                    == self.demo_data[demo]["rounds"]
                )

    def test_parsed_opts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                assert (
                    self.demo_data[demo]["json"]["ParserParameters"]["damagesRolledUp"]
                    == False
                )
                assert (
                    self.demo_data[demo]["json"]["ParserParameters"]["tradeTime"] == 5
                )
                assert (
                    self.demo_data[demo]["json"]["ParserParameters"]["roundBuyStyle"]
                    == "hltv"
                )
                assert (
                    self.demo_data[demo]["json"]["ParserParameters"]["parseRate"] == 256
                )

    def test_frames(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    assert len(r["frames"]) > 0

    def test_player_counts(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["gameRounds"]:
                    for f in r["frames"]:
                        assert len(f["T"]["players"]) == 5
                        assert len(f["CT"]["players"]) == 5

    def _count_deaths(self, json):
        total_deaths = 0
        for r in json["gameRounds"]:
            for _ in r["kills"]:
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
        for r in json["gameRounds"]:
            for k in r["kills"]:
                if not k["isTeamkill"] and not k["isSuicide"]:
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
        for r in json["gameRounds"]:
            for k in r["kills"]:
                if k["isTeamkill"]:
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
        for r in json["gameRounds"]:
            for k in r["kills"]:
                if k["isFirstKill"]:
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
        for r in json["gameRounds"]:
            for k in r["Kills"]:
                if k["isHeadshot"]:
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
        for r in json["gameRounds"]:
            for k in r["kills"]:
                if k["assisterName"] and (k["assisterTeam"] != k["victimTeam"]):
                    total_ast += 1
                if (
                    (k["flashThrowerName"] != k["assisterName"])
                    and (k["flashThrowerTeam"] != k["victimTeam"])
                    and (k["flashThrowerName"] is not None)
                ):
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

    def _count_flash_assists(self, json):
        total_flash_ast = 0
        for r in json["gameRounds"]:
            for k in r["kills"]:
                if k["flashThrowerName"] and (k["flashThrowerTeam"] != k["victimTeam"]):
                    total_flash_ast += 1
        return total_flash_ast

    def test_parsed_flash_assists(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_flash_ast = self._count_flash_assists(self.demo_data[demo]["json"])
                real_flash_ast = self.demo_data[demo]["totalFlashAssists"]
                print(
                    "[{0}] Parsed {1} flash assists, real flash assists are {2}".format(
                        demo, demo_flash_ast, real_flash_ast
                    )
                )
                assert demo_flash_ast == real_flash_ast

    def test_parsed_roundendreasons(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for i, r in enumerate(self.demo_data[demo]["json"]["gameRounds"]):
                    assert (
                        r["roundEndReason"]
                        == self.demo_data[demo]["roundEndReasons"][i]
                    )

    def _count_enemies_flashed(self, json):
        total_flashed = 0
        for r in json["gameRounds"]:
            if r["flashes"]:
                for f in r["flashes"]:
                    # Use 1.5 seconds as cutoff for "enemies flashed"
                    if (
                        (f["attackerTeam"] != f["playerTeam"])
                        and ((f["playerSide"] == "T") or (f["playerSide"] == "CT"))
                        and (f["flashDuration"] > 1.5)
                    ):
                        total_flashed += 1
        return total_flashed

    def test_parsed_enemies_flashed(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_enemies_flashed = self._count_enemies_flashed(
                    self.demo_data[demo]["json"]
                )
                real_enemies_flashed = self.demo_data[demo]["enemiesFlashed"]
                print(
                    "[{0}] Parsed {1} enemies flashed, real enemies flashed are {2}".format(
                        demo, demo_enemies_flashed, real_enemies_flashed
                    )
                )
                assert demo_enemies_flashed == real_enemies_flashed

    def _sum_util_dmg(self, json):
        util_dmg = 0
        for r in json["gameRounds"]:
            for dmg in r["damages"]:
                if (
                    dmg["weapon"] in ["HE Grenade", "Molotov", "Incendiary Grenade"]
                    and dmg["attackerTeam"] != dmg["victimTeam"]
                ):
                    util_dmg += dmg["hpDamageTaken"]
        return util_dmg

    def test_parsed_util_dmg(self):
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                demo_util_dmg = self._sum_util_dmg(self.demo_data[demo]["json"])
                util_dmg = self.demo_data[demo]["utilityDamage"]
                print(
                    "[{0}] Parsed {1} util dmg, real util dmg is {2}".format(
                        demo, demo_util_dmg, util_dmg
                    )
                )
                assert demo_util_dmg < util_dmg + 30
                assert demo_util_dmg > util_dmg - 30

    def test_event_ticks(self):
        """Tests to see if all events/frames occur within a round"""
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["GameRounds"]:
                    start_tick = r["StartTick"]
                    end_tick = r["EndOfficialTick"]
                    if r["Kills"] is not None:
                        for e in r["Kills"]:
                            assert e["Tick"] >= start_tick and e["Tick"] <= end_tick
                    if r["Damages"] is not None:
                        for e in r["Damages"]:
                            assert e["Tick"] >= start_tick and e["Tick"] <= end_tick
                    if r["BombEvents"] is not None:
                        for e in r["BombEvents"]:
                            assert e["Tick"] >= start_tick and e["Tick"] <= end_tick
                    if r["WeaponFires"] is not None:
                        for e in r["WeaponFires"]:
                            assert e["Tick"] >= start_tick and e["Tick"] <= end_tick
                    if r["Grenades"] is not None:
                        for e in r["Grenades"]:
                            assert (
                                e["ThrowTick"] >= start_tick
                                and e["DestroyTick"] <= end_tick
                            )
                            assert e["ThrowTick"] <= e["DestroyTick"]
                    if r["Flashes"] is not None:
                        for e in r["Flashes"]:
                            assert e["Tick"] >= start_tick and e["Tick"] <= end_tick
                    # Technically frames could happen outside...shouldn't be a big deal
                    # if r["Frames"] is not None:
                    #    for e in r["Frames"]:
                    #        assert e["Tick"] >= start_tick and e["Tick"] <= end_tick

    def test_defuse_round_end(self):
        """Tests to see if on bomb defuse round ends that the last action is a bomb defuse"""
        for demo in self.demo_data:
            if self.demo_data[demo]["useForTests"]:
                for r in self.demo_data[demo]["json"]["GameRounds"]:
                    if r["RoundEndReason"] == "BombDefused":
                        assert r["BombEvents"][-1]["BombAction"] == "defuse"
