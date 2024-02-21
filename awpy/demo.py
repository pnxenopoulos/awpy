"""Defines the Demo class."""

import os

import pandas as pd
from demoparser2 import DemoParser  # pylint: disable=E0611
from pydantic import BaseModel, ConfigDict

from awpy.parsers import (
    parse_bomb,
    parse_damages,
    parse_flashes,
    parse_grenades,
    parse_infernos,
    parse_kills,
    parse_smokes,
    parse_ticks,
    parse_weapon_fires,
)


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
    """Class to store a demo's data."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Parser & Metadata
    file: str
    parser: DemoParser
    header: DemoHeader

    # Data
    grenades: pd.DataFrame
    kills: pd.DataFrame
    damages: pd.DataFrame
    bomb: pd.DataFrame
    smokes: pd.DataFrame
    flashes: pd.DataFrame
    infernos: pd.DataFrame
    weapon_fires: pd.DataFrame
    footstep: pd.DataFrame
    ticks: pd.DataFrame
    button_presses: pd.DataFrame

    def __init__(self, file: str) -> None:  # pylint: disable=super-init-not-called
        """Create a demo object.

        Args:
            file (str): Path to the demo file

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If there is an error parsing the demo

        Returns:
            Demo: The demo object
        """
        if not os.path.exists(file):
            file_not_found_msg = f"{file} not found."
            raise FileNotFoundError(file_not_found_msg)

        # Create the parser and parse the events
        self.parser = DemoParser(file)
        self.header = parse_header(self.parser.parse_header())

        # Parse the demo
        # Need to add rounds parsing here
        self.grenades = parse_grenades(self.parser)
        self.kills = parse_kills(self.parser)
        self.damages = parse_damages(self.parser)
        self.bomb = parse_bomb(self.parser)
        self.smokes = parse_smokes(self.parser)
        self.flashes = parse_flashes(self.parser)
        self.infernos = parse_infernos(self.parser)
        self.weapon_fires = parse_weapon_fires(self.parser)
        self.ticks = parse_ticks(self.parser)


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
