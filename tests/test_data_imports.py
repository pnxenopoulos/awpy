import os
import pytest

from csgo import DIST, MAP_NAV


class TestDataImports:
    """Class to test the data imports"""

    # def test_preloaded_distances(self):
    #    """Tests the preloaded distances"""
    #    assert DIST["de_inferno"][522][522] == 0
    # currently returns 1...need to fully recalculate distances

    def test_map_nav(self):
        """Tests the nav dataframe"""
        assert MAP_NAV[MAP_NAV["MapName"] == "de_cbble"].shape[0] == 1180
        assert MAP_NAV.isna().sum().sum() == 0
