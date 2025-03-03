"""Test the awpy.nav module."""

import json

import pytest

import awpy.data
import awpy.nav


@pytest.fixture
def parsed_nav():
    """Fixture that returns a parsed Nav object."""
    return awpy.nav.Nav.from_path(path="tests/de_dust2.nav")


class TestNav:
    """Tests the Nav object."""

    def test_invalid_filepath(self):
        """Test the Nav object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            awpy.nav.Nav.from_path("xyz.nav")

    def test_nav_areas(self, parsed_nav: awpy.nav.Nav):
        """Test the Demo object with an HLTV demo."""
        assert len(parsed_nav.areas) == 2248

    def test_nav_json(self):
        """Test the Nav object from a JSON file."""
        nav_as_json_path = awpy.data.NAVS_DIR / "de_dust2.json"

        with open(nav_as_json_path) as nav:
            nav_as_json = json.load(nav)
            assert len(nav_as_json["areas"]) == 2248
