"""Test the cli functions."""

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from awpy.cli import parse


# Mock Demo class, __init__ must match awpy.demo.Demo
class MockDemo:
    """Mock Demo class for testing."""

    def __init__(
        self, path: Path, *, verbose: bool, ticks: bool  # noqa: ARG002
    ) -> None:
        """Creates a mock Demo object."""
        self.kills = pd.DataFrame({"data": [1, 2, 3]})
        self.damages = pd.DataFrame({"data": [1, 2, 3]})
        self.bomb = pd.DataFrame({"data": [1, 2, 3]})
        self.smokes = pd.DataFrame({"data": [1, 2, 3]})
        self.infernos = pd.DataFrame({"data": [1, 2, 3]})
        self.weapon_fires = pd.DataFrame({"data": [1, 2, 3]})
        self.rounds = pd.DataFrame({"data": [1, 2, 3]})
        self.grenades = pd.DataFrame({"data": [1, 2, 3]})
        self.ticks = pd.DataFrame({"data": [1, 2, 3]})
        self.header = {"info": "mock"}


@pytest.fixture()
def mock_demo(monkeypatch: pytest.MonkeyPatch):  # noqa: PT004
    """Fixture for mocking the Demo class."""
    monkeypatch.setattr("awpy.cli.Demo", MockDemo)


class TestCommandLine:
    """Tests the Awpy command line interface."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_demo: None):  # noqa: ARG002, PT004
        """Setup CLI runner."""
        self.runner = CliRunner()

    def test_invalid_filepath(self):
        """Test the parse command with an invalid filepath."""
        result = self.runner.invoke(parse, ["xyz.dem"])
        assert result.exit_code != 0
        assert isinstance(result.exception, SystemExit)

    def test_zip_creation(self):
        """Test that the parse command produces a zip file."""
        with tempfile.NamedTemporaryFile(suffix=".dem") as tmpfile:
            result = self.runner.invoke(parse, [tmpfile.name])
            assert result.exit_code == 0

            zip_name = Path(tmpfile.name).stem + ".zip"
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

                # Check content of one file as an example
                with zipf.open("header.json") as f:
                    header = json.load(f)
                    assert header == {"info": "mock"}

    def test_zip_creation_notick(self):
        """Test that the parse command produces a zip file."""
        with tempfile.NamedTemporaryFile(suffix=".dem") as tmpfile:
            result = self.runner.invoke(parse, [tmpfile.name, "--noticks"])
            assert result.exit_code == 0

            zip_name = Path(tmpfile.name).stem + ".zip"
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
                    "header.json",
                ]
                zipped_files = [Path(file).name for file in zipf.namelist()]
                assert all(Path(file).name in zipped_files for file in expected_files)

                # Assert ticks.data is not in the zipf
                assert "ticks.data" not in zipped_files

                # Check content of one file as an example
                with zipf.open("header.json") as f:
                    header = json.load(f)
                    assert header == {"info": "mock"}
