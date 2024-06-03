"""Test the cli functions."""

from pathlib import Path

import pytest

from awpy.cli import parse


class TestCommandLine:
    """Tests the Awpy command line interface."""

    def test_invalid_filepath(self):
        """Test the parse command with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            parse("xyz.dem")

    def test_zip_creation(self):
        """Test that the parse command produces a zip file."""
        _ = parse("tests/spirit-vs-mouz-m1-vertigo.dem")
        assert (Path("tests/spirit-vs-mouz-m1-vertigo.zip")).exists()
