import pytest

from csgo.analytics.distance import (
    bombsite_distance,
    point_distance,
    polygon_area,
    area_distance,
)
from csgo.utils import AutoVivification


class TestCSGOAnalytics:
    """ Class to test CSGO analytics
    """

    def test_bombsite_distance(self):
        """ Test bombsite distance function.
        """
        assert bombsite_distance([0, 0, 0]) == 35
        assert bombsite_distance([0, 0, 0], bombsite="B") == 38
        assert bombsite_distance([0, 0, 0], bombsite="A", map="de_inferno") == 30

    def test_point_distance(self):
        """ Test point distance function
        """
        assert point_distance([0, 0], [1, 1], type="euclidean") == 1.4142135623730951
        assert point_distance([0, 0], [1, 1], type="manhattan") == 2
        assert point_distance([0, 0], [1, 1], type="canberra") == 2.0
        assert point_distance([-1, 5], [2, 1], type="cosine") == 0.7368825942078912
        assert point_distance([0, 0, 0], [100, 100, 100]) == 4
        assert point_distance([0, 0, 0], [100, 100, 100], map="de_vertigo") == 1

    def test_polygon_area(self):
        """ Test polygon area function
        """
        assert polygon_area([0, 1, 2], [0, 1, 0]) == 1.0

    def test_bombsite_invalid_map(self):
        """
        Test bombsite function with an invalid map.
        """
        with pytest.raises(ValueError):
            bombsite_distance([0, 0, 0], map="dust2")

    def test_point_invalid_map(self):
        """
        Test point distance function with an invalid map.
        """
        with pytest.raises(ValueError):
            point_distance([0, 0, 0], [1, 1, 1], map="dust2")

    def test_area_invalid_map(self):
        """
        Test area distance function with an invalid map.
        """
        with pytest.raises(ValueError):
            area_distance(26, 42, map="dust2")

    def test_area_dist(self):
        """
        Tests that area distance returns correct value.
        """
        assert area_distance(26, 42, map="de_mirage") == 26
