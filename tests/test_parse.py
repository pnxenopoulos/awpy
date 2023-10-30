"""Tests demo parsing functionality."""


from awpy.parser import parse_demo


class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_demo_csgo_heroic_g2_katowice_2023(self):
        """Tests the output of Heroic vs G2 at Katowice 2023 (CSGO)."""
        parsed = parse_demo("tests/g2-vs-ence-m2-vertigo.dem")

        # Header
        assert parsed["header"]["map_name"] == "de_vertigo"
        assert parsed["header"]["demo_version_name"] == "valve_demo_2"
        assert parsed["header"]["client_name"] == "SourceTV Demo"

        # Rounds (not correct, need to calculate dmg)
        round_df = parsed["rounds"]
        assert round_df.shape[0] == 21
        assert round_df.round_end_reason.to_numpy()[0] == "t_win"
        assert round_df.round_end_reason.to_numpy()[1] == "t_win"
        assert round_df.round_end_reason.to_numpy()[2] == "ct_win"
        assert round_df.round_end_reason.to_numpy()[3] == "bomb_defused"
        assert round_df.round_end_reason.to_numpy()[4] == "ct_win"
        assert round_df.round_end_reason.to_numpy()[5] == "bomb_defused"
        assert round_df.round_end_reason.to_numpy()[6] == "t_win"
        assert round_df.round_end_reason.to_numpy()[7] == "target_bombed"
        assert round_df.round_end_reason.to_numpy()[8] == "t_win"
        assert round_df.round_end_reason.to_numpy()[9] == "t_win"
        assert round_df.round_end_reason.to_numpy()[10] == "t_win"
        assert round_df.round_end_reason.to_numpy()[11] == "ct_win"
        assert round_df.round_end_reason.to_numpy()[12] == "bomb_defused"
        assert round_df.round_end_reason.to_numpy()[13] == "target_bombed"
        assert round_df.round_end_reason.to_numpy()[14] == "t_win"
        assert round_df.round_end_reason.to_numpy()[15] == "target_bombed"
        assert round_df.round_end_reason.to_numpy()[16] == "target_bombed"
        assert round_df.round_end_reason.to_numpy()[17] == "t_win"
        assert round_df.round_end_reason.to_numpy()[18] == "target_bombed"
        assert round_df.round_end_reason.to_numpy()[19] == "t_win"
        assert round_df.round_end_reason.to_numpy()[20] == "t_win"

        # Kills
        kill_df = (
            parsed["kills"].groupby("attacker").size().reset_index(name="kill_count")
        )
        assert kill_df[kill_df["attacker"] == "huNter-"].kill_count.to_numpy()[0] == 9
        assert kill_df[kill_df["attacker"] == "HooXi"].kill_count.to_numpy()[0] == 13
        assert kill_df[kill_df["attacker"] == "m0NESY"].kill_count.to_numpy()[0] == 16
        assert kill_df[kill_df["attacker"] == "jks"].kill_count.to_numpy()[0] == 17
        assert kill_df[kill_df["attacker"] == "NiKo"].kill_count.to_numpy()[0] == 25
        assert kill_df[kill_df["attacker"] == "Snappi"].kill_count.to_numpy()[0] == 17
        assert kill_df[kill_df["attacker"] == "NertZ"].kill_count.to_numpy()[0] == 16
        assert kill_df[kill_df["attacker"] == "dycha"].kill_count.to_numpy()[0] == 15
        assert kill_df[kill_df["attacker"] == "SunPayus"].kill_count.to_numpy()[0] == 12
        assert kill_df[kill_df["attacker"] == "maden"].kill_count.to_numpy()[0] == 11
