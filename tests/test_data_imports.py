import os
import pytest
import networkx

from csgo import MAP_NAV, MAP_DATA, NAV, NAV_GRAPHS


class TestDataImports:
    """Class to test the data imports"""

    def test_map_nav(self):
        """Tests the nav dataframe"""
        assert MAP_NAV[MAP_NAV["MapName"] == "de_cbble"].shape[0] == 1180
        assert MAP_NAV.isna().sum().sum() == 0

    def test_nav(self):
        assert type(NAV) == dict

    def test_nav_graphs(self):
        assert type(NAV_GRAPHS) == networkx.classes.graph.Graph

    def test_map_data(self):
        """Tests the nav data"""
        assert MAP_DATA["de_overpass"]["scale"] == 5.2
