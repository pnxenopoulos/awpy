"""Test the awpy.nav module."""

import pytest

from awpy.nav import Nav


@pytest.fixture
def parsed_nav():
    """Fixture that returns a parsed Nav object."""
    return Nav(path="tests/de_dust2.nav")


class TestNav:
    """Tests the Nav object."""

    def test_invalid_filepath(self):
        """Test the Nav object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Nav("xyz.nav")

    def test_hltv_demo(self, parsed_nav: Nav):
        """Test the Demo object with an HLTV demo."""
        assert len(parsed_nav.areas) == 2248
