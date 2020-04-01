import pytest

from csgo.analytics.distance import bombsite_distance, point_distance, polygon_area

class TestCSGOAnalytics:
    """ Class to test CSGO analytics
    """

    def test_bombsite_distance(self):
        """ Test bombsite distance function.
        """
        assert bombsite_distance([0,0,0]) == 35
        assert bombsite_distance([0,0,0], bombsite="B") == 38
        assert bombsite_distance([0,0,0], bombsite="A", map="de_inferno") == 30

    def test_point_distance(self):
        """ Test point distance function
        """
        assert point_distance([0,0],[1,1], type="euclidean") == 1.4142135623730951
        assert point_distance([0,0],[1,1], type="manhattan") == 2
        assert point_distance([0,0],[1,1], type="canberra") == 2.0
        assert point_distance([-1,5],[2,1], type="cosine") == 0.7368825942078912

    def test_polygon_area(self):
        """ Test polygon area function
        """
        assert polygon_area([0,1,2], [0,1,0]) == 2.0