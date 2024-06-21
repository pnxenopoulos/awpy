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
    def setup(self):  # noqa: PT004
        """Setup CLI runner."""
        self.runner = CliRunner()

    def test_parse_invalid_filepath(self):
        """Test the parse command with an invalid filepath."""
        result = self.runner.invoke(parse, ["xyz.dem"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)

    def test_parse_zip_creation(self):
        """Test that the parse command produces a zip file."""
        demofile = Path("tests/spirit-vs-mouz-m1-vertigo.dem")
        if not demofile.exists():
            pytest.fail(f"Test file {demofile} does not exist.")
        
        result = self.runner.invoke(parse, [str(demofile)])
        assert result.exit_code == 0

        zip_name = Path(Path(demofile.name).stem + ".zip")
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
