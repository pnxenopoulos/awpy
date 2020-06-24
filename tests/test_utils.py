import os
import pytest
import pandas as pd

from csgo.utils import AutoVivification, NpEncoder, check_go_version


class TestUtils:
    """ Class to test the csgo package util classes and functions
    """

    def test_go_version(self):
        """ Tests if the Golang version >= 1.14.0
        """
        go_works = check_go_version()
        assert go_works == True

    def test_autoviv_keyerror(self):
        """ Tests if the AutoVivification feature presents a KeyError on missing key
        """
        a = AutoVivification()
        a["Ping"]["Pong"] = "Test"
        assert a["Ping"]["Pong"] == "Test"
