import pytest
import numpy as np

from csgo import NAV
from csgo.analytics.nav import area_distance, find_area, point_distance, point_in_area, PlaceEncoder

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
        avg_x = (NAV["de_dust2"][152]["NorthWestX"] + NAV["de_dust2"][152]["SouthEastX"])/2
        avg_y = (NAV["de_dust2"][152]["NorthWestY"] + NAV["de_dust2"][152]["SouthEastY"])/2
        avg_z = (NAV["de_dust2"][152]["NorthWestZ"] + NAV["de_dust2"][152]["SouthEastZ"])/2
        assert point_in_area(map_name="de_dust2", area_id=152, point=[avg_x,avg_y,avg_z])

    def test_find_area(self):
        """ Tests find_area
        """
        with pytest.raises(ValueError):
            find_area(map_name="test", point=[0, 0, 0])
        with pytest.raises(ValueError):
            find_area(map_name="de_dust2", point=[0, 0])
        avg_x = (NAV["de_dust2"][152]["NorthWestX"] + NAV["de_dust2"][152]["SouthEastX"])/2
        avg_y = (NAV["de_dust2"][152]["NorthWestY"] + NAV["de_dust2"][152]["SouthEastY"])/2
        avg_z = (NAV["de_dust2"][152]["NorthWestZ"] + NAV["de_dust2"][152]["SouthEastZ"])/2
        area_found = find_area(map_name="de_dust2", point=[avg_x, avg_y, avg_z])
        assert type(area_found) == dict
        assert area_found["AreaId"] == 152

    def test_area_distance(self):
        """ Tests area distance
        """
        with pytest.raises(ValueError):
            area_distance(map_name="test", area_a=152, area_b=152, dist_type="graph")
        with pytest.raises(ValueError):
            area_distance(map_name="de_dust2", area_a=0, area_b=0, dist_type="graph")
        with pytest.raises(ValueError):
            area_distance(map_name="de_dust2", area_a=152, area_b=152, dist_type="test")
        assert area_distance(map_name="de_dust2", area_a=152, area_b=152, dist_type="graph") == 0
        assert area_distance(map_name="de_dust2", area_a=152, area_b=152, dist_type="geodesic") == 0

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
        assert point_distance(map_name="de_dust2", point_a=[0, 0], point_b=[1, 1], dist_type="euclidean") == 1.4142135623730951
        assert point_distance(map_name="de_dust2", point_a=[0, 0], point_b=[1, 1], dist_type="manhattan") == 2
        assert point_distance(map_name="de_dust2", point_a=[0, 0], point_b=[1, 1], dist_type="canberra") == 2.0
        assert point_distance(map_name="de_dust2", point_a=[-1, 5], point_b=[2, 1], dist_type="cosine") == 0.7368825942078912
        avg_x = (NAV["de_dust2"][152]["NorthWestX"] + NAV["de_dust2"][152]["SouthEastX"])/2
        avg_y = (NAV["de_dust2"][152]["NorthWestY"] + NAV["de_dust2"][152]["SouthEastY"])/2
        avg_z = (NAV["de_dust2"][152]["NorthWestZ"] + NAV["de_dust2"][152]["SouthEastZ"])/2
        assert point_distance(map_name="de_dust2", point_a=[avg_x,avg_y,avg_z], point_b=[avg_x,avg_y,avg_z], dist_type="graph") == 0
        assert point_distance(map_name="de_dust2", point_a=[avg_x,avg_y,avg_z], point_b=[avg_x,avg_y,avg_z], dist_type="geodesic") == 0

    def test_place_encode(self):
        """Tests that place encoding works for correct values
        """
        e = PlaceEncoder()
        assert np.sum(e.encode("place", "TSpawn")) == 1
        assert np.sum(e.encode("place", "TSpawnnn")) == 0
        assert np.sum(e.encode("map", "de_dust2")) == 1
        assert np.sum(e.encode("map", "de_dust0")) == 0