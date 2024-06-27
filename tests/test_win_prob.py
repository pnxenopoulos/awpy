"""Tests Win Probability module."""

import pytest

from awpy import Demo
from awpy.stats import win_probability

class TestWinProbability:
    """Tests the win probability calculations.
    
    https://www.hltv.org/matches/2369248/natus-vincere-vs-virtuspro-pgl-cs2-major-copenhagen-2024-europe-rmr-closed-qualifier-a
    """

    @classmethod
    def setup_class(cls):
        """
        Setup method called before any tests are run.
        Initializes the Demo object and random weights for testing.
        """
        cls.demo = Demo(file='tests/natus-vincere-vs-virtus-pro-m1-overpass.dem')  


    @classmethod
    def teardown_class(cls):
        """
        Teardown method called after all tests have run.
        """
        cls.demo = None


    def test_win_probability_symmetry(self):
        """Test to ensure P(CT Win) = 1 - P(T Win) at a given tick."""
        probabilities = win_probability(self.demo, 168200)
        for prob in probabilities:
            assert prob["CT_win_probability"] == pytest.approx(1 - prob["T_win_probability"], 0.01)


    def test_known_ct_sided_situation(self):
        """Test for a known heavily CT-sided situation."""
        probabilities = win_probability(self.demo, 168200)
        assert probabilities[0]["tick"] == 168200
        assert probabilities[0]["CT_win_probability"] > 0.7


    def test_prediction_count_matches_ticks(self):
        """Test that the number of predictions matches the number of ticks passed in."""
        ticks = [166100, 167023, 168200]
        probabilities = win_probability(self.demo, ticks)
        assert len(probabilities) == len(ticks)
