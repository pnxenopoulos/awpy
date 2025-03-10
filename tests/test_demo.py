"""Test the Demo object."""

import json
import os
import pathlib
import zipfile

import polars as pl
import pytest

import awpy.demo


class TestDemo:
    """Tests the Demo object."""

    def test_invalid_filepath(self):
        """Test the Demo object with an invalid filepath."""
        with pytest.raises(FileNotFoundError):
            awpy.demo.Demo("xyz.dem")

    def test_hltv_demo(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the Demo object with an HLTV demo."""
        assert parsed_hltv_demo.header["map_name"] == "de_nuke"

    def test_faceit_demo(self, parsed_faceit_demo: awpy.demo.Demo):
        """Test the Demo object with a FACEIT demo."""
        assert parsed_faceit_demo.header["map_name"] == "de_mirage"

    def test_mm_demo(self, parsed_mm_demo: awpy.demo.Demo):
        """Test the Demo object with an MM demo."""
        assert parsed_mm_demo.header["map_name"] == "de_ancient"

    def test_compress(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test that the demo is zipped."""
        parsed_hltv_demo.compress()

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

            # Check content of header as an example
            with zipf.open("header.json") as f:
                header = json.load(f)
                assert header["map_name"] == "de_nuke"

    def test_hltv_ticks_end_official_end(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the ticks DataFrame for an HLTV demo (end to official end)."""
        for end, official_end in zip(
            # Do not parse the last element, which is the last round
            parsed_hltv_demo.rounds["end"].to_list()[:-1],
            parsed_hltv_demo.rounds["official_end"].to_list()[:-1],
            strict=False,
        ):
            assert not parsed_hltv_demo.ticks.filter(
                pl.col("tick") >= end,
                pl.col("tick") <= official_end,
            ).is_empty()

    def test_hltv_ticks_start_freeze(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the ticks DataFrame for an HLTV demo (start to freeze end)."""
        for start, freeze_end in zip(
            parsed_hltv_demo.rounds["start"].to_list(),
            parsed_hltv_demo.rounds["freeze_end"].to_list(),
            strict=False,
        ):
            assert not parsed_hltv_demo.ticks.filter(pl.col("tick") >= start, pl.col("tick") < freeze_end).is_empty()

    def test_hltv_ticks_freeze_end(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the ticks DataFrame for an HLTV demo (freeze end to end)."""
        for freeze_end, end in zip(
            parsed_hltv_demo.rounds["freeze_end"].to_list(),
            parsed_hltv_demo.rounds["end"].to_list(),
            strict=False,
        ):
            assert not parsed_hltv_demo.ticks.filter(pl.col("tick") >= freeze_end, pl.col("tick") < end).is_empty()

    def test_hltv_rounds(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the rounds DataFrame for an HLTV demo."""
        assert parsed_hltv_demo.rounds["reason"].to_list() == [
            "ct_killed",
            "ct_killed",
            "ct_killed",
            "t_killed",
            "ct_killed",
            "bomb_exploded",
            "t_killed",
            "time_ran_out",
            "bomb_exploded",
            "ct_killed",
            "ct_killed",
            "t_killed",
            "t_killed",
            "t_killed",
            "bomb_exploded",
            "t_killed",
            "t_killed",
            "t_killed",
        ]

    def test_hltv_kills(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the kills DataFrame for an HLTV demo."""
        # Total kills
        assert len(parsed_hltv_demo.kills) == 111

    def test_hltv_damages(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the damages DataFrame for an HLTV demo."""
        assert not parsed_hltv_demo.damages.is_empty()

    def test_faceit_rounds(self, parsed_faceit_demo: awpy.demo.Demo):
        """Test the rounds DataFrame for a FACEIT demo."""
        assert len(parsed_faceit_demo.rounds) == 24

    def test_faceit_kills(self, parsed_faceit_demo: awpy.demo.Demo):
        """Test the kills DataFrame for a FACEIT demo."""
        assert len(parsed_faceit_demo.kills.filter(pl.col("attacker_side") != pl.col("victim_side"))) == 165

    def test_mm_rounds(self, parsed_mm_demo: awpy.demo.Demo):
        """Test the rounds DataFrame for an MM demo."""
        assert parsed_mm_demo.rounds["reason"].to_list() == [
            "ct_killed",
            "t_killed",
            "t_killed",
            "t_killed",
            "t_killed",
            "t_killed",
            "ct_killed",
            "t_surrender",
        ]

    def test_mm_kills(self, parsed_mm_demo: awpy.demo.Demo):
        """Test the kills DataFrame for an MM demo."""
        assert len(parsed_mm_demo.kills.filter(pl.col("attacker_side") != pl.col("victim_side"))) == 42
