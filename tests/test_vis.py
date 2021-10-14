import pytest

from csgo.visualization.plot import (
    position_transform,
    plot_map,
    plot_nades,
    plot_positions,
    plot_round,
)


class TestVis:
    """Class to test CSGO data cleaning functions"""

    def test_position_scale(self):
        """Test position transforms"""
        assert type(position_transform("de_ancient", 0, "x")) == float
