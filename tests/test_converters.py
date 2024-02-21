"""Test the conversion methods."""

import pandas as pd

from awpy.converters import (
    map_bombsites,
    map_game_phase,
    map_hitgroup,
    map_round_end_reasons,
)


class TestConverters:
    """Tests conversion methods."""

    def test_map_bombsites(self):
        """Test the map_bombsites method."""
        series = pd.Series([318, 401, -1])
        expected = pd.Series(["A", "B", None])
        result = map_bombsites(series)
        pd.testing.assert_series_equal(result, expected)

    def test_map_hitgroup(self):
        """Test the map_hitgroup method."""
        series = pd.Series([0, 1, 2, 3, 4, 5, 6, 7, 8, 10, -1])
        expected = pd.Series(
            [
                "generic",
                "head",
                "chest",
                "stomach",
                "left arm",
                "right arm",
                "left leg",
                "right leg",
                "neck",
                "gear",
                None,
            ]
        )
        result = map_hitgroup(series)
        pd.testing.assert_series_equal(result, expected)

    def test_map_round_end_reasons(self):
        """Test the map_round_end_reasons method."""
        series = pd.Series(
            [0, 1, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, -1]
        )
        expected = pd.Series(
            [
                "still_in_progress",
                "target_bombed",
                "bomb_defused",
                "ct_win",
                "t_win",
                "draw",
                "hostages_rescued",
                "target_saved",
                "hostages_not_rescued",
                "t_not_escaped",
                "vip_not_escaped",
                "game_start",
                "t_surrender",
                "ct_surrender",
                "t_planted",
                "cts_reached_hostage",
                None,
            ]
        )
        result = map_round_end_reasons(series)
        pd.testing.assert_series_equal(result, expected)

    def test_map_game_phase(self):
        """Test the map_game_phase method."""
        series = pd.Series([0, 1, 2, 3, 4, 5, 6, 7, -1])
        expected = pd.Series(
            [
                "init",
                "pregame",
                "startgame",
                "preround",
                "teamwin",
                "restart",
                "stalemate",
                "gameover",
                None,
            ]
        )
        result = map_game_phase(series)
        pd.testing.assert_series_equal(result, expected)
