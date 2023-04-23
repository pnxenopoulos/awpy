"""Tests utils module."""
import tempfile
from unittest.mock import MagicMock, patch

from awpy.utils import AutoVivification, check_go_version, is_in_range


class TestUtils:
    """Class to test the csgo package util classes and functions."""

    @patch("awpy.utils.subprocess")
    def test_go_version(self, mock_subproc: MagicMock):
        """Tests if the Golang version >= 1.18.0."""
        inputs = [
            b"go version go1.18.4 windows/amd64",
            b"go version go1.17.4 windows/amd64",
            b"go version go1.7.4 windows/amd64",
            b"",
            b"a \n b",
            b"go version go2.1.4 windows/amd64",
        ]
        outputs = [True, False, False, False, False, True]
        for my_input, my_output in zip(inputs, outputs, strict=True):
            with tempfile.TemporaryFile() as fp:
                mock_subproc.Popen.return_value.__enter__.return_value.stdout = fp
                fp.write(my_input)
                fp.seek(0)
                assert check_go_version() is my_output

        mock_subproc.Popen.return_value = IOError
        assert check_go_version() is False

    def test_autoviv_keyerror(self):
        """Tests if the AutoVivification feature presents a KeyError on missing key."""
        a = AutoVivification()
        a["Ping"]["Pong"] = "Test"
        assert a["Ping"]["Pong"] == "Test"

    def test_is_in_range(self):
        """Tests if in range."""
        assert is_in_range(0, -1, 1)
        assert not is_in_range(-100, -1, 1)
