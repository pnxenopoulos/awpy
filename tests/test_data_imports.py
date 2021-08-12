import os
import pytest

from csgo import DIST, MAP_NAV


class TestDataImports:
    """Class to test the data imports"""

    def test_preloaded_distances(self):
        """Tests the preloaded distances"""
        assert DIST["de_cbble"][4453][4453] == 0

    def test_map_nav(self):
        """Tests the nav information"""
        assert MAP_NAV[MAP_NAV['MapName'] == 'de_cbble'].shape[0] == 1180
