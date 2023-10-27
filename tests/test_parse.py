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
        parsed = parse_demo("tests/g2-vs-ence-m2-vertigo.dem")

        # Header
        parsed["header"]["map_name"] == "de_vertigo"
        parsed["header"]["demo_version_name"] == "valve_demo_2"
        parsed["header"]["client_name"] == "SourceTV Demo"

        # Rounds (not correct, need to calculate dmg)
        round_df = parsed["rounds"]
        round_df.shape[0] == 21
        round_df.round_end_reason.values[0] == "t_win"
        round_df.round_end_reason.values[1] == "t_win"
        round_df.round_end_reason.values[2] == "ct_win"
        round_df.round_end_reason.values[3] == "bomb_defused"
        round_df.round_end_reason.values[4] == "ct_win"
        round_df.round_end_reason.values[5] == "bomb_defused"
        round_df.round_end_reason.values[6] == "t_win"
        round_df.round_end_reason.values[7] == "target_bombed"
        round_df.round_end_reason.values[8] == "t_win"
        round_df.round_end_reason.values[9] == "t_win"
        round_df.round_end_reason.values[10] == "t_win"
        round_df.round_end_reason.values[11] == "ct_win"
        round_df.round_end_reason.values[12] == "bomb_defused"
        round_df.round_end_reason.values[13] == "target_bombed"
        round_df.round_end_reason.values[14] == "t_win"
        round_df.round_end_reason.values[15] == "target_bombed"
        round_df.round_end_reason.values[16] == "target_bombed"
        round_df.round_end_reason.values[17] == "t_win"
        round_df.round_end_reason.values[18] == "target_bombed"
        round_df.round_end_reason.values[19] == "t_win"
        round_df.round_end_reason.values[20] == "t_win"

        # Damages
        damage_df = parsed["damages"]
        damage_df["dmg"] = damage_df["dmg_health"].apply(lambda x: min(x, 100))
        damage_df = (
            parsed["damages"].groupby("attacker").dmg.sum().reset_index(name="adr")
        )
        damage_df["adr"] = damage_df["adr"] / 21

        # Kills
        kill_df = (
            parsed["kills"].groupby("attacker").size().reset_index(name="kill_count")
        )
        kill_df[kill_df["attacker"] == "huNter-"].kill_count.values[0] == 9
        kill_df[kill_df["attacker"] == "HooXi"].kill_count.values[0] == 13
        kill_df[kill_df["attacker"] == "m0NESY"].kill_count.values[0] == 16
        kill_df[kill_df["attacker"] == "jks"].kill_count.values[0] == 17
        kill_df[kill_df["attacker"] == "NiKo"].kill_count.values[0] == 25
        kill_df[kill_df["attacker"] == "Snappi"].kill_count.values[0] == 17
        kill_df[kill_df["attacker"] == "NertZ"].kill_count.values[0] == 16
        kill_df[kill_df["attacker"] == "dycha"].kill_count.values[0] == 15
        kill_df[kill_df["attacker"] == "SunPayus"].kill_count.values[0] == 12
        kill_df[kill_df["attacker"] == "maden"].kill_count.values[0] == 11
