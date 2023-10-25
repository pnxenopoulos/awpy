"""Tests demo parsing functionality."""
import logging
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from awpy.parser import parse_demo

class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_demo_csgo_heroic_g2_katowice_2023(self):
        """Tests the output of Heroic vs G2 at Katowice 2023 (CSGO)."""
        parsed = parse_demo("tests/heroic-g2-katowice-2023-mirage.dem")