"""Tests map control functionality."""
import pytest

from awpy.analytics.map_control import (
    _approx_neighbors,
    _bfs_helper,
    calc_frame_map_control_metric,
    calculate_round_map_control_metrics,
    graph_to_tile_neighbors,
)
from awpy.data import NAV_GRAPHS


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
        }
        self.isolated_tiles_inferno = [850]
        self.connected_tiles_inferno = [2641, 277]

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

    def test_approx_neighbors(self):
        """Tests _approx_neighbors.

        Simple sanity check to ensure function runs - Doesn't check
        on neighbors individually but instead asserts on
        size on TileNeighbors object
        """
        with pytest.raises(ValueError, match="Tile ID not found."):
            _approx_neighbors(map_name="de_inferno", source_tile_id=0)
        with pytest.raises(ValueError, match="Invalid n_neighbors value. Must be > 0."):
            _approx_neighbors(
                map_name="de_inferno",
                source_tile_id=self.connected_tiles_inferno[0],
                n_neighbors=0,
            )

        for tile in self.isolated_tiles_inferno + self.connected_tiles_inferno:
            cur_neighbors = _approx_neighbors(
                map_name="de_inferno", source_tile_id=tile
            )
            assert len(cur_neighbors) == 5

        for tile in self.isolated_tiles_inferno + self.connected_tiles_inferno:
            cur_neighbors = _approx_neighbors(
                map_name="de_inferno", source_tile_id=tile, n_neighbors=10
            )
            assert len(cur_neighbors) == 10

    def test_bfs_helper(self):
        """Tests _bfs_helper with a couple isolated CT positions.

        Simple sanity check to ensure function runs - Doesn't check
        on assert map control values idnividually and instead asserts on
        size on MapControlValues object
        """
        with pytest.raises(ValueError, match="Invalid max_depth value. Must be > 0."):
            _bfs_helper(
                map_name="de_inferno",
                current_tiles=self.isolated_tiles_inferno
                + self.connected_tiles_inferno,
                neighbor_info=graph_to_tile_neighbors(
                    list(NAV_GRAPHS["de_inferno"].edges)
                ),
                max_depth=0,
            )

        sanity_bfs_return = _bfs_helper(
            map_name="de_inferno",
            current_tiles=self.isolated_tiles_inferno + self.connected_tiles_inferno,
            neighbor_info=graph_to_tile_neighbors(list(NAV_GRAPHS["de_inferno"].edges)),
        )
        assert len(sanity_bfs_return.keys()) > 0

    def test_calculate_round_map_control_metrics(self):
        """Tests calculate_round_map_control_metrics with T 5v1 control scenario."""
        round_length = 50
        test_round = {
            "frames": [self.fake_frames["map_control_sanity_t_control"]] * round_length
        }
        with pytest.raises(ValueError, match="Map not found."):
            calculate_round_map_control_metrics(
                map_name="de_mock",
                round_data=test_round,
            )
        test_map_control_metric = calculate_round_map_control_metrics(
            map_name="de_inferno",
            round_data=test_round,
        )
        assert len(test_map_control_metric) == round_length

        for frame_metric in test_map_control_metric:
            assert frame_metric < 0.5  # Map Control is T sided
