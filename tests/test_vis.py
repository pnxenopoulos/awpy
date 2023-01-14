import os
from unittest.mock import patch
import pytest
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
        with pytest.raises(ValueError):
            position_transform("de_ancient", 0, "scale")

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
        # Test original with and withouzt z_cutoff
        fig, axis = plot_map(map_name="de_ancient")
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)
        fig, axis = plot_map(map_name="de_vertigo")

        # Test simpleradar with and withouzt z_cutoff
        fig, axis = plot_map(map_name="de_ancient", map_type="simplerader")
        fig, axis = plot_map(map_name="de_vertigo", map_type="simplerader", dark=True)

        # Test what happens when simpleradar is missing
        fig, axis = plot_map(map_name="de_anubis", map_type="simplerader")
        # Currently there is no map that has a z_cutoff but is missing simpleradar

    @patch("awpy.visualization.plot.mpl.axes.Axes.scatter")
    def test_plot_positions(self, scatter_mock):
        """Test plot positions"""
        fig, axis = plot_positions()
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)
        fig, axis = plot_positions(
            positions=[(1, 2), (2, 1)],
            colors=["red", "blue"],
            markers=["X", "8"],
            alphas=[1.0, 0.4],
            sizes=[1.0, 0.3],
            apply_transformation=True,
        )
        # Should be called once for each list entry
        assert scatter_mock.call_count == 2
        # Second call should have been made with these arguments:
        scatter_mock.assert_called_with(
            x=position_transform("de_ancient", 2, "x"),
            y=position_transform("de_ancient", 1, "y"),
            c="blue",
            marker="8",
            alpha=0.4,
            s=0.3,
        )

    def test_plot_round(self):
        """Test plot round"""
        filename = "test.gif"
        frames = [
            {
                "bomb": {"x": 2890, "y": 74, "z": 1613.03125},
                "t": {"players": []},
                "ct": {"players": [{"hp": 100, "x": 0, "y": 0}]},
            },
            {
                "bomb": {},
                "t": {"players": [{"hp": 0, "x": 0, "y": 0}]},
                "ct": {"players": []},
            },
        ]
        assert not os.path.exists(filename)
        assert plot_round(filename, frames)
        assert os.path.exists(filename)
        with patch("awpy.visualization.plot.plot_positions") as plot_positions_mock:
            plot_positions_mock.return_value = matplotlib.pyplot.subplots()
            plot_round(filename, frames)
            assert plot_positions_mock.call_count == 2
            plot_positions_mock.assert_called_with(
                positions=[
                    (
                        position_transform("de_ancient", 0, "x"),
                        position_transform("de_ancient", 0, "y"),
                    )
                ],
                colors=["red"],
                markers=["x"],
                map_name="de_ancient",
                map_type="original",
                dark=False,
            )
        os.remove(filename)

    def test_plot_nades(self):
        """Test plot nades"""
        nades_to_plot = [
            "Flashbang",
            "HE Grenade",
            "Smoke Grenade",
            "Molotov",
            "Incendiary Grenade",
        ]
        gameRounds = [
            {
                "grenades": [
                    {
                        "throwerSide": "T",
                        "throwerX": 2422.34375,
                        "throwerY": 99.59375,
                        "grenadeType": "Smoke Grenade",
                        "grenadeX": 7.65625,
                        "grenadeY": 0.21875,
                    },
                    {
                        "throwerSide": "CT",
                        "throwerX": -644.28125,
                        "throwerY": -320.75,
                        "grenadeType": "Decoy Grenade",
                        "grenadeX": -590.625,
                        "grenadeY": -163.84375,
                    },
                    {
                        "throwerSide": "CT",
                        "throwerX": -644.28125,
                        "throwerY": -320.75,
                        "grenadeType": "Flashbang",
                        "grenadeX": -590.625,
                        "grenadeY": -163.84375,
                    },
                    {
                        "throwerSide": "CT",
                        "throwerX": -644.28125,
                        "throwerY": -320.75,
                        "grenadeType": "HE Grenade",
                        "grenadeX": -590.625,
                        "grenadeY": -163.84375,
                    },
                    {
                        "throwerSide": "CT",
                        "throwerX": -644.28125,
                        "throwerY": -320.75,
                        "grenadeType": "Smoke Grenade",
                        "grenadeX": -590.625,
                        "grenadeY": -163.84375,
                    },
                    {
                        "throwerSide": "CT",
                        "throwerX": -644.28125,
                        "throwerY": -320.75,
                        "grenadeType": "Molotov",
                        "grenadeX": -590.625,
                        "grenadeY": -163.84375,
                    },
                ]
            },
            {"grenades": []},
        ]

        fig, axis = plot_nades([])
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axis, matplotlib.axes.SubplotBase)
        fig, axis = plot_nades(gameRounds, side="CT", nades=nades_to_plot)
        with patch("awpy.visualization.plot.mpl.axes.Axes.scatter") as scatter_mock:
            with patch("awpy.visualization.plot.mpl.axes.Axes.plot") as plot_mock:
                fig, axis = plot_nades(gameRounds, side="CT", nades=nades_to_plot)
                # Only call it for valid grenades (not decay) from the correct side
                assert scatter_mock.call_count == 4
                assert plot_mock.call_count == 4
                plot_mock.assert_called_with(
                    [
                        position_transform("de_ancient", -644.28125, "x"),
                        position_transform("de_ancient", -590.625, "x"),
                    ],
                    [
                        position_transform("de_ancient", -320.75, "y"),
                        position_transform("de_ancient", -163.84375, "y"),
                    ],
                    color="red",
                )
                scatter_mock.assert_called_with(
                    position_transform("de_ancient", -590.625, "x"),
                    position_transform("de_ancient", -163.84375, "y"),
                    color="red",
                )
