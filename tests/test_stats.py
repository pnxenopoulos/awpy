"""Tests stats module."""
import numbers
from math import isclose

import pandas as pd

from awpy.analytics.stats import player_stats
from awpy.parser import DemoParser


def weighted_avg(
    metric: str, weighting_metric: str, stats_t: dict, stats_ct: dict
) -> float:
    """Calculates the weighted average.

    Between stats_t and stats_ct for the value of
    'metric' weighted by 'weighting_metric'.
    """
    return (
        (stats_t[metric] * stats_t[weighting_metric])
        + (stats_ct[metric] * stats_ct[weighting_metric])
    ) / (stats_t[weighting_metric] + stats_ct[weighting_metric])


class TestStats:
    """Class to test the statistics functions.

    Uses:
    https://www.hltv.org/matches/2337844/astralis-vs-liquid-blast-pro-series-global-final-2019.
    """

    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        self.parser = DemoParser(
            demofile="tests/astralis-vs-liquid-m2-nuke.dem",
            demo_id="test",
            parse_rate=128,
            parse_frames=True,
        )
        self.data = self.parser.parse(clean=True)

    def teardown_class(self):
        """Set parser to none."""
        self.parser = None
        self.data = None

    def test_player_stats_both_json(self):
        """Tests json generation of player stats for both sides."""
        stats = player_stats(self.data["gameRounds"])
        assert isinstance(stats, dict)
        assert stats["76561197995889730"]["kills"] == 19
        assert stats["76561197995889730"]["totalRounds"] == 28
        assert stats["76561197995889730"]["hs"] == 16
        assert stats["76561197995889730"]["assists"] == 1
        assert stats["76561197995889730"]["flashAssists"] == 0
        assert stats["76561197995889730"]["deaths"] == 17
        assert stats["76561197995889730"]["adr"] == 63.6
        assert stats["76561197995889730"]["rating"] == 1.03
        assert stats["76561197995889730"]["kast"] == 67.9
        assert stats["76561197995889730"]["firstKills"] == 2
        assert stats["76561197995889730"]["firstDeaths"] == 2
        assert stats["76561197995889730"]["teamName"] == "Team Liquid"
        assert stats["76561197995889730"]["playerName"] == "nitr0"

        assert stats["76561197990682262"]["playerName"] == "Xyp9x"
        assert stats["76561197990682262"]["attempts1v5"] == 5
        assert stats["76561197990682262"]["success1v5"] == 0
        assert stats["76561197990682262"]["attempts1v1"] == 2
        assert stats["76561197990682262"]["success1v1"] == 2
        assert stats["76561197990682262"]["kills5"] == 0

        assert stats["76561197987713664"]["playerName"] == "device"
        assert stats["76561197987713664"]["kills5"] == 1
        assert stats["76561197987713664"]["tradeKills"] == 5
        assert stats["76561197987713664"]["tradedDeaths"] == 5

    def test_player_stats_both_df(self):
        """Tests player stats generation for df."""
        stats_df = player_stats(self.data["gameRounds"], return_type="df")
        assert isinstance(stats_df, pd.DataFrame)

    def test_player_stats_ct(self):
        """Tests json generation of player stats for ct."""
        stats_ct = player_stats(self.data["gameRounds"], selected_side="ct")
        assert isinstance(stats_ct, dict)
        assert stats_ct["76561197995889730"]["kills"] == 14
        assert stats_ct["76561197995889730"]["totalRounds"] == 15
        assert stats_ct["76561197995889730"]["hs"] == 12
        assert stats_ct["76561197995889730"]["assists"] == 0
        assert stats_ct["76561197995889730"]["flashAssists"] == 0
        assert stats_ct["76561197995889730"]["deaths"] == 7
        assert stats_ct["76561197995889730"]["adr"] == 84.9
        assert stats_ct["76561197995889730"]["kast"] == 80.0
        assert stats_ct["76561197995889730"]["firstKills"] == 2
        assert stats_ct["76561197995889730"]["firstDeaths"] == 0
        assert stats_ct["76561197995889730"]["teamName"] == "Team Liquid"
        assert stats_ct["76561197995889730"]["playerName"] == "nitr0"

    def test_player_stats_t(self):
        """Tests json generation of player stats for t."""
        stats_t = player_stats(self.data["gameRounds"], selected_side="T")
        assert isinstance(stats_t, dict)
        assert stats_t["76561197995889730"]["kills"] == 5
        assert stats_t["76561197995889730"]["totalRounds"] == 13
        assert stats_t["76561197995889730"]["hs"] == 4
        assert stats_t["76561197995889730"]["assists"] == 1
        assert stats_t["76561197995889730"]["flashAssists"] == 0
        assert stats_t["76561197995889730"]["deaths"] == 10
        assert stats_t["76561197995889730"]["adr"] == 38.9
        assert stats_t["76561197995889730"]["kast"] == 53.8
        assert stats_t["76561197995889730"]["firstKills"] == 0
        assert stats_t["76561197995889730"]["firstDeaths"] == 2
        assert stats_t["76561197995889730"]["teamName"] == "Team Liquid"
        assert stats_t["76561197995889730"]["playerName"] == "nitr0"

    def test_player_stats_sum(self):
        """Tests that ct and t stats sum to total."""
        stats = player_stats(self.data["gameRounds"])
        stats_t = player_stats(self.data["gameRounds"], selected_side="T")
        stats_ct = player_stats(self.data["gameRounds"], selected_side="CT")
        for player in stats:
            for metric in stats[player]:
                total_value = stats[player][metric]
                t_value = stats_t[player][metric]
                ct_value = stats_ct[player][metric]
                # All numerical purely cummulative values should add up
                if isinstance(total_value, numbers.Number) and metric not in {
                    "kast",
                    "rating",
                    "adr",
                    "accuracy",
                    "isBot",
                    "kdr",
                    "hsPercent",
                    "steamID",
                }:
                    # Allow for slight deviation in case of rounding
                    assert isclose(total_value, (t_value + ct_value), abs_tol=0.11)
                elif metric in {"steamID", "isBot"}:
                    assert total_value == t_value
                    assert total_value == ct_value
                elif metric in {"playerName", "teamName"}:
                    assert total_value in {t_value, ct_value}
                elif metric in {"kast", "adr"}:
                    assert isclose(
                        total_value,
                        weighted_avg(
                            metric, "totalRounds", stats_t[player], stats_ct[player]
                        ),
                        abs_tol=0.11,
                    )
                elif metric == "hsPercent":
                    assert isclose(
                        total_value,
                        weighted_avg(
                            metric, "kills", stats_t[player], stats_ct[player]
                        ),
                        abs_tol=0.11,
                    )
                elif metric == "kdr":
                    assert isclose(
                        total_value,
                        weighted_avg(
                            metric, "deaths", stats_t[player], stats_ct[player]
                        ),
                        abs_tol=0.11,
                    )
                elif metric == "accuracy":
                    assert isclose(
                        total_value,
                        weighted_avg(
                            metric, "totalShots", stats_t[player], stats_ct[player]
                        ),
                        abs_tol=0.11,
                    )

    def test_suicides(self):
        """Test that suicides are parsed correctly."""
        test_rounds = [
            {
                "roundNum": 1,
                "isWarmup": False,
                "startTick": 17374,
                "freezeTimeEndTick": 18898,
                "endTick": 26021,
                "endOfficialTick": 26910,
                "bombPlantTick": 22924,
                "tScore": 0,
                "ctScore": 0,
                "endTScore": 1,
                "endCTScore": 0,
                "ctTeam": "team_-Fuchshenger",
                "tTeam": "team_Sunk3r",
                "winningSide": "T",
                "winningTeam": "team_Sunk3r",
                "losingTeam": "team_-Fuchshenger",
                "roundEndReason": "TerroristsWin",
                "ctFreezeTimeEndEqVal": 3850,
                "ctRoundStartEqVal": 1000,
                "ctRoundSpendMoney": 3500,
                "ctBuyType": "Full Eco",
                "tFreezeTimeEndEqVal": 4250,
                "tRoundStartEqVal": 1000,
                "tRoundSpendMoney": 3250,
                "tBuyType": "Full Eco",
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
        assert stats["76561198049899734"]["suicides"] == 1

    def test_player_timeout(self):
        """Test that timed out players do not crash."""
        test_rounds = [
            {
                "ctSide": {
                    "teamName": "team_-Fuchshenger",
                    "players": [
                        {"playerName": "-Fuchshenger", "steamID": 76561199002916187},
                    ],
                },
                "tSide": {
                    "teamName": "team_Sunk3r",
                    "players": [
                        {"playerName": "Sunk3r", "steamID": 76561198173639909},
                    ],
                },
                "kills": [],
                "damages": [],
                "weaponFires": [],
                "flashes": [],
                "grenades": [],
                "bombEvents": [],
            },
            {
                "ctSide": {
                    "teamName": "team_-Fuchshenger",
                    "players": [],
                },
                "tSide": {
                    "teamName": "team_Sunk3r",
                    "players": [
                        {"playerName": "Sunk3r", "steamID": 76561198173639909},
                    ],
                },
                "kills": [
                    {
                        "tick": 21548,
                        "seconds": 20.866141732283463,
                        "clockTime": "01:35",
                        "attackerSteamID": 76561199002916187,
                        "attackerName": "-Fuchshenger",
                        "attackerTeam": "team_Sunk3r",
                        "attackerSide": "T",
                        "attackerX": 1623.4302978515625,
                        "attackerY": 1222.76708984375,
                        "attackerZ": 161.6575927734375,
                        "attackerViewX": 337.1978759765625,
                        "attackerViewY": 0.274658203125,
                        "victimSteamID": 76561199002916187,
                        "victimName": "-Fuchshenger",
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
            },
        ]
        player_stats(test_rounds)

    def test_player_stats_none_player_before_clutch(self):
        """Tests that player stats handles None sides correctly.

        Especially in clutch initialization.
        """
        test_rounds = [
            {
                "roundNum": 1,
                "isWarmup": False,
                "startTick": 17374,
                "freezeTimeEndTick": 18898,
                "endTick": 26021,
                "endOfficialTick": 26910,
                "bombPlantTick": 22924,
                "tScore": 0,
                "ctScore": 0,
                "endTScore": 1,
                "endCTScore": 0,
                "ctTeam": "team_-Fuchshenger",
                "tTeam": "team_Sunk3r",
                "winningSide": "T",
                "winningTeam": "team_Sunk3r",
                "losingTeam": "team_-Fuchshenger",
                "roundEndReason": "TerroristsWin",
                "ctFreezeTimeEndEqVal": 3850,
                "ctRoundStartEqVal": 1000,
                "ctRoundSpendMoney": 3500,
                "ctBuyType": "Full Eco",
                "tFreezeTimeEndEqVal": 4250,
                "tRoundStartEqVal": 1000,
                "tRoundSpendMoney": 3250,
                "tBuyType": "Full Eco",
                "ctSide": {
                    "teamName": "team_-Fuchshenger",
                    "players": None,
                },
                "tSide": {
                    "teamName": "team_Sunk3r",
                    "players": None,
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
                        "victimSteamID": 76561198118383015,
                        "victimName": "Flubykiller",
                        "victimTeam": "team_Sunk3r",
                        "victimSide": "CT",
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
        player_stats(test_rounds)

    def test_player_stats_none_player_in_clutch(self):
        """Tests that player stats handles a side being None correctly in clutches."""
        test_rounds = [
            {
                "roundNum": 1,
                "isWarmup": False,
                "startTick": 17374,
                "freezeTimeEndTick": 18898,
                "endTick": 26021,
                "endOfficialTick": 26910,
                "bombPlantTick": 22924,
                "tScore": 0,
                "ctScore": 0,
                "endTScore": 1,
                "endCTScore": 0,
                "ctTeam": "team_-Fuchshenger",
                "tTeam": "team_Sunk3r",
                "winningSide": "T",
                "winningTeam": "team_Sunk3r",
                "losingTeam": "team_-Fuchshenger",
                "roundEndReason": "TerroristsWin",
                "ctFreezeTimeEndEqVal": 3850,
                "ctRoundStartEqVal": 1000,
                "ctRoundSpendMoney": 3500,
                "ctBuyType": "Full Eco",
                "tFreezeTimeEndEqVal": 4250,
                "tRoundStartEqVal": 1000,
                "tRoundSpendMoney": 3250,
                "tBuyType": "Full Eco",
                "ctSide": {
                    "teamName": "team_-Fuchshenger",
                    "players": [
                        {"playerName": "-Fuchshenger", "steamID": 76561199002916187},
                        {"playerName": "Flubykiller", "steamID": 76561198118383015},
                    ],
                },
                "tSide": {
                    "teamName": "team_Sunk3r",
                    "players": None,
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
                        "victimSteamID": 76561198118383015,
                        "victimName": "Flubykiller",
                        "victimTeam": "team_Sunk3r",
                        "victimSide": "CT",
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
        player_stats(test_rounds)
