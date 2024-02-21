"""Test the conversion methods."""

import pandas as pd

from awpy.converters import (
    map_bombsites,
)


class TestConverters:
    """Tests conversion methods."""

    def test_map_bombsites(self):
        """Test the map_bombsites method."""
        series = pd.Series([318, 401, 412])
        expected = pd.Series(["A", "B", None])
        result = map_bombsites(series)
        pd.testing.assert_series_equal(result, expected)
