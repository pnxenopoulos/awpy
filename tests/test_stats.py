"""Test the stats module."""

import polars as pl
import pytest

import awpy.demo
import awpy.stats


@pytest.fixture
def adr_results(parsed_hltv_demo: awpy.demo.Demo) -> pl.DataFrame:
    """Fixture that returns ADR results filtered for the 'all' side."""
    adr_df = awpy.stats.adr(parsed_hltv_demo, team_dmg=True)
    return adr_df.filter(pl.col("side") == "all")


@pytest.fixture
def kast_results(parsed_hltv_demo: awpy.demo.Demo) -> pl.DataFrame:
    """Fixture that returns ADR results filtered for the 'all' side."""
    kast_df = awpy.stats.kast(parsed_hltv_demo)
    return kast_df.filter(pl.col("side") == "all")


class TestStats:
    """Tests the stats module."""

    @pytest.mark.parametrize(
        ("name", "expected_adr"),
        [
            ("ZywOo", 127.0),
            ("ropz", 93.3),
            ("apEX", 84.4),
            ("flameZ", 70.8),
            ("mezii", 37.8),
            ("donk", 93.9),
            ("zont1x", 56.1),
            ("magixx", 59.1),
            ("sh1ro", 34.0),
            ("chopper", 26.3),
        ],
    )
    def test_adr(self, adr_results: pl.DataFrame, name: str, expected_adr: float):
        """Test the ADR function. Compares to HLTV."""
        player_df = adr_results.filter(pl.col("name") == name)

        # Verify that exactly one record exists for the player
        assert len(player_df) == 1, f"Expected one record for {name}, got {len(player_df)}"

        # Extract and round the ADR value
        actual_adr = player_df.select("adr").item()
        assert round(actual_adr, 1) == expected_adr, (
            f"ADR for {name} is {round(actual_adr, 1)}, expected {expected_adr}"
        )

    @pytest.mark.parametrize(
        ("name", "expected_kast"),
        [
            ("ZywOo", 88.9),
            ("ropz", 83.3),
            ("apEX", 66.7),
            ("flameZ", 72.2),
            ("mezii", 83.3),
            ("donk", 66.7),
            ("zont1x", 50.0),
            ("magixx", 44.4),
            ("sh1ro", 50.0),
            ("chopper", 33.3),
        ],
    )
    def test_kast(self, kast_results: pl.DataFrame, name: str, expected_kast: float):
        """Test the KAST function. Compares to HLTV."""
        player_df = kast_results.filter(pl.col("name") == name)

        # Verify that exactly one record exists for the player
        assert len(player_df) == 1, f"Expected one record for {name}, got {len(player_df)}"

        # Extract and round the KAST value
        actual_kast = player_df.select("kast").item()
        assert round(actual_kast, 1) == expected_kast, (
            f"KAST for {name} is {round(actual_kast, 1)}, expected {expected_kast}"
        )

    def test_rating(self, parsed_hltv_demo: awpy.demo.Demo):
        """Test the rating function. Checks that ordering is correct."""
        rating_df = awpy.stats.rating(parsed_hltv_demo).filter(pl.col("side") == "all").sort("rating")
        assert len(rating_df) == 10, f"Expected 10 players, got {len(rating_df)}"

        assert rating_df["name"].to_list() == [
            "chopper",
            "sh1ro",
            "magixx",
            "zont1x",
            "mezii",
            "flameZ",
            "donk",
            "apEX",
            "ropz",
            "ZywOo",
        ]
