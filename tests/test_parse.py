"""Tests demo parsing functionality."""

import pytest

from awpy.parser import parse_demo
from awpy.parser.models import Demo


@pytest.fixture(scope="class")
def hltv_demo():
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return parse_demo("tests/natus-vincere-vs-virtus-pro-m1-overpass.dem")


@pytest.fixture(scope="class")
def faceit_demo():
    """Test case for FACEIT demos.

    https://www.faceit.com/en/cs2/room/1-89e005ee-da0b-487a-9d5b-65fde0069d7a
    """
    return parse_demo("tests/1-89e005ee-da0b-487a-9d5b-65fde0069d7a-1-2.dem")


class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_path_not_found(self):
        """Tests that we get a FileNotFoundError when an incorrect path is specified."""
        with pytest.raises(
            FileNotFoundError, match="file-does-not-exist.dem not found."
        ):
            parse_demo("file-does-not-exist.dem")

    def test_invalid_trade_time(self):
        """Tests that we get a ValueError when an invalid trade time is specified."""
        with pytest.raises(
            ValueError, match="Trade time must be a positive integer. Received: -1"
        ):
            parse_demo(
                "tests/natus-vincere-vs-virtus-pro-m1-overpass.dem", trade_time=-1
            )

    def test_hltv_demo_header(self, hltv_demo: Demo):
        """Tests the header of NaVi vs VP at PGL Copenhagen 2024 (CS2).

        Args:
            hltv_demo (Demo): The parsed NaVi vs VP demo.
        """
        assert (
            hltv_demo.header.demo_version_guid == "8e9d71ab-04a1-4c01-bb61-acfede27c046"
        )
        assert hltv_demo.header.demo_version_name == "valve_demo_2"
        assert hltv_demo.header.map_name == "de_overpass"

    def test_hltv_demo_rounds(self, hltv_demo: Demo):
        """Tests the rounds of NaVi vs VP at PGL Copenhagen 2024 (CS2).

        Args:
            hltv_demo (Demo): The parsed NaVi vs VP demo.
        """
        assert hltv_demo.rounds.shape[0] == 35

        round_end_reasons = hltv_demo.rounds.round_end_reason.to_numpy()

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

    def test_hltv_demo_kills(self, hltv_demo: Demo):
        """Tests the kills of NaVi vs VP at PGL Copenhagen 2024 (CS2).

        Args:
            hltv_demo (Demo): The parsed NaVi vs VP demo.
        """
        kills_no_team_dmg = hltv_demo.kills[
            hltv_demo.kills["attacker_side"] != hltv_demo.kills["victim_side"]
        ]
        kill_df = (
            kills_no_team_dmg.groupby("attacker").size().reset_index(name="kill_count")
        )

        # Kills
        assert kill_df.loc[kill_df["attacker"] == "iM", "kill_count"].iloc[0] == 28
        assert (
            kill_df.loc[kill_df["attacker"] == "w0nderful", "kill_count"].iloc[0] == 28
        )
        assert (
            kill_df.loc[kill_df["attacker"] == "AleksibOb", "kill_count"].iloc[0] == 22
        )
        assert kill_df.loc[kill_df["attacker"] == "jL.", "kill_count"].iloc[0] == 22
        assert kill_df.loc[kill_df["attacker"] == "b1t", "kill_count"].iloc[0] == 19
        assert kill_df.loc[kill_df["attacker"] == "Hop6epT", "kill_count"].iloc[0] == 25
        assert kill_df.loc[kill_df["attacker"] == "fame", "kill_count"].iloc[0] == 19
        assert (
            kill_df.loc[kill_df["attacker"] == "JAMEZWER", "kill_count"].iloc[0] == 20
        )
        assert kill_df.loc[kill_df["attacker"] == "FL1TJO", "kill_count"].iloc[0] == 19
        assert kill_df.loc[kill_df["attacker"] == "mir1", "kill_count"].iloc[0] == 19

        # Deaths
        death_df = (
            hltv_demo.kills.groupby("victim").size().reset_index(name="death_count")
        )
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
        assert death_df.loc[death_df["victim"] == "fame", "death_count"].iloc[0] == 23
        assert (
            death_df.loc[death_df["victim"] == "JAMEZWER", "death_count"].iloc[0] == 22
        )
        assert death_df.loc[death_df["victim"] == "FL1TJO", "death_count"].iloc[0] == 25
        assert death_df.loc[death_df["victim"] == "mir1", "death_count"].iloc[0] == 28

        # Assists
        assist_df = (
            kills_no_team_dmg.groupby("assister")
            .size()
            .reset_index(name="assist_count")
        )
        assert assist_df.loc[assist_df["assister"] == "iM", "assist_count"].iloc[0] == 3
        assert (
            assist_df.loc[assist_df["assister"] == "w0nderful", "assist_count"].iloc[0]
            == 5
        )
        assert (
            assist_df.loc[assist_df["assister"] == "AleksibOb", "assist_count"].iloc[0]
            == 14
        )
        assert (
            assist_df.loc[assist_df["assister"] == "jL.", "assist_count"].iloc[0] == 6
        )
        assert (
            assist_df.loc[assist_df["assister"] == "b1t", "assist_count"].iloc[0] == 12
        )
        assert (
            assist_df.loc[assist_df["assister"] == "Hop6epT", "assist_count"].iloc[0]
            == 7
        )
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
        )
        assert (
            assist_df.loc[assist_df["assister"] == "mir1", "assist_count"].iloc[0] == 8
        )

    def test_faceit_header(self, faceit_demo: Demo):
        """Tests the header of a FACEIT demo.

        Args:
            faceit_demo (Demo): The parsed FACEIT demo.
        """
        assert (
            faceit_demo.header.demo_version_guid
            == "8e9d71ab-04a1-4c01-bb61-acfede27c046"
        )
        assert faceit_demo.header.demo_version_name == "valve_demo_2"
        assert faceit_demo.header.map_name == "de_anubis"
        assert faceit_demo.header.server_name == "FACEIT.com register to play here"

    def test_faceit_rounds(self, faceit_demo: Demo):
        """Tests the rounds of a FACEIT demo.

        Args:
            faceit_demo (Demo): The parsed FACEIT demo.
        """
        assert faceit_demo.rounds.shape[0] == 20

    def test_faceit_kills(self, faceit_demo: Demo):
        """Tests the kills of a FACEIT demo.

        Args:
            faceit_demo (Demo): The parsed FACEIT demo.
        """
        kills_no_team_dmg = faceit_demo.kills[
            faceit_demo.kills["attacker_side"] != faceit_demo.kills["victim_side"]
        ]
        kill_df = (
            kills_no_team_dmg.groupby("attacker").size().reset_index(name="kill_count")
        )

        # Kills
        assert (
            kill_df.loc[kill_df["attacker"] == "RAALZh3h3", "kill_count"].iloc[0] == 21
        )
        assert kill_df.loc[kill_df["attacker"] == "-910", "kill_count"].iloc[0] == 20
        assert (
            kill_df.loc[kill_df["attacker"] == "Mzinho-H", "kill_count"].iloc[0] == 13
        )
        assert kill_df.loc[kill_df["attacker"] == "Senzu-", "kill_count"].iloc[0] == 12
        assert (
            kill_df.loc[kill_df["attacker"] == "innocent", "kill_count"].iloc[0] == 10
        )  # Says he got 11
        assert (
            kill_df.loc[kill_df["attacker"] == "somedieyoung", "kill_count"].iloc[0]
            == 16
        )
        assert kill_df.loc[kill_df["attacker"] == "--br0", "kill_count"].iloc[0] == 15
        assert kill_df.loc[kill_df["attacker"] == "degst3r", "kill_count"].iloc[0] == 14
        assert kill_df.loc[kill_df["attacker"] == "DemQQ-", "kill_count"].iloc[0] == 11
        assert kill_df.loc[kill_df["attacker"] == "kRaSnaL", "kill_count"].iloc[0] == 7

        # Deaths
        death_df = (
            faceit_demo.kills.groupby("victim").size().reset_index(name="death_count")
        )
        assert (
            death_df.loc[death_df["victim"] == "RAALZh3h3", "kill_count"].iloc[0] == 11
        )
        assert death_df.loc[death_df["victim"] == "-910", "kill_count"].iloc[0] == 12
        assert (
            death_df.loc[death_df["victim"] == "Mzinho-H", "kill_count"].iloc[0] == 13
        )
        assert death_df.loc[death_df["victim"] == "Senzu-", "kill_count"].iloc[0] == 13
        assert (
            death_df.loc[death_df["victim"] == "innocent", "kill_count"].iloc[0] == 14
        )
        assert (
            death_df.loc[death_df["victim"] == "somedieyoung", "kill_count"].iloc[0]
            == 14
        )
        assert (
            death_df.loc[death_df["victim"] == "--br0", "kill_count"].iloc[0] == 14
        )  # Says he got 15
        assert death_df.loc[death_df["victim"] == "degst3r", "kill_count"].iloc[0] == 16
        assert death_df.loc[death_df["victim"] == "DemQQ-", "kill_count"].iloc[0] == 15
        assert death_df.loc[death_df["victim"] == "kRaSnaL", "kill_count"].iloc[0] == 17

        # Assists
        assist_df = (
            kills_no_team_dmg.groupby("assister")
            .size()
            .reset_index(name="assist_count")
        )
        assert (
            assist_df.loc[assist_df["assister"] == "RAALZh3h3", "kill_count"].iloc[0]
            == 1
        )
        assert assist_df.loc[assist_df["assister"] == "-910", "kill_count"].iloc[0] == 8
        assert (
            assist_df.loc[assist_df["assister"] == "Mzinho-H", "kill_count"].iloc[0]
            == 8
        )
        assert (
            assist_df.loc[assist_df["assister"] == "Senzu-", "kill_count"].iloc[0] == 4
        )  # Says he got 5
        assert (
            assist_df.loc[assist_df["assister"] == "innocent", "kill_count"].iloc[0]
            == 6
        )
        assert (
            assist_df.loc[assist_df["assister"] == "somedieyoung", "kill_count"].iloc[0]
            == 4
        )
        assert (
            assist_df.loc[assist_df["assister"] == "--br0", "kill_count"].iloc[0] == 6
        )
        # Degster had 0 assists
        assert (
            assist_df.loc[assist_df["assister"] == "DemQQ-", "kill_count"].iloc[0] == 3
        )
        assert (
            assist_df.loc[assist_df["assister"] == "kRaSnaL", "kill_count"].iloc[0] == 1
        )
