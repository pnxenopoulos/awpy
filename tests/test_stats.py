"""Tests demo stats functionality."""

import pytest

from awpy.parser import parse_demo
from awpy.analytics import adr


class TestStats:
    """Class to test stats functionality."""

    def setup_class(self):
        """Sets up the class by parsing the demo."""
        self.parsed_demo = parse_demo("tests/g2-vs-ence-m2-vertigo.dem")

    def test_adr(self):
        """Tests average-damage-per-round (ADR) calculation."""
        adr_df = adr(self.parsed_demo)
        adr_NiKo = adr_df[
            (adr_df["steamid"] == 76561198041683378) & (adr_df["side"] == "total")
        ]["adr"].iloc[0]
        adr_Snappi = adr_df[
            (adr_df["steamid"] == 76561197989423065) & (adr_df["side"] == "total")
        ]["adr"].iloc[0]

        assert round(adr_NiKo, 1) == 125.5
        assert round(adr_Snappi, 1) == 109.7
