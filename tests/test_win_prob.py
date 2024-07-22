"""Test the win probability module."""

import pytest
import pandas as pd
from awpy import Demo
from awpy.stats import win_probability


@pytest.fixture(scope="class")
def hltv_demo() -> Demo:
    """Test Demo for an HLTV demo.

    Teams: Natus Vincere vs Virtus Pro (de_overpass)
    Event: PGL CS2 Major Copenhagen 2024 Europe RMR Closed Qualifier A (CS2)
    Source: HLTV
    Link: https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return Demo(file='tests/natus-vincere-vs-virtus-pro-m1-overpass.dem')


class TestWinProbability:
    """Tests win probability module."""

    def test_win_probability_symmetry(self, hltv_demo: Demo):
        """Tests to ensure P(CT Win) + P(T Win) = 1 at a given tick."""
        probabilities = win_probability(hltv_demo, 168200)
        assert isinstance(probabilities, pd.DataFrame)
        assert len(probabilities) == 1
        assert probabilities["CT_win_probability"].iloc[0] + probabilities["T_win_probability"].iloc[0] == pytest.approx(1.0)

    def test_known_ct_sided_situation(self, hltv_demo: Demo):
        """Tests for a known heavily CT-sided situation."""
        probabilities = win_probability(hltv_demo, 168200)
        assert probabilities["tick"].iloc[0] == 168200
        assert probabilities["CT_win_probability"].iloc[0] > 0.7

    def test_prediction_count_matches_ticks(self, hltv_demo: Demo):
        """Tests that the number of predictions matches the number of ticks passed in."""
        ticks = [166100, 167023, 168200]
        probabilities = win_probability(hltv_demo, ticks)
        assert len(probabilities) == len(ticks)
        assert all(probabilities["tick"].tolist() == ticks)

    def test_win_probability_dataframe_structure(self, hltv_demo: Demo):
        """Tests the structure of the returned DataFrame."""
        probabilities = win_probability(hltv_demo, [168200, 169000])
        assert isinstance(probabilities, pd.DataFrame)
        assert set(probabilities.columns) == {"tick", "CT_win_probability", "T_win_probability"}
        assert len(probabilities) == 2

    def test_win_probability_range(self, hltv_demo: Demo):
        """Tests that probabilities are within the valid range [0, 1]."""
        probabilities = win_probability(hltv_demo, [168200, 169000, 170000])
        assert all(0 <= prob <= 1 for prob in probabilities["CT_win_probability"])
        assert all(0 <= prob <= 1 for prob in probabilities["T_win_probability"])

    def test_win_probability_single_tick(self, hltv_demo: Demo):
        """Tests win probability calculation for a single tick."""
        probabilities = win_probability(hltv_demo, 168200)
        assert isinstance(probabilities, pd.DataFrame)
        assert len(probabilities) == 1
        assert probabilities["tick"].iloc[0] == 168200
