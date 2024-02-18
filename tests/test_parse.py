"""Tests demo parsing functionality."""

import pandas as pd
import pytest
from pydantic import ValidationError

from awpy.parser import parse_demo
from awpy.parser.models import Demo, DemoHeader
from awpy.parser.round import apply_round_id_to_df, parse_rounds


@pytest.fixture(scope="class")
def hltv_demo():
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return parse_demo(
        file="tests/natus-vincere-vs-virtus-pro-m1-overpass.dem", rounds=False
    )


@pytest.fixture(scope="class")
def hltv_demo_round_end_reasons():
    """Test case for NaVi vs VP at PGL Copenhagen 2024 (CS2) from HLTV.

    https://www.hltv.org/stats/matches/mapstatsid/169189/natus-vincere-vs-virtuspro
    """
    return [
        "t_win",
        "t_win",
        "t_win",
        "t_win",
        "t_win",
        "t_win",
        "target_saved",
        "t_win",
        "target_bombed",
        "t_win",
        "ct_win",
        "ct_win",
        "t_win",
        "target_bombed",
        "t_win",
        "t_win",
        "target_bombed",
        "ct_win",
        "t_win",
        "target_bombed",
        "t_win",
        "target_saved",
        "target_saved",
        "t_win",
        "target_bombed",
        "t_win",
        "ct_win",
        "t_win",
        "t_win",
        "ct_win",
        "target_bombed",
        "bomb_defused",
        "ct_win",
        "t_win",
        "t_win",
    ]


@pytest.fixture(scope="class")
def faceit_demo():
    """Test case for FACEIT demos.

    https://www.faceit.com/en/cs2/room/1-89e005ee-da0b-487a-9d5b-65fde0069d7a
    """
    return parse_demo(file="tests/1-89e005ee-da0b-487a-9d5b-65fde0069d7a-1-2.dem")


@pytest.fixture(scope="class")
def header():
    """Test case for the demo header."""
    return DemoHeader(
        demo_version_guid="8e9d71ab-04a1-4c01-bb61-acfede27c046",
        network_protocol="13985",
        fullpackets_version="2",
        allow_clientside_particles=True,
        addons="",
        client_name="SourceTV Demo",
        map_name="de_overpass",
        server_name="challengermode.com - Register to join",
        demo_version_name="valve_demo_2",
        allow_clientside_entities=True,
        demo_file_stamp="PBDEMS2\x00",
        game_directory="/home/dathost/cs2_linux/game/csgo",
    )


class TestParser:
    """Class to test the demo parser.

    We use the demofiles in `test_data.json`
    """

    def test_path_not_found(self):
        """Tests that we get a FileNotFoundError when an incorrect path is specified."""
        with pytest.raises(
            FileNotFoundError, match="file-does-not-exist.dem not found."
        ):
            parse_demo(file="file-does-not-exist.dem")

    def test_missing_round_events(self, header: DemoHeader):
        """Test that we raise appropriate errors if we are missing round events."""
        with pytest.raises(ValidationError):
            Demo(header=header, events={}, ticks=None, grenades=None)

    def test_missing_round_start(self, header: DemoHeader):
        """Test that we raise an error if we are missing round start events."""
        with pytest.raises(ValidationError):
            Demo(
                header=header,
                events={
                    "round_freeze_end": [],
                    "round_end": [],
                    "round_officially_ended": [],
                    "bomb_planted": [],
                },
                ticks=None,
                grenades=None,
            )

    def test_missing_round_freeze(self, header: DemoHeader):
        """Test that we raise an error if we are missing round freeze events."""
        with pytest.raises(ValidationError):
            Demo(
                header=header,
                events={
                    "round_start": [],
                    "round_end": [],
                    "round_officially_ended": [],
                    "bomb_planted": [],
                },
                ticks=None,
                grenades=None,
            )

    def test_missing_round_end(self, header: DemoHeader):
        """Test that we raise an error if we are missing round end events."""
        with pytest.raises(ValidationError):
            Demo(
                header=header,
                events={
                    "round_start": [],
                    "round_freeze_end": [],
                    "round_officially_ended": [],
                    "bomb_planted": [],
                },
                ticks=None,
                grenades=None,
            )

    def test_missing_round_officially_ended(self, header: DemoHeader):
        """Test that we raise an error if we are missing round official end events."""
        with pytest.raises(ValidationError):
            Demo(
                header=header,
                events={
                    "round_start": [],
                    "round_freeze_end": [],
                    "round_end": [],
                    "bomb_planted": [],
                },
                ticks=None,
                grenades=None,
            )

    def test_missing_bomb_planted(self, header: DemoHeader):
        """Test that we raise an error if we are missing bomb planted events."""
        with pytest.raises(ValidationError):
            Demo(
                header=header,
                events={
                    "round_start": [],
                    "round_freeze_end": [],
                    "round_end": [],
                    "round_officially_ended": [],
                },
                ticks=None,
                grenades=None,
            )

    def test_event_type(self, header: DemoHeader):
        """Test that we add the event type to the DataFrame."""
        demo = Demo(
            header=header,
            events={
                "round_start": pd.DataFrame([{"tick": 1}]),
                "round_freeze_end": pd.DataFrame([{"tick": 1}]),
                "round_end": pd.DataFrame([{"tick": 1}]),
                "round_officially_ended": pd.DataFrame([{"tick": 1}]),
                "bomb_planted": pd.DataFrame([{"tick": 1}]),
            },
            ticks=None,
            grenades=None,
        )
        assert all(demo.events["round_start"].columns == ["tick", "event_type"])
        assert all(demo.events["round_freeze_end"].columns == ["tick", "event_type"])
        assert all(demo.events["round_end"].columns == ["tick", "event_type"])
        assert all(
            demo.events["round_officially_ended"].columns == ["tick", "event_type"]
        )
        assert all(demo.events["bomb_planted"].columns == ["tick", "event_type"])

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


class TestRoundParser:
    """Class to test the round parsing functions."""

    def test_hltv_rounds(self, hltv_demo: Demo, hltv_demo_round_end_reasons: list[str]):
        """Tests the round parsing for NaVi vs VP at PGL Copenhagen 2024 (CS2).

        Args:
            hltv_demo (Demo): The parsed NaVi vs VP demo.
            hltv_demo_round_end_reasons (list[str]): The expected round end reasons.
        """
        rounds = parse_rounds(hltv_demo)
        assert rounds.shape[0] == 35
        assert rounds.round_start.tolist()[0] == 79_614
        assert rounds.bomb_plant.tolist()[0] == 86_518
        assert pd.isna(rounds.bomb_plant.tolist()[6])
        round_end_reasons = rounds.round_end_reason.tolist()
        for parsed_reason, expected_reason in zip(
            round_end_reasons, hltv_demo_round_end_reasons, strict=False
        ):
            assert parsed_reason == expected_reason

    def test_tick_column_not_found(self, hltv_demo: Demo):
        """Test that we raise an error if the tick column is not found."""
        rounds = parse_rounds(hltv_demo)
        with pytest.raises(KeyError):
            apply_round_id_to_df(rounds, rounds)

    def test_round_id_for_event(self, hltv_demo: Demo):
        """Test that we add the round_id to the DataFrame."""
        rounds = parse_rounds(hltv_demo)
        events = pd.DataFrame({"tick": [80_000], "event": ["test_event"]})
        events = apply_round_id_to_df(events, rounds)
        assert events.round_id.tolist()[0] == 1
