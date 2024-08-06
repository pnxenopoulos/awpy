"""Test the Demo object."""

import json
import zipfile
from pathlib import Path

import pytest

from awpy.demo import Demo


@pytest.fixture()
def parsed_hltv_demo():
    """Fixture that returns a parsed Demo object."""
    return Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem")


@pytest.fixture()
def parsed_hltv_demo_no_rounds():
    """Fixture that returns a parsed Demo object with rounds disabled."""
    return Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem", rounds=False)


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Demo("xyz.dem")

    def test_hltv_demo(self, parsed_hltv_demo: Demo):
        """Test the Demo object with an HLTV demo."""
        assert parsed_hltv_demo.header["map_name"] == "de_vertigo"

    def test_no_rounds(self, parsed_hltv_demo_no_rounds: Demo):
        """Test that when you do not parse rounds, there are no top-level dataframes."""
        assert parsed_hltv_demo_no_rounds.rounds is None
        assert parsed_hltv_demo_no_rounds.kills is None
        assert parsed_hltv_demo_no_rounds.damages is None
        assert parsed_hltv_demo_no_rounds.bomb is None
        assert parsed_hltv_demo_no_rounds.smokes is None
        assert parsed_hltv_demo_no_rounds.infernos is None
        assert parsed_hltv_demo_no_rounds.weapon_fires is None
        assert parsed_hltv_demo_no_rounds.rounds is None
        assert parsed_hltv_demo_no_rounds.grenades is None

    def test_compress(self, parsed_hltv_demo: Demo):
        """Test that the demo is zipped."""
        parsed_hltv_demo.compress()

        zip_name = Path("spirit-vs-mouz-m1-vertigo.zip")
        assert zip_name.exists()

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

    def test_compress_no_rounds(self, parsed_hltv_demo_no_rounds: Demo):
        """Test that the demo is zipped and no top-level dataframes are generated."""
        parsed_hltv_demo_no_rounds.compress()

        zip_name = Path("spirit-vs-mouz-m1-vertigo.zip")
        assert zip_name.exists()

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
