"""Test the parser methods."""

import pandas as pd
import pytest
from demoparser2 import DemoParser

from awpy.parsers import remove_nonplay_ticks


@pytest.fixture(scope="class")
def hltv_demoparser() -> DemoParser:
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return DemoParser(file="tests/natus-vincere-vs-virtus-pro-m1-overpass.dem")


@pytest.fixture(scope="class")
def parsed_state() -> pd.DataFrame:
    """Creates mock parsed state to be filtered."""
    columns = [
        "is_freeze_period",
        "is_warmup_period",
        "is_terrorist_timeout",
        "is_ct_timeout",
        "is_technical_timeout",
        "is_waiting_for_resume",
        "is_match_started",
        "game_phase",
        "other_data",
    ]
    data = [
        [False, False, False, False, False, False, True, 2, "event1"],
        [True, False, False, False, False, False, True, 2, "nonplay1"],
        [False, True, False, False, False, False, True, 3, "nonplay2"],
        [False, False, False, False, False, False, True, 3, "event2"],
        [False, False, False, False, False, False, True, 1, "nonplay3"],
    ]
    return pd.DataFrame(data, columns=columns)


class TestParsers:
    """Tests parser methods."""

    def test_remove_nonplay_ticks_bad_cols(self):
        """Tests that we raise an error if we are missing the necessary columns."""
        with pytest.raises(
            ValueError, match="is_freeze_period not found in dataframe."
        ):
            remove_nonplay_ticks(pd.DataFrame())

    def test_remove_nonplay_ticks(self, parsed_state: pd.DataFrame):
        """Tests that we filter out non-play ticks."""
        filtered_df = remove_nonplay_ticks(parsed_state)
        assert len(filtered_df) == 2
        assert "event1" in filtered_df["other_data"].to_numpy()
        assert "event2" in filtered_df["other_data"].to_numpy()
