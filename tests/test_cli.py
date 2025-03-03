"""Test the cli functions."""

import json
import os
import pathlib
import zipfile

import pytest
from click.testing import CliRunner

import awpy.cli


class TestCommandLine:
    """Tests the Awpy command line interface."""

    @pytest.fixture(autouse=True)
    def setup_runner(self, setup):  # noqa: ANN001, ARG002
        """Setup CLI runner. `setup` arg is the pytest setup fixture."""
        self.runner = CliRunner()

    def test_parse_nav_invalid_filepath(self):
        """Test the nav command with an invalid filepath."""
        result = self.runner.invoke(awpy.cli.parse_nav, ["xyz.nav"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)

    def test_parse_nav(self):
        """Test that the nav command produces a json file."""
        result = self.runner.invoke(awpy.cli.parse_nav, ["tests/de_dust2.nav"])
        assert result.exit_code == 0

        json_name = "tests/de_dust2.json"
        assert os.path.exists(json_name)

    def test_parse_demo_invalid_filepath(self):
        """Test the parse command with an invalid filepath."""
        result = self.runner.invoke(awpy.cli.parse_demo, ["xyz.dem"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)

    def test_parse_demo_zip_creation(self):
        """Test that the parse command produces a zip file."""
        result = self.runner.invoke(awpy.cli.parse_demo, ["tests/vitality-vs-spirit-m2-nuke.dem"])
        assert result.exit_code == 0

        zip_name = "vitality-vs-spirit-m2-nuke.zip"
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
            zipped_files = [pathlib.Path(file).name for file in zipf.namelist()]
            assert all(pathlib.Path(file).name in zipped_files for file in expected_files)

            # Check if there is an events/ folder and it contains files
            events_files = [file for file in zipf.namelist() if file.endswith(".parquet")]
            assert len(events_files) > 0

            # Check content of one file as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_nuke"
