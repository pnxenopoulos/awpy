"""Test the cli functions."""

import json
import os
import pathlib
import zipfile
from collections.abc import Mapping
from enum import Enum, auto

import pytest
from click.testing import CliRunner

import awpy.cli

PROPERTY_EVENTS_MAPPING: Mapping[str, list[str]] = {
    "kills": ["player_death"],
    "damages": ["player_hurt"],
    "footsteps": ["player_sound"],
    "shots": ["weapon_fire"],
    "smokes": ["smokegrenade_detonate", "smokegrenade_expired"],
    "infernos": ["inferno_startburn", "inferno_expire"],
    "bomb": ["bomb_dropped", "bomb_pickup", "bomb_planted", "bomb_exploded", "bomb_defused"],
}


class EventsPassingMode(Enum):
    """Enum for events passing mode."""

    COMMA_LIST = auto()
    SEPARATE_ARGS = auto()


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

    @pytest.mark.parametrize("events_passing", [EventsPassingMode.COMMA_LIST, EventsPassingMode.SEPARATE_ARGS])
    @pytest.mark.parametrize(
        "properties",
        [
            ["kills"],
            ["kills", "damages"],
            ["kills", "damages", "smokes"],
        ],
    )
    def test_parse_demo_events_passing(self, properties: list[str], events_passing: EventsPassingMode):
        """Test that the parse command correctly accepts events overrides."""
        events = list({item for key in properties for item in PROPERTY_EVENTS_MAPPING.get(key, [])})
        match events_passing:
            case EventsPassingMode.COMMA_LIST:
                events_args = ["--events", ",".join(events)]
            case EventsPassingMode.SEPARATE_ARGS:
                events_args = [elem for event in events for elem in ("--events", event)]
        result = self.runner.invoke(
            awpy.cli.parse_demo,
            ["tests/vitality-vs-spirit-m2-nuke.dem", *events_args],
        )
        assert result.exit_code == 0

        zip_name = "vitality-vs-spirit-m2-nuke.zip"
        assert os.path.exists(zip_name)

        with zipfile.ZipFile(zip_name, "r") as zipf:
            # Check if all expected files are in the zip
            expected_files = [f"{prop}.parquet" for prop in properties] + [
                "header.json",
                "ticks.parquet",
                "grenades.parquet",
                "rounds.parquet",
            ]
            zipped_files = [pathlib.Path(file).name for file in zipf.namelist()]
            assert {pathlib.Path(file).name for file in expected_files} == set(zipped_files)
            # Check if there is an events/ folder and it contains files
            events_files = [file for file in zipf.namelist() if file.endswith(".parquet")]
            assert len(events_files) > 0

            # Check content of one file as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_nuke"
