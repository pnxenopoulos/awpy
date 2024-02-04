"""Tests demo stats functionality."""

from awpy.parser import parse_demo
from awpy.stats import adr, kast


class TestStats:
    """Class to test stats functionality."""

    def setup_class(self):
        """Sets up the class by parsing the demo."""
        self.parsed_demo = parse_demo("tests/g2-vs-ence-m2-vertigo.dem")

    def test_adr(self):
        """Tests average-damage-per-round (ADR) calculation."""
        adr_df = adr(self.parsed_demo)
        adr_niko = adr_df[
            (adr_df["steamid"] == 76561198041683378) & (adr_df["side"] == "total")
        ]["adr"].iloc[0]
        adr_snappi = adr_df[
            (adr_df["steamid"] == 76561197989423065) & (adr_df["side"] == "total")
        ]["adr"].iloc[0]

        assert round(adr_niko, 1) == 125.5
        assert round(adr_snappi, 1) == 109.7

    def test_kast(self):
        """Tests kill-assist-survive-traded (KAST) calculation."""
        kast_df = kast(self.parsed_demo)
        kast_niko = kast_df[
            (kast_df["steamid"] == 76561198041683378) & (kast_df["side"] == "total")
        ]["kast"].iloc[0]

        assert round(kast_niko, 2) == 0.95
