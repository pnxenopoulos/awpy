import pytest

from csgo.analytics.coords import coords_to_area


class TestCSGOCoords:
    """Class to test CSGO coordinate functions"""

    def test_coords_to_area_invalid_map(self):
        """
        Test coords to area function with an invalid map.
        """
        with pytest.raises(ValueError):
            coords_to_area(x=0, y=0, z=0, map="dust2")

    def test_coords_to_area(self):
        """
        Tests that coords to area returns correctly.
        """
        coord = coords_to_area(x=0, y=0, z=64, map="de_dust2")
        assert coord["AreaID"] == 7760
        assert coord["AreaName"] == "OutsideLong"
