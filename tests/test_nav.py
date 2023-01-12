import pytest
import numpy as np

from awpy.data import NAV
from awpy.analytics.nav import (
    area_distance,
    find_closest_area,
    generate_position_token,
    point_distance,
    point_in_area,
    generate_centroids,
    stepped_hull,
    position_state_distance,
    token_state_distance,
    frame_distance,
    token_distance,
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
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                        "isAlive": False,
                    }
                ]
            },
            "t": {
                "players": [
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                        "isAlive": True,
                    }
                ]
            },
        }
        token = generate_position_token(map_name, frame)
        assert type(token) == dict
        assert "tToken" in token.keys()
        assert "ctToken" in token.keys()
        assert "token" in token.keys()
        assert token["tToken"] == "000000000000000000100000000000"
        assert token["ctToken"] == "000000000000000000000000000000"
        assert (
            token["token"]
            == "000000000000000000000000000000000000000000000000100000000000"
        )
        with pytest.raises(ValueError):
            generate_position_token("de_does_not_exist", frame)

    def test_generate_centroids(self):
        """Tests generate centroids"""
        with pytest.raises(ValueError):
            generate_centroids(map_name="test")
        centroids, reps = generate_centroids("de_inferno")
        assert type(centroids) == dict
        assert "Quad" in centroids
        assert centroids == {
            "CTSpawn": 2831,
            "": 80,
            "BombsiteA": 3129,
            "TRamp": 190,
            "TSpawn": 3030,
            "LowerMid": 55,
            "TopofMid": 32,
            "Quad": 124,
            "Upstairs": 1306,
            "BombsiteB": 520,
            "Banana": 791,
            "Ruins": 225,
            "Middle": 8,
            "BackAlley": 269,
            "Apartments": 1606,
            "Graveyard": 3126,
            "SecondMid": 1478,
            "Balcony": 2367,
            "Pit": 305,
            "Arch": 82,
            "Bridge": 57,
            "Underpass": 2944,
            "Library": 911,
            "Deck": 74,
            "Kitchen": 257,
        }
        assert type(reps) == dict
        assert "" in reps
        assert reps == {
            "CTSpawn": 2832,
            "": 749,
            "BombsiteA": 3128,
            "TRamp": 190,
            "TSpawn": 3030,
            "LowerMid": 314,
            "TopofMid": 32,
            "Quad": 124,
            "Upstairs": 1306,
            "BombsiteB": 1968,
            "Banana": 109,
            "Ruins": 377,
            "Middle": 338,
            "BackAlley": 363,
            "Apartments": 2367,
            "Graveyard": 3126,
            "SecondMid": 730,
            "Balcony": 3050,
            "Pit": 2518,
            "Arch": 59,
            "Bridge": 57,
            "Underpass": 2946,
            "Library": 911,
            "Deck": 255,
            "Kitchen": 441,
        }

    def test_stepped_hull(self):
        """Tests stepped hull"""
        hull = stepped_hull(
            [
                (0, 0),
                (1, 0),
                (0, 1),
                (1, 1),
                (0.5, 0.5),
                (0.2, 0.2),
            ]
        )
        assert type(hull) == list
        assert hull == [(0, 1), (0, 0), (1, 0), (1, 1), (0, 1)]
        assert stepped_hull([(1, 1)]) == [(1, 1)]
        assert stepped_hull([]) == []

    def test_position_state_distance(self):
        """Tests position state distance"""
        pos_state1 = np.array([[[-500, -850, 100]]])
        pos_state2 = np.array([[[-550, -100, 130]], [[1, 1, 1]]])
        with pytest.raises(ValueError):
            position_state_distance(
                "de_ancient", pos_state1, pos_state2, distance_type="euclidean"
            )

        pos_state1 = np.array([[[-500, -850, 100, 6]]])
        pos_state2 = np.array([[[-550, -100, 130, 6]]])
        with pytest.raises(ValueError):
            position_state_distance(
                "de_ancient", pos_state1, pos_state2, distance_type="euclidean"
            )

        pos_state1 = np.array([[[-500, -850, 100]]])
        pos_state2 = np.array([[[-550, -100, 130]]])
        with pytest.raises(ValueError):
            position_state_distance(
                "de_map_does_not_exist",
                pos_state1,
                pos_state2,
                distance_type="euclidean",
            )
        with pytest.raises(ValueError):
            position_state_distance(
                "de_ancient",
                pos_state1,
                pos_state2,
                distance_type="distance_type_does_not_exist",
            )
        dist = position_state_distance(
            "de_ancient", pos_state1, pos_state2, distance_type="euclidean"
        )
        assert type(dist) == float
        assert round(dist, 2) == 752.26

        pos_state1 = np.array([[[-500, -850, 100], [-555, -105, 135]]])
        pos_state2 = np.array([[[-550, -100, 130], [-500, -850, 100]]])
        dist = position_state_distance(
            "de_ancient", pos_state1, pos_state2, distance_type="euclidean"
        )
        assert round(dist, 2) == 4.33

        pos_state1 = np.array([[[-500, -850, 100], [-445, -105, 135]]])
        pos_state2 = np.array([[[-550, -100, 130], [-500, -850, 100]]])
        dist = position_state_distance(
            "de_ancient", pos_state1, pos_state2, distance_type="graph"
        )
        assert type(dist) == float
        assert dist == 1

    def test_token_state_distance(self):
        """Tests token state distance"""
        token_array1 = np.array(
            [
                0.0,
                2.0,
                0.0,
                2.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
        token_array2 = np.array(
            [
                0.0,
                2.0,
                0.0,
                1.0,
                0.0,
                0.0,
                2.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                5.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
        with pytest.raises(ValueError):
            token_state_distance(
                "de_map_does_not_exist",
                token_array1,
                token_array2,
                distance_type="euclidean",
            )
        with pytest.raises(ValueError):
            token_state_distance(
                "de_ancient", token_array1, token_array2, distance_type="euclidean"
            )
        token_array1 = np.array(
            [
                0.0,
                2.0,
                0.0,
                2.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
        token_array2 = np.array(
            [
                0.0,
                2.0,
                0.0,
                1.0,
                0.0,
                0.0,
                2.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
        with pytest.raises(ValueError):
            token_state_distance(
                "de_ancient", token_array1, token_array2, distance_type="euclidean"
            )
        token_array1 = np.array(
            [
                0.0,
                2.0,
                0.0,
                2.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                2.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                1.0,
                1.0,
            ]
        )
        token_array2 = np.array(
            [
                0.0,
                2.0,
                0.0,
                1.0,
                0.0,
                0.0,
                2.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                5.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
        with pytest.raises(ValueError):
            token_state_distance(
                "de_ancient",
                token_array1,
                token_array2,
                distance_type="distance_tpye_does_not_exist",
            )
        with pytest.raises(ValueError):
            token_state_distance(
                "de_ancient",
                token_array1,
                token_array2,
                distance_type="graph",
                reference_point="reference_point_does_not_exist",
            )
        dist = token_state_distance(
            "de_ancient", token_array1, token_array2, distance_type="graph"
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 7.10
        dist = token_state_distance(
            "de_ancient", token_array1, token_array2, distance_type="euclidean"
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 643.12
        dist = token_state_distance(
            "de_ancient", token_array1, token_array2, distance_type="geodesic"
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 903.71

        token_array1 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=int,
        )
        token_array2 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=int,
        )
        dist = token_state_distance(
            "de_dust2", token_array1, token_array2, distance_type="edit_distance"
        )
        assert dist == 2
        dist = token_state_distance(
            "de_dust2",
            token_array1,
            token_array2,
            distance_type="graph",
            reference_point="representative_point",
        )
        assert isinstance(dist, float)
        assert dist == 6
        dist = token_state_distance(
            "de_dust2",
            token_array1,
            token_array2,
            distance_type="euclidean",
            reference_point="representative_point",
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 336.60
        dist = token_state_distance(
            "de_dust2",
            token_array1,
            token_array2,
            distance_type="geodesic",
            reference_point="representative_point",
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 782.12

        token_array1 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=int,
        )
        token_array2 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=int,
        )
        dist = token_state_distance(
            "de_nuke", token_array1, token_array2, distance_type="edit_distance"
        )
        assert dist == 2
        dist = token_state_distance(
            "de_nuke", token_array1, token_array2, distance_type="graph"
        )
        assert isinstance(dist, float)
        assert dist == 27
        dist = token_state_distance(
            "de_nuke", token_array1, token_array2, distance_type="euclidean"
        )
        assert isinstance(dist, float)
        assert round(dist, 2) == 2272.12
        dist = token_state_distance("de_nuke", token_array1, token_array2)
        assert isinstance(dist, float)
        assert round(dist, 2) == 4252.04

    def test_frame_distance(self):
        """Tests frame distance"""
        map_name = "de_nuke"
        frame1 = {
            "ct": {
                "players": [
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                    }
                ]
            },
            "t": {"players": []},
            "isKillFrame": False,
        }
        frame2 = {
            "ct": {
                "players": [
                    {
                        "x": -614.4315185546875,
                        "y": -550.5277099609375,
                        "z": -213.96875,
                    }
                ]
            },
            "t": {"players": []},
            "isKillFrame": True,
        }
        array1 = np.array([[[-814.4315185546875, -950.5277099609375, -413.96875]]])
        array2 = np.array([[[-614.4315185546875, -550.5277099609375, -213.96875]]])
        assert frame_distance(map_name, frame1, frame2) == position_state_distance(
            map_name, array1, array2
        )
        frame1 = {
            "t": {
                "players": [
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                    }
                ]
            },
            "ct": {"players": []},
            "isKillFrame": False,
        }
        frame2 = {
            "t": {
                "players": [
                    {
                        "x": -614.4315185546875,
                        "y": -550.5277099609375,
                        "z": -213.96875,
                    }
                ]
            },
            "ct": {"players": []},
            "isKillFrame": True,
        }
        array1 = np.array([[[-814.4315185546875, -950.5277099609375, -413.96875]]])
        array2 = np.array([[[-614.4315185546875, -550.5277099609375, -213.96875]]])
        assert frame_distance(map_name, frame1, frame2) == position_state_distance(
            map_name, array1, array2
        )
        frame1 = {
            "ct": {
                "players": [
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                    }
                ]
            },
            "t": {
                "players": [
                    {
                        "x": -814.4315185546875,
                        "y": -950.5277099609375,
                        "z": -413.96875,
                    }
                ]
            },
            "isKillFrame": False,
        }
        frame2 = {
            "ct": {
                "players": [
                    {
                        "x": -614.4315185546875,
                        "y": -550.5277099609375,
                        "z": -213.96875,
                    }
                ]
            },
            "t": {
                "players": [
                    {
                        "x": -614.4315185546875,
                        "y": -550.5277099609375,
                        "z": -213.96875,
                    }
                ]
            },
            "isKillFrame": True,
        }
        array1 = np.array(
            [
                [[-814.4315185546875, -950.5277099609375, -413.96875]],
                [[-814.4315185546875, -950.5277099609375, -413.96875]],
            ]
        )
        array2 = np.array(
            [
                [[-614.4315185546875, -550.5277099609375, -213.96875]],
                [[-614.4315185546875, -550.5277099609375, -213.96875]],
            ]
        )
        assert frame_distance(map_name, frame1, frame2) == position_state_distance(
            map_name, array1, array2
        )

    def test_token_distance(self):
        """Tests token distance"""
        map_name = "de_nuke"
        token1 = "000000000000000000100000000000"
        token2 = "000000000000000000000000000001"
        array1 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            dtype=int,
        )
        array2 = np.array(
            [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            ],
            dtype=int,
        )
        assert token_distance(map_name, token1, token2) == token_state_distance(
            map_name, array1, array2
        )
