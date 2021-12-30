import pytest
import numpy as np

from csgo import NAV
from csgo.analytics.nav import point_in_area, PlaceEncoder

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

    def test_place_encode(self):
        """Tests that place encoding works for correct values
        """
        e = PlaceEncoder()
        assert np.sum(e.encode("place", "TSpawn")) == 1
        assert np.sum(e.encode("place", "TSpawnnn")) == 0
        assert np.sum(e.encode("map", "de_dust2")) == 1
        assert np.sum(e.encode("map", "de_dust0")) == 0
