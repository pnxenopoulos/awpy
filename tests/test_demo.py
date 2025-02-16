"""Test the Demo object."""

import json
import os
import zipfile
from pathlib import Path

import pytest

from awpy.demo import Demo


@pytest.fixture
def parsed_hltv_demo():
    """Fixture that returns a parsed HLTV Demo object."""
    dem = Demo(path="tests/spirit-vs-mouz-m1-vertigo.dem")
    dem.parse()
    return dem


@pytest.fixture
def parsed_faceit_demo():
    """Fixture that returns a parsed Faceit Demo object."""
    dem = Demo(path="tests/faceit-fpl-1-a568cd9f-8817-4410-a3f3-2270f89135e2.dem")
    dem.parse()
    return dem


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            Demo("xyz.dem")

    def test_hltv_demo(self, parsed_hltv_demo: Demo):
        """Test the Demo object with an HLTV demo."""
        assert parsed_hltv_demo.header["map_name"] == "de_vertigo"

    def test_compress(self, parsed_hltv_demo: Demo):
        """Test that the demo is zipped."""
        parsed_hltv_demo.compress()

        zip_name = "spirit-vs-mouz-m1-vertigo.zip"
        assert os.path.exists(zip_name)

        with zipfile.ZipFile(zip_name, "r") as zipf:
            # Check if all expected files are in the zip
            expected_files = [
                "kills.parquet",
                "damages.parquet",
                "footsteps.parquet",
                "shots.parquet",
                "grenades.parquet",
                "smokes.parquet",
                "infernos.parquet",
                "bomb.parquet",
                "ticks.parquet",
                "rounds.parquet",
                "header.json",
            ]
            zipped_files = [Path(file).name for file in zipf.namelist()]
            assert all(Path(file).name in zipped_files for file in expected_files)

            # Check if there is an events/ folder and it contains files
            events_files = [file for file in zipf.namelist() if file.endswith(".parquet")]
            assert len(events_files) > 0

            # Check content of header as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_vertigo"

    def test_hltv_rounds(self, parsed_hltv_demo: Demo):
        """Test the rounds DataFrame for an HLTV demo."""
        assert not parsed_hltv_demo.rounds.is_empty()
        assert parsed_hltv_demo.rounds["reason"].to_list() == [
            "ct_killed",
            "ct_killed",
            "ct_killed",
            "t_killed",
            "bomb_defused",
            "ct_killed",
            "bomb_exploded",
            "t_killed",
            "bomb_defused",
            "t_killed",
            "ct_killed",
            "ct_killed",
            "ct_killed",
            "ct_killed",
            "t_killed",
            "ct_killed",
            "t_killed",
            "t_killed",
            "t_killed",
            "ct_killed",
            "t_killed",
            "bomb_exploded",
            "t_killed",
        ]

    def test_hltv_kills(self, parsed_hltv_demo: Demo):
        """Test the kills DataFrame for an HLTV demo."""
        assert not parsed_hltv_demo.kills.is_empty()

    def test_hltv_damages(self, parsed_hltv_demo: Demo):
        """Test the damages DataFrame for an HLTV demo."""
        assert not parsed_hltv_demo.damages.is_empty()

    def test_faceit_kills(self, parsed_faceit_demo: Demo):
        """Test the kills DataFrame for a Faceit demo."""
        assert not parsed_faceit_demo.kills.is_empty()
