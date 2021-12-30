import pytest
import numpy as np

from csgo import NAV
from csgo.analytics.nav import point_distance, point_in_area, PlaceEncoder

class TestNav:
    """Class to test the nav-related functions."""

    def test_point_in_area(self):
        """Tests point in area
        """
        with pytest.raises(ValueError):
            point_in_area(map_name="test", area_id=0, point=[0,0,0])
        with pytest.raises(ValueError):
            point_in_area(map_name="de_dust2", area_id=0, point=[0,0,0])
        with pytest.raises(ValueError):
            point_in_area(map_name="test", area_id=0, point=[0])
        avg_x = (NAV["de_dust2"][7233]["NorthWestX"] + NAV["de_dust2"][7233]["SouthEastX"])/2
        avg_y = (NAV["de_dust2"][7233]["NorthWestY"] + NAV["de_dust2"][7233]["SouthEastY"])/2
        avg_z = (NAV["de_dust2"][7233]["NorthWestZ"] + NAV["de_dust2"][7233]["SouthEastZ"])/2
        assert point_in_area(map_name="de_dust2", area_id=7233, point=[avg_x,avg_y,avg_z])

    def test_find_area(self):
        """ Tests find_area
        """
        assert True

    def test_area_distance(self):
        """ Tests area distance
        """
        assert True

    def test_point_distance(self):
        """ Tests point distance
        """
        with pytest.raises(ValueError):
            point_distance(map_name="test", point_a=[0,0,0], point_b=[0,0,0], dist_type="graph")
        with pytest.raises(ValueError):
            point_distance(map_name="de_dust2", point_a=[0,0], point_b=[0,0], dist_type="graph")
        with pytest.raises(ValueError):
            point_distance(map_name="test", point_a=[0,0,0], point_b=[0,0,0], dist_type="geodesic")
        with pytest.raises(ValueError):
            point_distance(map_name="de_dust2", point_a=[0,0], point_b=[0,0], dist_type="geodesic")
        assert point_distance(point_a=[0, 0], point_b=[1, 1], dist_type="euclidean") == 1.4142135623730951
        assert point_distance(point_a=[0, 0], point_b=[1, 1], dist_type="manhattan") == 2
        assert point_distance(point_a=[0, 0], point_b=[1, 1], dist_type="canberra") == 2.0
        assert point_distance(point_a=[-1, 5], point_b=[2, 1], dist_type="cosine") == 0.7368825942078912
        avg_x = (NAV["de_dust2"][7233]["NorthWestX"] + NAV["de_dust2"][7233]["SouthEastX"])/2
        avg_y = (NAV["de_dust2"][7233]["NorthWestY"] + NAV["de_dust2"][7233]["SouthEastY"])/2
        avg_z = (NAV["de_dust2"][7233]["NorthWestZ"] + NAV["de_dust2"][7233]["SouthEastZ"])/2
        assert point_distance(point_a=[avg_x,avg_y,avg_z], point_b=[avg_x,avg_y,avg_z], dist_type="graph") == 0
        assert point_distance(point_a=[avg_x,avg_y,avg_z], point_b=[avg_x,avg_y,avg_z], dist_type="geodesic") == 0

    def test_place_encode(self):
        """Tests that place encoding works for correct values
        """
        e = PlaceEncoder()
        assert np.sum(e.encode("place", "TSpawn")) == 1
        assert np.sum(e.encode("place", "TSpawnnn")) == 0
        assert np.sum(e.encode("map", "de_dust2")) == 1
        assert np.sum(e.encode("map", "de_dust0")) == 0
