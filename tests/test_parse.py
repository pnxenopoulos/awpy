"""Tests demo parsing functionality."""

import pandas as pd
import pytest

from awpy.parser import parse_demo


class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_path_not_found(self):
        """Tests that we get a FileNotFoundError when an incorrect path is specified."""
        with pytest.raises(FileNotFoundError):
            parse_demo("file-does-not-exist.dem")

    def test_demo_cs2_navi_vp_pgl_copenhagen_2024(self):
        """Tests the output of NaVi vs VP at PGL Copenhagen 2024 (CS2)."""
        parsed = parse_demo("natus-vincere-vs-virtus-pro-m1-overpass.dem")

        # Header
        assert parsed.header.demo_version_guid == "8e9d71ab-04a1-4c01-bb61-acfede27c046"
        assert parsed.header.demo_version_name == "valve_demo_2"
        assert parsed.header.map_name == "de_overpass"

        # Rounds
        assert parsed.rounds.shape[0] == 35
        round_end_reasons = parsed.rounds.round_end_reason.to_numpy()

        # First Half
        assert round_end_reasons[0] == "t_win"
        assert round_end_reasons[1] == "t_win"
        assert round_end_reasons[2] == "t_win"
        assert round_end_reasons[3] == "t_win"
        assert round_end_reasons[4] == "t_win"
        assert round_end_reasons[5] == "t_win"
        assert round_end_reasons[6] == "target_saved"
        assert round_end_reasons[7] == "t_win"
        assert round_end_reasons[8] == "target_bombed"
        assert round_end_reasons[9] == "t_win"
        assert round_end_reasons[10] == "ct_win"
        assert round_end_reasons[11] == "ct_win"

        # Second Half
        assert round_end_reasons[12] == "t_win"
        assert round_end_reasons[13] == "target_bombed"
        assert round_end_reasons[14] == "t_win"
        assert round_end_reasons[15] == "t_win"
        assert round_end_reasons[16] == "target_bombed"
        assert round_end_reasons[17] == "ct_win"
        assert round_end_reasons[18] == "t_win"
        assert round_end_reasons[19] == "target_bombed"
        assert round_end_reasons[20] == "t_win"
        assert round_end_reasons[21] == "target_saved"
        assert round_end_reasons[22] == "target_saved"
        assert round_end_reasons[23] == "t_win"
        assert round_end_reasons[24] == "target_bombed"
        assert round_end_reasons[25] == "t_win"
        assert round_end_reasons[26] == "ct_win"

        # Overtime
        assert round_end_reasons[27] == "t_win"
        assert round_end_reasons[28] == "t_win"
        assert round_end_reasons[29] == "ct_win"
        assert round_end_reasons[30] == "target_bombed"
        assert round_end_reasons[31] == "bomb_defused"
        assert round_end_reasons[32] == "ct_win"
        assert round_end_reasons[33] == "t_win"
        assert round_end_reasons[34] == "t_win"

        # Kills
        kill_df = parsed.kills[
            parsed.kills["attacker_side"] != parsed.kills["victim_side"]
        ]
        kill_df = kill_df.groupby("attacker").size().reset_index(name="kill_count")
        assert kill_df.loc[kill_df["attacker"] == "iM", "kill_count"].iloc[0] == 28
        assert (
            kill_df.loc[kill_df["attacker"] == "w0nderful", "kill_count"].iloc[0] == 28
        )
        assert (
            kill_df.loc[kill_df["attacker"] == "AleksibOb", "kill_count"].iloc[0] == 22
        )
        assert kill_df.loc[kill_df["attacker"] == "jL.", "kill_count"].iloc[0] == 22
        assert (
            kill_df.loc[kill_df["attacker"] == "b1t", "kill_count"].iloc[0] == 19
        )  # Listed as 20 in HLTV
        assert kill_df.loc[kill_df["attacker"] == "Hop6epT", "kill_count"].iloc[0] == 25
        assert kill_df.loc[kill_df["attacker"] == "fame", "kill_count"].iloc[0] == 19
        assert (
            kill_df.loc[kill_df["attacker"] == "JAMEZWER", "kill_count"].iloc[0] == 20
        )
        assert kill_df.loc[kill_df["attacker"] == "FL1TJO", "kill_count"].iloc[0] == 19
        assert kill_df.loc[kill_df["attacker"] == "mir1", "kill_count"].iloc[0] == 19

        # Deaths
        death_df = parsed.kills.groupby("victim").size().reset_index(name="death_count")
        assert death_df.loc[death_df["victim"] == "iM", "death_count"].iloc[0] == 20
        assert (
            death_df.loc[death_df["victim"] == "w0nderful", "death_count"].iloc[0] == 15
        )
        assert (
            death_df.loc[death_df["victim"] == "AleksibOb", "death_count"].iloc[0] == 25
        )
        assert death_df.loc[death_df["victim"] == "jL.", "death_count"].iloc[0] == 23
        assert death_df.loc[death_df["victim"] == "b1t", "death_count"].iloc[0] == 22
        assert (
            death_df.loc[death_df["victim"] == "Hop6epT", "death_count"].iloc[0] == 24
        )
        assert (
            death_df.loc[death_df["victim"] == "fame", "death_count"].iloc[0] == 23
        )  # Listed as 24 in HLTV
        assert (
            death_df.loc[death_df["victim"] == "JAMEZWER", "death_count"].iloc[0] == 22
        )
        assert death_df.loc[death_df["victim"] == "FL1TJO", "death_count"].iloc[0] == 25
        assert death_df.loc[death_df["victim"] == "mir1", "death_count"].iloc[0] == 28

        # Assists
        kill_df = parsed.kills[
            parsed.kills["attacker_side"] != parsed.kills["victim_side"]
        ]
        assist_df = kill_df.groupby("assister").size().reset_index(name="assist_count")
        assert assist_df.loc[assist_df["assister"] == "iM", "assist_count"].iloc[0] == 3
        assert (
            assist_df.loc[assist_df["assister"] == "w0nderful", "assist_count"].iloc[0]
            == 5
        )  # Listed as 7 in HLTV
        assert (
            assist_df.loc[assist_df["assister"] == "AleksibOb", "assist_count"].iloc[0]
            == 14
        )
        assert (
            assist_df.loc[assist_df["assister"] == "jL.", "assist_count"].iloc[0] == 6
        )  # Listed as 7 in HLTV
        assert (
            assist_df.loc[assist_df["assister"] == "b1t", "assist_count"].iloc[0] == 12
        )  # Listed as 13 in HLTV
        assert (
            assist_df.loc[assist_df["assister"] == "Hop6epT", "assist_count"].iloc[0]
            == 7
        )  # Listed as 8 in HLTV
        assert (
            assist_df.loc[assist_df["assister"] == "fame", "assist_count"].iloc[0] == 1
        )
        assert (
            assist_df.loc[assist_df["assister"] == "JAMEZWER", "assist_count"].iloc[0]
            == 2
        )
        assert (
            assist_df.loc[assist_df["assister"] == "FL1TJO", "assist_count"].iloc[0]
            == 8
        )  # Listed as 9 in HLTV
        assert (
            assist_df.loc[assist_df["assister"] == "mir1", "assist_count"].iloc[0] == 8
        )  # Listed as 9 in HLTV

    def test_trade_kills(self):
        """Tests that we can identify trade kills."""
        kill_df = pd.DataFrame(
            {
                "tick": [128, 256, 1024],
                "attacker_steamid": [1, 6, 2],
                "victim_steamid": [7, 1, 6],
                "attacker_side": ["ct", "t", "ct"],
                "victim_side": ["t", "ct", "t"],
            }
        )
        kill_df["is_trade"] = kill_df.apply(
            lambda row: is_trade_kill(kill_df, row.name, 640), axis=1
        )
        kill_df["was_traded"] = kill_df.apply(
            lambda row: was_traded(kill_df, row.name, 640), axis=1
        )

        assert all(kill_df.is_trade.to_numpy() == [False, True, False])
        assert all(kill_df.is_trade.to_numpy() == [True, False, False])
