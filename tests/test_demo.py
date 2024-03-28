"""Test the Demo object."""

import pytest

from awpy.demo import Demo


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_args(self):
        """Test the Demo object with invalid arguments."""
        with pytest.raises(TypeError):
            Demo("tests/spirit-vs-mouz-m1-vertigo.dem")

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Demo(file="xyz.dem")

    def test_hltv_demo(self):
        """Test the Demo object with an HLTV demo."""
        parsed_demo = Demo(file="tests/spirit-vs-mouz-m1-vertigo.dem")
        assert parsed_demo.file == "tests/spirit-vs-mouz-m1-vertigo.dem"
        assert parsed_demo.header.map_name == "de_vertigo"
