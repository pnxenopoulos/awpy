import json
import pandas as pd
import pytest
import requests
import numbers
from math import isclose

from awpy.parser import DemoParser
from awpy.analytics.stats import player_stats, other_side


def weighted_avg(
    metric: str, weighting_metric: str, stats_t: dict, stats_ct: dict
) -> float:
    """Calculates the weighted average between stats_t and stats_ct for the value of
    'metric' weighted by 'weighting_metric'"""
    return (
        (stats_t[metric] * stats_t[weighting_metric])
        + (stats_ct[metric] * stats_ct[weighting_metric])
    ) / (stats_t[weighting_metric] + stats_ct[weighting_metric])


class TestStats:
    """Class to test the statistics functions.
    Uses https://www.hltv.org/matches/2337844/astralis-vs-liquid-blast-pro-series-global-final-2019.
    """

    def setup_class(self):
        """Sets up class by defining the parser, filters, and dataframes."""
        with open("tests/test_data.json") as f:
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

    def test_other_side(self):
        """Tests other side"""
        assert other_side("T") == "CT"
        assert other_side("t") == "ct"
        assert other_side("CT") == "T"
        assert other_side("ct") == "t"

    def test_player_stats(self):
        """Tests player stats generation"""
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
        assert stats["76561197990682262"]["1v5attempts"] == 5
        assert stats["76561197990682262"]["1v5success"] == 0
        assert stats["76561197990682262"]["1v1attempts"] == 2
        assert stats["76561197990682262"]["1v1success"] == 2
        assert stats["76561197990682262"]["5kills"] == 0

        assert stats["76561197987713664"]["playerName"] == "device"
        assert stats["76561197987713664"]["5kills"] == 1
        assert stats["76561197987713664"]["tradeKills"] == 5
        assert stats["76561197987713664"]["tradedDeaths"] == 3

        stats_df = player_stats(self.data["gameRounds"], return_type="df")
        assert type(stats_df) == pd.DataFrame

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
                    assert total_value == t_value and total_value == ct_value
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
