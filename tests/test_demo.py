"""Test the Demo object."""

import pytest

from awpy.demo import Demo


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Demo("xyz.dem")
