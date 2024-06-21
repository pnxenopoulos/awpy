"""Test the Demo object."""

import json
import os
import zipfile
from pathlib import Path

import pytest

from awpy.demo import Demo


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Demo("xyz.dem")

    def test_hltv_demo(self):
        """Test the Demo object with an HLTV demo."""
        parsed_demo = Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem")
        assert parsed_demo.header["map_name"] == "de_vertigo"

    def test_no_rounds(self):
        """Test that when you do not parse rounds, there are no top-level dataframes."""
        parsed_demo = Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem", rounds=False)
        assert parsed_demo.rounds is None
        assert parsed_demo.kills is None
        assert parsed_demo.damages is None
        assert parsed_demo.bomb is None
        assert parsed_demo.smokes is None
        assert parsed_demo.infernos is None
        assert parsed_demo.weapon_fires is None
        assert parsed_demo.rounds is None
        assert parsed_demo.grenades is None

    def test_compress(self):
        """Test that the demo is zipped."""
        demo = Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem")
        demo.compress()

        zip_name = "spirit-vs-mouz-m1-vertigo.zip"
        assert os.path.exists(zip_name)

        with zipfile.ZipFile(zip_name, "r") as zipf:
            # Check if all expected files are in the zip
            expected_files = [
                "kills.data",
                "damages.data",
                "bomb.data",
                "smokes.data",
                "infernos.data",
                "weapon_fires.data",
                "rounds.data",
                "grenades.data",
                "ticks.data",
                "header.json",
            ]
            zipped_files = [Path(file).name for file in zipf.namelist()]
            assert all(Path(file).name in zipped_files for file in expected_files)

            # Check if there is an events/ folder and it contains files
            events_files = [
                file
                for file in zipf.namelist()
                if file.startswith("events/") and not file.endswith("/")
            ]
            assert len(events_files) > 0

            # Check content of header as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_vertigo"

    def test_compress_no_rounds(self):
        """Test that the demo is zipped and no top-level dataframes are generated."""
        demo = Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem", rounds=False)
        demo.compress()

        zip_name = "spirit-vs-mouz-m1-vertigo.zip"
        assert os.path.exists(zip_name)

        with zipfile.ZipFile(zip_name, "r") as zipf:
            # Check if all expected files are in the zip
            expected_files = [
                "header.json",
            ]
            zipped_files = [Path(file).name for file in zipf.namelist()]
            assert all(Path(file).name in zipped_files for file in expected_files)

            # Check if there is an events/ folder and it contains files
            events_files = [
                file
                for file in zipf.namelist()
                if file.startswith("events/") and not file.endswith("/")
            ]
            assert len(events_files) > 0

            # Check content of header as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_vertigo"
