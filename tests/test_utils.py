import os
import pytest
import pandas as pd

from csgo.utils import AutoVivification, check_go_version, is_in_range


class TestUtils:
    """Class to test the csgo package util classes and functions"""

    def test_go_version(self):
        """Tests if the Golang version >= 1.14.0"""
        go_works = check_go_version()
        assert go_works == True

    def test_autoviv_keyerror(self):
        """Tests if the AutoVivification feature presents a KeyError on missing key"""
        a = AutoVivification()
        a["Ping"]["Pong"] = "Test"
        assert a["Ping"]["Pong"] == "Test"

    def test_is_in_range(self):
        """Tests if in range"""
        assert is_in_range(0, -1, 1)
        assert not is_in_range(-100, -1, 1)
