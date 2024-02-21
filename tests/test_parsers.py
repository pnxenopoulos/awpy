"""Test the parser methods."""

import pandas as pd
import pytest
from demoparser2 import DemoParser

from awpy.parsers import filter_out_nonplay_ticks


@pytest.fixture(scope="class")
def hltv_demoparser() -> DemoParser:
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return DemoParser(file="tests/natus-vincere-vs-virtus-pro-m1-overpass.dem")


class TestParsers:
    """Tests parser methods."""

    def test_filter_out_nonplay_ticks_bad_cols(self):
        """Tests that we raise an error if we are missing the necessary columns."""
        with pytest.raises(
            ValueError, match="is_freeze_period not found in dataframe."
        ):
            filter_out_nonplay_ticks(pd.DataFrame())
