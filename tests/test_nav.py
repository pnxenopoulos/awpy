import pytest
import numpy as np

from csgo.data import NAV
from csgo.analytics.nav import (
    area_distance,
    find_closest_area,
    generate_position_token,
    point_distance,
    point_in_area,
)


class TestNav:
    """Class to test the nav-related functions."""

    def test_point_in_area(self):
        """Tests point in area"""
        with pytest.raises(ValueError):
            point_in_area(map_name="test", area_id=0, point=[0, 0, 0])
        with pytest.raises(ValueError):
            point_in_area(map_name="de_dust2", area_id=0, point=[0, 0, 0])
        with pytest.raises(ValueError):
            point_in_area(map_name="test", area_id=0, point=[0])
        avg_x = (
            NAV["de_dust2"][152]["northWestX"] + NAV["de_dust2"][152]["southEastX"]
        ) / 2
        avg_y = (
            NAV["de_dust2"][152]["northWestY"] + NAV["de_dust2"][152]["southEastY"]
        ) / 2
        avg_z = (
            NAV["de_dust2"][152]["northWestZ"] + NAV["de_dust2"][152]["southEastZ"]
        ) / 2
        assert point_in_area(
            map_name="de_dust2", area_id=152, point=[avg_x, avg_y, avg_z]
        )

    def test_find_area(self):
        """Tests find_area"""
        with pytest.raises(ValueError):
            find_closest_area(map_name="test", point=[0, 0, 0])
        with pytest.raises(ValueError):
            find_closest_area(map_name="de_dust2", point=[0, 0])
        avg_x = (
            NAV["de_dust2"][152]["northWestX"] + NAV["de_dust2"][152]["southEastX"]
        ) / 2
        avg_y = (
            NAV["de_dust2"][152]["northWestY"] + NAV["de_dust2"][152]["southEastY"]
        ) / 2
        avg_z = (
            NAV["de_dust2"][152]["northWestZ"] + NAV["de_dust2"][152]["southEastZ"]
        ) / 2
        area_found = find_closest_area(map_name="de_dust2", point=[avg_x, avg_y, avg_z])
        assert type(area_found) == dict
        assert area_found["areaId"] == 152

    def test_area_distance(self):
        """Tests area distance"""
        with pytest.raises(ValueError):
            area_distance(map_name="test", area_a=152, area_b=152, dist_type="graph")
        with pytest.raises(ValueError):
            area_distance(map_name="de_dust2", area_a=0, area_b=0, dist_type="graph")
        with pytest.raises(ValueError):
            area_distance(map_name="de_dust2", area_a=152, area_b=152, dist_type="test")
        graph_dist = area_distance(
            map_name="de_dust2", area_a=152, area_b=152, dist_type="graph"
        )
        geo_dist = area_distance(
            map_name="de_dust2", area_a=152, area_b=152, dist_type="geodesic"
        )
        assert type(graph_dist) == dict
        assert graph_dist["distanceType"] == "graph"
        assert graph_dist["distance"] == 0
        assert type(geo_dist) == dict
        assert geo_dist["distanceType"] == "geodesic"
        assert geo_dist["distance"] == 0

    def test_point_distance(self):
        """Tests point distance"""
        with pytest.raises(ValueError):
            point_distance(
                map_name="test", point_a=[0, 0, 0], point_b=[0, 0, 0], dist_type="graph"
            )
        with pytest.raises(ValueError):
            point_distance(
                map_name="de_dust2", point_a=[0, 0], point_b=[0, 0], dist_type="graph"
            )
        with pytest.raises(ValueError):
            point_distance(
                map_name="test",
                point_a=[0, 0, 0],
                point_b=[0, 0, 0],
                dist_type="geodesic",
            )
        with pytest.raises(ValueError):
            point_distance(
                map_name="de_dust2",
                point_a=[0, 0],
                point_b=[0, 0],
                dist_type="geodesic",
            )
        assert (
            point_distance(
                map_name="de_dust2",
                point_a=[0, 0],
                point_b=[1, 1],
                dist_type="euclidean",
            )["distance"]
            == 1.4142135623730951
        )
        assert (
            point_distance(
                map_name="de_dust2",
                point_a=[0, 0],
                point_b=[1, 1],
                dist_type="manhattan",
            )["distance"]
            == 2
        )
        assert (
            point_distance(
                map_name="de_dust2",
                point_a=[0, 0],
                point_b=[1, 1],
                dist_type="canberra",
            )["distance"]
            == 2.0
        )
        assert (
            point_distance(
                map_name="de_dust2", point_a=[-1, 5], point_b=[2, 1], dist_type="cosine"
            )["distance"]
            == 0.7368825942078912
        )
        avg_x = (
            NAV["de_dust2"][152]["northWestX"] + NAV["de_dust2"][152]["southEastX"]
        ) / 2
        avg_y = (
            NAV["de_dust2"][152]["northWestY"] + NAV["de_dust2"][152]["southEastY"]
        ) / 2
        avg_z = (
            NAV["de_dust2"][152]["northWestZ"] + NAV["de_dust2"][152]["southEastZ"]
        ) / 2
        assert (
            point_distance(
                map_name="de_dust2",
                point_a=[avg_x, avg_y, avg_z],
                point_b=[avg_x, avg_y, avg_z],
                dist_type="graph",
            )["distance"]
            == 0
        )
        assert (
            point_distance(
                map_name="de_dust2",
                point_a=[avg_x, avg_y, avg_z],
                point_b=[avg_x, avg_y, avg_z],
                dist_type="geodesic",
            )["distance"]
            == 0
        )

    def test_position_token(self):
        """Tests that position token returns correct values"""
        map_name = "de_nuke"
        frame = {
            "ct": {
                "players": [
                    {"x": -814.4315185546875, "y": -950.5277099609375, "z": -413.96875}
                ]
            },
            "t": {
                "players": [
                    {"x": -814.4315185546875, "y": -950.5277099609375, "z": -413.96875}
                ]
            },
        }
        token = generate_position_token(map_name, frame)
        assert type(token) == dict
        assert "tToken" in token.keys()
        assert "ctToken" in token.keys()
        assert "token" in token.keys()
        assert token["tToken"] == "000000000000000000100000000000"
        assert token["ctToken"] == "000000000000000000100000000000"
        assert (
            token["token"]
            == "000000000000000000100000000000000000000000000000100000000000"
        )
        with pytest.raises(ValueError):
            generate_position_token("de_does_not_exist", frame)
        with pytest.raises(ValueError):
            frame["ct"]["players"] == []
            generate_position_token("de_nuke", frame)
