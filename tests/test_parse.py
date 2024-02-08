"""Tests demo parsing functionality."""

import pytest

from awpy.parser import parse_demo
from awpy.parser.models import Demo


@pytest.fixture(scope="class")
def hltv_demo():
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return parse_demo(file="tests/natus-vincere-vs-virtus-pro-m1-overpass.dem")


@pytest.fixture(scope="class")
def faceit_demo():
    """Test case for FACEIT demos.

    https://www.faceit.com/en/cs2/room/1-89e005ee-da0b-487a-9d5b-65fde0069d7a
    """
    return parse_demo(file="tests/1-89e005ee-da0b-487a-9d5b-65fde0069d7a-1-2.dem")


class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_path_not_found(self):
        """Tests that we get a FileNotFoundError when an incorrect path is specified."""
        with pytest.raises(
            FileNotFoundError, match="file-does-not-exist.dem not found."
        ):
            parse_demo(file="file-does-not-exist.dem")

    def test_hltv_demo_header(self, hltv_demo: Demo):
        """Tests the header of NaVi vs VP at PGL Copenhagen 2024 (CS2).

        Args:
            hltv_demo (Demo): The parsed NaVi vs VP demo.
        """
        assert (
            hltv_demo.header.demo_version_guid == "8e9d71ab-04a1-4c01-bb61-acfede27c046"
        )
        assert hltv_demo.header.demo_version_name == "valve_demo_2"
        assert hltv_demo.header.map_name == "de_overpass"

    def test_faceit_header(self, faceit_demo: Demo):
        """Tests the header of a FACEIT demo.

        Args:
            faceit_demo (Demo): The parsed FACEIT demo.
        """
        assert (
            faceit_demo.header.demo_version_guid
            == "8e9d71ab-04a1-4c01-bb61-acfede27c046"
        )
        assert faceit_demo.header.demo_version_name == "valve_demo_2"
        assert faceit_demo.header.map_name == "de_anubis"
        assert faceit_demo.header.server_name == "FACEIT.com register to play here"
