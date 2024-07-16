"""Test the cli functions."""

import json
import os
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from awpy.cli import parse


class TestCommandLine:
    """Tests the Awpy command line interface."""

    @pytest.fixture(autouse=True)
    def setup_runner(self, setup):  # noqa: ANN001, ARG002, PT004
        """Setup CLI runner. `setup` arg is the pytest setup fixture."""
        self.runner = CliRunner()

    def test_parse_invalid_filepath(self):
        """Test the parse command with an invalid filepath."""
        result = self.runner.invoke(parse, ["xyz.dem"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)

    def test_parse_zip_creation(self):
        """Test that the parse command produces a zip file."""
        result = self.runner.invoke(parse, ["tests/spirit-vs-mouz-m1-vertigo.dem"])
        assert result.exit_code == 0

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

            # Check content of one file as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_vertigo"
