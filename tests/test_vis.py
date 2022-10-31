import os
import matplotlib
from awpy.visualization.plot import (
    position_transform,
    position_transform_all,
    plot_map,
    plot_nades,
    plot_positions,
    plot_round,
)


class TestVis:
    """Class to test CSGO data cleaning functions"""

    def test_position_scale(self):
        """Test position transforms"""
        assert isinstance(position_transform("de_ancient", 0, "x"), float)
        assert isinstance(position_transform("de_ancient", 0, "y"), float)
        assert position_transform("de_ancient", 0, "scale") is None

    def test_position_transform_all(self):
        """Test position_transform_all"""
        map_name = "de_nuke"
        pos = (1000, 500, 200)
        transformed = position_transform_all(map_name, pos)
        assert isinstance(transformed, tuple)
        assert len(transformed) == 3
        assert isinstance(transformed[1], float)
        pos2 = (1000, 500, -600)
        transformed2 = position_transform_all(map_name, pos2)
        assert transformed[1] == transformed2[1] - 1024

    def test_plot_map(self):
        """Test plot map"""
        fig, axis = plot_map(map_name="de_ancient")
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)
        fig, axis = plot_map(map_name="de_anubis", map_type="simplerader")
        fig, axis = plot_map(map_name="de_vertigo", map_type="simplerader")

    def test_plot_positions(self):
        """Test plot positions"""
        fig, axis = plot_positions()
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)

    def test_plot_round(self):
        """Test plot round"""
        filename = "test.gif"
        frames = [
            {
                "bomb": False,
                "t": {"players": []},
                "ct": {"players": [{"hp": 100, "x": 0, "y": 0}]},
            }
        ]
        assert not os.path.exists(filename)
        assert plot_round(filename, frames)
        assert os.path.exists(filename)
        os.remove(filename)

    def test_plot_nades(self):
        """Test plot nades"""
        fig, axis = plot_nades([])
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)
