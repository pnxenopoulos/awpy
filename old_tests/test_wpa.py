"""Tests WPA module."""
import pytest

from awpy.analytics.wpa import round_win_probability, state_win_probability
from awpy.parser import DemoParser


class TestWPA:
    """Class to test WPA.

    Uses:
    www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser."""
        self.parser = DemoParser(demofile="tests/default.dem", log=True, parse_rate=256)
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none."""
        self.parser = None
        self.data = None

    def test_state_win_probability(self):
        """Tests state_win_probability."""
        my_model = 0
        with pytest.raises(NotImplementedError):
            state_win_probability(self.data["gameRounds"][7]["frames"][0], my_model)

    def test_round_win_probability(self):
        """Tests round_win_probability."""
        with pytest.raises(NotImplementedError):
            round_win_probability(5, 2, "de_inferno")
