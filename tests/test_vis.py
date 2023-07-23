"""Tests visualization module."""
import os
from unittest.mock import MagicMock, patch

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from awpy.types import PlotPosition
from awpy.visualization import AWPY_TMP_FOLDER
from awpy.visualization.plot import (
    plot_map,
    plot_nades,
    plot_positions,
    plot_round,
    plot_round_map_control,
    position_transform,
    position_transform_all,
)


class TestVis:
    """Class to test CSGO data cleaning functions."""

    def setup_class(self):
        """Sets up class by defining test image name."""
        self.filename = "test.gif"

    def teardown_class(self):
        """Set parser to none."""
        os.remove(self.filename)

    def test_position_scale(self):
        """Test position transforms."""
        assert isinstance(position_transform("de_ancient", 0, "x"), float)
        assert isinstance(position_transform("de_ancient", 0, "y"), float)
        with pytest.raises(ValueError, match="'axis' has to be 'x' or 'y' not "):
            position_transform("de_ancient", 0, "scale")

    def test_position_transform_all(self):
        """Test position_transform_all."""
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
        """Test plot map."""
        # Test original with and withouzt z_cutoff
        fig, axis = plot_map(map_name="de_ancient")
        assert isinstance(fig, Figure)
        assert isinstance(axis, Axes)
        fig, axis = plot_map(map_name="de_vertigo")

        # Test simpleradar with and withouzt z_cutoff
        fig, axis = plot_map(map_name="de_ancient", map_type="simplerader")
        fig, axis = plot_map(map_name="de_vertigo", map_type="simplerader", dark=True)

        # Test what happens when simpleradar is missing
        fig, axis = plot_map(map_name="de_anubis", map_type="simplerader")
        # Currently there is no map that has a z_cutoff but is missing simpleradar

    @patch("awpy.visualization.plot.Axes.scatter")
    def test_plot_positions(self, scatter_mock: MagicMock):
        """Test plot positions."""
        pos1 = PlotPosition((1, 2), "red", "X", 1.0, 1.0)
        pos2 = PlotPosition((2, 1), "blue", "8", 0.4, 0.3)
        fig, axis = plot_positions(
            positions=[pos1, pos2],
            apply_transformation=True,
        )
        assert isinstance(fig, Figure)
        assert isinstance(axis, Axes)
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
        """Test plot round."""
        frames = [
            {
                "bomb": {"x": 1890, "y": 74, "z": 1613.03125},
                "t": {"players": []},
                "ct": {"players": [{"hp": 100, "x": 0, "y": 0}]},
            },
            {
                "bomb": {"x": 1890, "y": 74, "z": 1613.03125},
                "t": {"players": [{"hp": 0, "x": 0, "y": 0}]},
                "ct": {"players": []},
            },
        ]
        assert not os.path.exists(self.filename)
        assert plot_round(self.filename, frames)
        assert os.path.exists(self.filename)
        with patch("awpy.visualization.plot.plot_positions") as plot_positions_mock:
            plot_positions_mock.return_value = plt.subplots()
            plot_round(self.filename, frames)
            assert plot_positions_mock.call_count == 2
            plot_positions_mock.assert_called_with(
                positions=[
                    PlotPosition(
                        (
                            position_transform("de_ancient", 1890, "x"),
                            position_transform("de_ancient", 74, "y"),
                        ),
                        "orange",
                        "8",
                    ),
                    PlotPosition(
                        (
                            position_transform("de_ancient", 0, "x"),
                            position_transform("de_ancient", 0, "y"),
                        ),
                        "red",
                        "x",
                    ),
                ],
                map_name="de_ancient",
                map_type="original",
                dark=False,
            )

    def test_plot_nades(self):
        """Test plot nades."""
        nades_to_plot = [
            "Flashbang",
            "HE Grenade",
            "Smoke Grenade",
            "Molotov",
            "Incendiary Grenade",
        ]
        game_rounds = [
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
        assert isinstance(fig, mpl.figure.Figure)
        assert isinstance(axis, mpl.axes.SubplotBase)
        fig, axis = plot_nades(game_rounds, side="CT", nades=nades_to_plot)
        with patch("awpy.visualization.plot.Axes.scatter") as scatter_mock, patch(
            "awpy.visualization.plot.Axes.plot"
        ) as plot_mock:
            fig, axis = plot_nades(game_rounds, side="CT", nades=nades_to_plot)
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

    def test_plot_round_map_control(self):
        """Test plot_round_map_control."""
        fake_alive_player = {
            "x": -42.51047897338867,
            "y": 868.4791870117188,
            "z": 54.92256546020508,
            "isAlive": True,
        }
        fake_frame = {
            "t": {"players": [fake_alive_player.copy()] * 5},
            "ct": {"players": [fake_alive_player.copy()]},
        }

        round_length = 50
        test_round = {"frames": [fake_frame] * round_length}

        test_filename = "map_control_test.gif"

        bool_returned = plot_round_map_control(
            test_filename, "de_inferno", test_round, plot_type="players"
        )

        assert bool_returned
        assert os.path.isdir(AWPY_TMP_FOLDER)
        assert len(os.listdir(AWPY_TMP_FOLDER)) > 0

        awpy_tmp_files = set(os.listdir(AWPY_TMP_FOLDER))

        for i in range(round_length):
            filename = "frame_" + str(i)
            filepath = f"{AWPY_TMP_FOLDER}/{filename}.png"

            # Assert temp frame file exists and size > 0 bytes
            assert filename + ".png" in awpy_tmp_files
            assert os.stat(filepath).st_size > 0

        # Assert gif is created and size > 0 bytes
        assert os.stat(test_filename).st_size > 0
