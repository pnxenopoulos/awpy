"""Tests Win Probability module."""

import pytest
from awpy import Demo
from awpy.stats import win_probability

@pytest.fixture(scope="class")
def demo():
    """
    Fixture to create and return a Demo object.
    """
    return Demo(file='tests/natus-vincere-vs-virtus-pro-m1-overpass.dem')

class TestWinProbability:
    """Test win probability module.

    Teams: Natus Vincere vs Virtus Pro (de_overpass)
    Event: PGL CS2 Major Copenhagen 2024 Europe RMR Closed Qualifier A (CS2)
    Source: HLTV
    Link: https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """


    def test_win_probability_symmetry(self, demo):
        """Test to ensure P(CT Win) + P(T Win) = 1 at a given tick."""
        probabilities = win_probability(demo, 168200)
        for prob in probabilities:
            assert prob["CT_win_probability"] + prob["T_win_probability"] == pytest.approx(1.0)

    def test_known_ct_sided_situation(self, demo):
        """Test for a known heavily CT-sided situation."""
        probabilities = win_probability(demo, 168200)
        assert probabilities[0]["tick"] == 168200
        assert probabilities[0]["CT_win_probability"] > 0.7

    def test_prediction_count_matches_ticks(self, demo):
        """Test that the number of predictions matches the number of ticks passed in."""
        ticks = [166100, 167023, 168200]
        probabilities = win_probability(demo, ticks)
        assert len(probabilities) == len(ticks)
