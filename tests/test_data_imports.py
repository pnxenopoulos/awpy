import os
import pytest
import networkx

from awpy.data import MAP_DATA, NAV, NAV_CSV, NAV_GRAPHS


class TestDataImports:
    """Class to test the data imports"""

    def test_nav_csv(self):
        """Tests the nav dataframe"""
        assert NAV_CSV[NAV_CSV["mapName"] == "de_cbble"].shape[0] == 1180

    def test_nav(self):
        assert type(NAV) == dict
        assert type(NAV["de_dust2"][152])
        assert NAV["de_dust2"][152]["areaName"] == "BombsiteA"

    def test_nav_graphs(self):
        assert type(NAV_GRAPHS) == dict
        assert type(NAV_GRAPHS["de_dust2"]) == networkx.DiGraph

    def test_map_data(self):
        """Tests the nav data"""
        assert MAP_DATA["de_overpass"]["scale"] == 5.2
