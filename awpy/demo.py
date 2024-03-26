"""Defines the Demo class."""

import os
from importlib.metadata import version
from typing import Any

import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611
from pydantic import BaseModel, ConfigDict, model_validator

from awpy.parsers import (
    parse_bomb,
    parse_damages,
    parse_grenades,
    parse_infernos,
    parse_kills,
    parse_rounds,
    parse_smokes,
    parse_ticks,
    parse_weapon_fires,
)
from awpy.utils import apply_round_num


class DemoHeader(BaseModel):
    """Class to store demo header information."""

    demo_version_guid: str
    network_protocol: str
    fullpackets_version: str
    allow_clientside_particles: bool
    addons: str
    client_name: str
    map_name: str
    server_name: str
    demo_version_name: str
    allow_clientside_entities: bool
    demo_file_stamp: str
    game_directory: str


class Demo(BaseModel):  # pylint: disable=too-many-instance-attributes
    """Class to store a demo's data. Called with `Demo(file="...")`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Parser & Metadata
    file: str
    parser: DemoParser
    header: DemoHeader
    events: dict[str, pd.DataFrame]
    version: str

    # Data
    kills: pd.DataFrame
    damages: pd.DataFrame
    bomb: pd.DataFrame
    smokes: pd.DataFrame
    infernos: pd.DataFrame
    weapon_fires: pd.DataFrame
    rounds: pd.DataFrame
    grenades: pd.DataFrame
    ticks: pd.DataFrame

    @model_validator(mode="before")
    @classmethod
    def parse_demo(cls: type["Demo"], values: dict[str, Any]) -> dict[str, Any]:
        """Parse the demo file.

        Args:
            values (dict[str, Any]): Passed in arguments.

        Raises:
            ValueError: If `file` is not a passed argument.
            FileNotFoundError: If specified filepath does not exist.

        Returns:
            dict[str, Any]: The parsed demo data.
        """
        file = values.get("file")
        if file is None:
            file_arg_error_msg = "Must specify filepath with `file` argument."
            raise ValueError(file_arg_error_msg)
        if not os.path.exists(file):
            file_not_found_error_msg = f"{file} not found."
            raise FileNotFoundError(file_not_found_error_msg)

        parser = DemoParser(file)
        header = parse_header(parser.parse_header())
        events = dict(
            parser.parse_events(
                parser.list_game_events(),
                player=[
                    "X",
                    "Y",
                    "Z",
                    "last_place_name",
                    "flash_duration",
                    "is_strafing",
                    "accuracy_penalty",
                    "zoom_lvl",
                    "health",
                    "armor",
                    "inventory",
                    "current_equip_value",
                    "rank",
                    "ping",
                    "has_defuser",
                    "has_helmet",
                    "pitch",
                    "yaw",
                    "team_name",
                    "team_clan_name",
                ],
                other=[
                    # Bomb
                    "is_bomb_planted",
                    "which_bomb_zone",
                    # State
                    "is_freeze_period",
                    "is_warmup_period",
                    "is_terrorist_timeout",
                    "is_ct_timeout",
                    "is_technical_timeout",
                    "is_waiting_for_resume",
                    "is_match_started",
                    "game_phase",
                ],
            )
        )

        # Parse the demo
        rounds = parse_rounds(parser)

        kills = apply_round_num(rounds, parse_kills(events))
        damages = apply_round_num(rounds, parse_damages(events))
        bomb = apply_round_num(rounds, parse_bomb(events))
        smokes = apply_round_num(rounds, parse_smokes(events), tick_col="start_tick")
        infernos = apply_round_num(
            rounds, parse_infernos(events), tick_col="start_tick"
        )
        weapon_fires = apply_round_num(rounds, parse_weapon_fires(events))
        grenades = apply_round_num(rounds, parse_grenades(parser))
        ticks = apply_round_num(rounds, parse_ticks(parser))

        return {
            # Parser & Metadata
            "file": file,
            "parser": parser,
            "header": header,
            "events": events,
            "version": version("awpy"),
            "hash": None,
            # Parsed from event dictionary
            "kills": kills,
            "damages": damages,
            "bomb": bomb,
            "smokes": smokes,
            "infernos": infernos,
            "weapon_fires": weapon_fires,
            # Parsed from parser
            "rounds": rounds,
            "grenades": grenades,
            "ticks": ticks,
        }


def parse_header(parsed_header: dict) -> DemoHeader:
    """Parse the header of the demofile.

    Args:
        parsed_header (dict): The header of the demofile. Output
            of `parser.parse_header()`.

    Returns:
        DemoHeader: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
        else:
            pass  # Loop through and convert strings to bools
    return DemoHeader(**parsed_header)
