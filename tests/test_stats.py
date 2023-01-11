import os
import json
import pandas as pd
import requests

from awpy.parser import DemoParser
from awpy.analytics.stats import player_stats


class TestStats:
    """Class to test the statistics functions.
    Uses https://www.hltv.org/matches/2337844/astralis-vs-liquid-blast-pro-series-global-final-2019.
    """

    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        with open("tests/test_data.json", encoding="utf-8") as f:
            self.demo_data = json.load(f)
        r = requests.get(self.demo_data["astralis-vs-liquid-m2-nuke"]["url"])
        open("astralis-vs-liquid-m2-nuke" + ".dem", "wb").write(r.content)
        self.parser = DemoParser(
            demofile="astralis-vs-liquid-m2-nuke.dem",
            demo_id="test",
            parse_rate=128,
            parse_frames=True,
        )
        self.data = self.parser.parse(clean=True)

    def teardown_class(self):
        """Set parser to none"""
        self.parser = None
        self.data = None
        files_in_directory = os.listdir()
        filtered_files = [
            file
            for file in files_in_directory
            if file.endswith(".dem") or file.endswith(".json")
        ]
        if len(filtered_files) > 0:
            for f in filtered_files:
                os.remove(f)

    def test_player_stats(self):
        """Tests player stats generation"""
        stats = player_stats(self.data["gameRounds"])
        assert stats["76561197995889730 - nitr0"]["kills"] == 19
        assert stats["76561197995889730 - nitr0"]["assists"] == 1
        assert stats["76561197995889730 - nitr0"]["flashAssists"] == 0
        assert stats["76561197995889730 - nitr0"]["deaths"] == 17
        assert stats["76561197995889730 - nitr0"]["adr"] == 63.6
        assert stats["76561197995889730 - nitr0"]["rating"] == 1.03
        assert stats["76561197995889730 - nitr0"]["kast"] == 67.9
        assert stats["76561197995889730 - nitr0"]["firstKills"] == 2
        assert stats["76561197995889730 - nitr0"]["firstDeaths"] == 2
        assert stats["76561197995889730 - nitr0"]["teamName"] == "Team Liquid"
        assert stats["76561197995889730 - nitr0"]["playerName"] == "nitr0"
        stats_df = player_stats(self.data["gameRounds"], return_type="df")
        assert isinstance(stats_df, pd.DataFrame)

        test_rounds = [
            {
                # "roundNum": 1,
                # "isWarmup": False,
                # "startTick": 17374,
                # "freezeTimeEndTick": 18898,
                # "endTick": 26021,
                # "endOfficialTick": 26910,
                # "bombPlantTick": 22924,
                # "tScore": 0,
                # "ctScore": 0,
                # "endTScore": 1,
                # "endCTScore": 0,
                # "ctTeam": "team_-Fuchshenger",
                # "tTeam": "team_Sunk3r",
                # "winningSide": "T",
                # "winningTeam": "team_Sunk3r",
                # "losingTeam": "team_-Fuchshenger",
                # "roundEndReason": "TerroristsWin",
                # "ctFreezeTimeEndEqVal": 3850,
                # "ctRoundStartEqVal": 1000,
                # "ctRoundSpendMoney": 3500,
                # "ctBuyType": "Full Eco",
                # "tFreezeTimeEndEqVal": 4250,
                # "tRoundStartEqVal": 1000,
                # "tRoundSpendMoney": 3250,
                # "tBuyType": "Full Eco",
                "ctSide": {
                    "teamName": "team_-Fuchshenger",
                    "players": [
                        {"playerName": "-Fuchshenger", "steamID": 76561199002916187},
                        {"playerName": "MAKARxJESUS", "steamID": 76561198144899828},
                        {"playerName": "XCSy", "steamID": 76561198366282668},
                        {"playerName": "__NIKI_", "steamID": 76561198318595189},
                        {"playerName": "Flubykiller", "steamID": 76561198118383015},
                    ],
                },
                "tSide": {
                    "teamName": "team_Sunk3r",
                    "players": [
                        {"playerName": "Sunk3r", "steamID": 76561198173639909},
                        {"playerName": "SlaynThemAll", "steamID": 76561198156162722},
                        {"playerName": "Afflic", "steamID": 76561198256616745},
                        {"playerName": "yngtired", "steamID": 76561198853008998},
                        {"playerName": "JanEric1", "steamID": 76561198049899734},
                    ],
                },
                "kills": [
                    {
                        "tick": 21548,
                        "seconds": 20.866141732283463,
                        "clockTime": "01:35",
                        "attackerSteamID": 76561198049899734,
                        "attackerName": "JanEric1",
                        "attackerTeam": "team_Sunk3r",
                        "attackerSide": "T",
                        "attackerX": 1623.4302978515625,
                        "attackerY": 1222.76708984375,
                        "attackerZ": 161.6575927734375,
                        "attackerViewX": 337.1978759765625,
                        "attackerViewY": 0.274658203125,
                        "victimSteamID": 76561198049899734,
                        "victimName": "JanEric1",
                        "victimTeam": "team_Sunk3r",
                        "victimSide": "T",
                        "victimX": 1623.4302978515625,
                        "victimY": 1222.76708984375,
                        "victimZ": 161.6575927734375,
                        "victimViewX": 337.1978759765625,
                        "victimViewY": 0.274658203125,
                        "assisterSteamID": 76561198173639909,
                        "assisterName": "Sunk3r",
                        "assisterTeam": "team_Sunk3r",
                        "assisterSide": "T",
                        "isSuicide": True,
                        "isTeamkill": False,
                        "isWallbang": False,
                        "penetratedObjects": 0,
                        "isFirstKill": True,
                        "isHeadshot": True,
                        "victimBlinded": False,
                        "attackerBlinded": False,
                        "flashThrowerSteamID": None,
                        "flashThrowerName": None,
                        "flashThrowerTeam": None,
                        "flashThrowerSide": None,
                        "noScope": False,
                        "thruSmoke": False,
                        "distance": 714.3147783842128,
                        "isTrade": False,
                        "playerTradedName": None,
                        "playerTradedTeam": None,
                        "playerTradedSteamID": None,
                        "weapon": "Glock-18",
                        "weaponClass": "Pistols",
                    },
                ],
                "damages": [],
                "weaponFires": [],
                "flashes": [],
                "grenades": [],
                "bombEvents": [],
            }
        ]
        stats = player_stats(test_rounds)
        assert stats["76561198049899734 - JanEric1"]["suicides"] == 1
