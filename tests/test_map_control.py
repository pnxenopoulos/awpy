"""Tests map control functionality."""
import pytest

from awpy.analytics.map_control import calc_frame_map_control_metric


class TestMapControl:
    """Class to test the map control-related functions."""

    def setup_class(self):
        """Setup class by defining custom Map Control object."""
        self.fake_alive_player = {
            "x": -42.51047897338867,
            "y": 868.4791870117188,
            "z": 54.92256546020508,
            "isAlive": True,
        }
        self.fake_dead_player = {
            "x": -42.51047897338867,
            "y": 868.4791870117188,
            "z": 54.92256546020508,
            "isAlive": False,
        }
        self.fake_frames = {
            "map_control_sanity_t_control": {
                "t": {"players": [self.fake_alive_player.copy()] * 5},
                "ct": {"players": [self.fake_alive_player.copy()]},
            },
            "map_control_sanity_ct_control": {
                "ct": {"players": [self.fake_alive_player.copy()] * 5},
                "t": {"players": [self.fake_alive_player.copy()]},
            },
            "map_control_null_5v0": {
                "t": {"players": [self.fake_alive_player.copy()] * 5},
                "ct": {"players": []},
            },
            "map_control_null_1v0": {
                "t": {"players": [self.fake_alive_player.copy()]},
                "ct": {"players": []},
            },
            "map_control_dead_5v5": {
                "t": {"players": [self.fake_dead_player.copy()] * 5},
                "ct": {"players": [self.fake_dead_player.copy()] * 5},
            },
        }

    def test_calc_frame_map_control_metric_sanity_t_control(self):
        """Tests calc_frame_map_control_metric with T 5v1 scenario."""
        with pytest.raises(ValueError, match="Map not found."):
            calc_frame_map_control_metric(
                map_name="de_mock",
                frame=self.fake_frames["map_control_sanity_t_control"],
            )
        test_map_control_metric = calc_frame_map_control_metric(
            map_name="de_inferno",
            frame=self.fake_frames["map_control_sanity_t_control"],
        )
        assert test_map_control_metric < 0.5  # Map Control is T sided

    def test_calc_frame_map_control_metric_sanity_ct_control(self):
        """Tests calc_frame_map_control_metric with CT 5v1 scenario."""
        with pytest.raises(ValueError, match="Map not found."):
            calc_frame_map_control_metric(
                map_name="de_mock",
                frame=self.fake_frames["map_control_sanity_ct_control"],
            )
        test_map_control_metric = calc_frame_map_control_metric(
            map_name="de_inferno",
            frame=self.fake_frames["map_control_sanity_ct_control"],
        )
        assert test_map_control_metric > 0.5  # Map Control is CT sided

    def test_calc_frame_map_control_metric_null_5v0(self):
        """Tests calc_frame_map_control_metric with T 5v0 scenario."""
        with pytest.raises(ValueError, match="Map not found."):
            calc_frame_map_control_metric(
                map_name="de_mock", frame=self.fake_frames["map_control_null_5v0"]
            )
        test_mc_metric = calc_frame_map_control_metric(
            map_name="de_inferno", frame=self.fake_frames["map_control_null_5v0"]
        )
        assert test_mc_metric == 0  # Map Control is complete T

    def test_calc_frame_map_control_metric_null_1v0(self):
        """Tests calc_frame_map_control_metric with T 1v0 scenario."""
        with pytest.raises(ValueError, match="Map not found."):
            calc_frame_map_control_metric(
                map_name="de_mock", frame=self.fake_frames["map_control_null_1v0"]
            )
        test_mc_metric = calc_frame_map_control_metric(
            map_name="de_inferno", frame=self.fake_frames["map_control_null_1v0"]
        )
        assert test_mc_metric == 0  # Map Control is complete T
