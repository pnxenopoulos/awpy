import json
import pandas as pd
import pytest
import requests

from awpy.parser import DemoParser
from awpy.analytics.stats import player_stats


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

    def test_player_stats(self):
        """Tests player stats generation"""
        stats = player_stats(self.data["gameRounds"])
        assert stats["76561197995889730"]["kills"] == 19
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
        stats_df = player_stats(self.data["gameRounds"], return_type="df")
        assert type(stats_df) == pd.DataFrame
