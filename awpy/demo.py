"""Defines the Demo class."""

import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from demoparser2 import DemoParser  # pylint: disable=E0611
from loguru import logger

from awpy.parsers.clock import parse_times
from awpy.parsers.events import (
    parse_bomb,
    parse_damages,
    parse_grenades,
    parse_infernos,
    parse_kills,
    parse_smokes,
    parse_weapon_fires,
)
from awpy.parsers.rounds import parse_rounds
from awpy.parsers.ticks import parse_ticks
from awpy.utils import apply_round_num

PROP_WARNING_LIMIT = 40
DEFAULT_PLAYER_PROPS = [
    "team_name",
    "team_clan_name",
    "X",
    "Y",
    "Z",
    "pitch",
    "yaw",
    "last_place_name",
    "health",
    "armor_value",
    "inventory",
    "current_equip_value",
    "has_defuser",
    "has_helmet",
    "flash_duration",
    "is_strafing",
    "accuracy_penalty",
    "zoom_lvl",
    "ping",
]

DEFAULT_WORLD_PROPS = [
    "game_time",
    "is_bomb_planted",
    "which_bomb_zone",
    "is_freeze_period",
    "is_warmup_period",
    "is_terrorist_timeout",
    "is_ct_timeout",
    "is_technical_timeout",
    "is_waiting_for_resume",
    "is_match_started",
    "game_phase",
]


class Demo:
    """Class to store a demo's data. Called with `Demo(file="...")`."""

    def __init__(
        self,
        path: Path,
        *,
        verbose: bool = False,
        ticks: bool = True,
        rounds: bool = True,
        player_props: Optional[list[str]] = None,
        other_props: Optional[list[str]] = None,
    ) -> None:
        """Instantiate a Demo object using the `demoparser2` backend.

        Args:
            path (Path): Path to demofile.
            verbose (bool, optional): Whether to be log verbosely. Defaults to False.
            ticks (bool, optional): Whether to parse ticks. Defaults to True.
            rounds (bool, optional): Whether to get round information for every event.
            player_props(list[str], optional): List of player props to
                get with each event type. See `demoparser2`.
            other_props(list[str], optional): List of other props to
                get with each event type. See `demoparser2`.

        Raises:
            FileNotFoundError: If the specified `path` to demo does not exist.
        """
        # Pathify any input
        self.path = Path(path)

        # Save params. If/else in case bad params are passed
        self.verbose = verbose
        self.parse_ticks = ticks if ticks else False
        self.parse_rounds = rounds if rounds else False

        # Parser & Metadata
        self.parser = None  # DemoParser
        self.header = None  # DemoHeader
        self.events = {}  # Dictionary of [event, dataframe]

        # Set the prop lists. Always include default props
        self.player_props = (
            DEFAULT_PLAYER_PROPS
            if player_props is None
            else player_props + DEFAULT_PLAYER_PROPS
        )
        self.player_props = list(set(self.player_props))
        self.other_props = (
            DEFAULT_WORLD_PROPS
            if other_props is None
            else other_props + DEFAULT_WORLD_PROPS
        )
        self.other_props = list(set(self.other_props))

        # Data (pandas dataframes)
        self.kills = None
        self.damages = None
        self.bomb = None
        self.smokes = None
        self.infernos = None
        self.weapon_fires = None
        self.rounds = None
        self.grenades = None
        self.ticks = None

        if self.path.exists():
            self.parser = DemoParser(str(self.path))
            self._success(f"Created parser for {self.path}")

            self._parse_demo()
            self._success(f"Parsed raw events for {self.path}")

            self._parse_events()
            self._success(f"Processed events for {self.path}")
        else:
            demo_path_not_found_msg = f"{path} does not exist!"
            raise FileNotFoundError(demo_path_not_found_msg)

    def _success(self, msg: str) -> None:
        """Log a success message.

        Args:
            msg (str): The success message to log.
        """
        if self.verbose:
            logger.success(msg)

    def _warn(self, msg: str) -> None:
        """Log a warning message.

        Args:
            msg (str): The warning message to log.
        """
        if self.verbose:
            logger.warning(msg)

    def _debug(self, msg: str) -> None:
        """Log a debug message.

        Args:
            msg (str): The debug message to log.
        """
        if self.verbose:
            logger.debug(msg)

    def _parse_demo(self) -> None:
        """Parse the demo header and file."""
        if not self.parser:
            no_parser_error_msg = "No parser found!"
            raise ValueError(no_parser_error_msg)

        self.header = parse_header(self.parser.parse_header())

        self._debug(
            f"Found the following game events: {self.parser.list_game_events()}"
        )
        self.events = dict(
            self.parser.parse_events(
                self.parser.list_game_events(),
                player=self.player_props,
                other=self.other_props,
            )
        )

    def _parse_events(self) -> None:
        """Process the raw parsed data."""
        if len(self.events) == 0:
            no_events_error_msg = "No events found!"
            raise ValueError(no_events_error_msg)

        if self.parse_rounds is True:
            self.rounds = parse_rounds(
                self.parser, self.events
            )  # Must pass parser for round start/end events

            self.kills = parse_times(
                apply_round_num(self.rounds, parse_kills(self.events)), self.rounds
            )
            self.damages = parse_times(
                apply_round_num(self.rounds, parse_damages(self.events)), self.rounds
            )
            self.bomb = parse_times(
                apply_round_num(self.rounds, parse_bomb(self.events)), self.rounds
            )
            self.smokes = parse_times(
                apply_round_num(
                    self.rounds, parse_smokes(self.events), tick_col="start_tick"
                ),
                self.rounds,
                tick_col="start_tick",
            )
            self.infernos = parse_times(
                apply_round_num(
                    self.rounds, parse_infernos(self.events), tick_col="start_tick"
                ),
                self.rounds,
                tick_col="start_tick",
            )
            self.weapon_fires = parse_times(
                apply_round_num(self.rounds, parse_weapon_fires(self.events)),
                self.rounds,
            )
            self.grenades = parse_times(
                apply_round_num(self.rounds, parse_grenades(self.parser)), self.rounds
            )

        # Parse ticks
        if self.parse_ticks is True:
            if len(self.player_props) + len(self.other_props) > PROP_WARNING_LIMIT:
                self._warn(
                    f"""
                    Trying to get
                    {len(self.player_props) + len(self.other_props)} properties.
                    This may take a while or cause an out-of-memory error!
                    Try using fewer props or set them
                    dynamically in .player_props and .other_props
                    """
                )
            if self.parse_rounds:
                self.ticks = apply_round_num(
                    self.rounds,
                    parse_ticks(self.parser, self.player_props, self.other_props),
                )
        else:
            self._debug("Skipping tick parsing...")

        # Get round info for every event
        if self.parse_rounds is True:
            for event_name, event in self.events.items():
                if "tick" in event.columns:
                    self.events[event_name] = apply_round_num(
                        self.rounds, self.events[event_name]
                    )
        else:
            self._debug("Skipping round number parsing for events...")

    def compress(self, outpath: Optional[Path] = None) -> None:
        """Saves the demo data to a zip file.

        Args:
            outpath (Path): Path to save the zip file. Defaults to cwd.
        """
        outpath = Path.cwd() if outpath is None else Path(outpath)
        zip_name = outpath / Path(self.path.stem + ".zip")

        with (
            tempfile.TemporaryDirectory() as tmpdirname,
            zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf,
        ):
            # Get the main dataframes
            if self.parse_rounds:
                for df_name, df in [
                    ("kills", self.kills),
                    ("damages", self.damages),
                    ("bomb", self.bomb),
                    ("smokes", self.smokes),
                    ("infernos", self.infernos),
                    ("weapon_fires", self.weapon_fires),
                    ("rounds", self.rounds),
                    ("grenades", self.grenades),
                ]:
                    df_filename = os.path.join(tmpdirname, f"{df_name}.data")
                    df.to_parquet(df_filename, index=False)
                    zipf.write(df_filename, f"{df_name}.data")

            # Write all events
            for event_name, event in self.events.items():
                event_filename = os.path.join(tmpdirname, f"{event_name}-event.data")
                event.to_parquet(event_filename, index=False)
                zipf.write(event_filename, os.path.join("events", f"{event_name}.data"))

            # Write ticks
            if self.ticks is not None:
                ticks_filename = os.path.join(tmpdirname, "ticks.data")
                self.ticks.to_parquet(ticks_filename, index=False)
                zipf.write(ticks_filename, "ticks.data")

            header_filename = os.path.join(tmpdirname, "header.json")
            with open(header_filename, "w", encoding="utf-8") as f:
                json.dump(self.header, f)
            zipf.write(header_filename, "header.json")

            self._success(f"Zipped demo data to {zip_name}")


def parse_header(parsed_header: dict) -> dict:
    """Parse the header of the demofile to a dictionary.

    Args:
        parsed_header (dict): The header of the demofile. Output
            of `parser.parse_header()`.

    Returns:
        dict: The parsed header of the demofile.
    """
    for key, value in parsed_header.items():
        if value == "true":
            parsed_header[key] = True
        elif value == "false":
            parsed_header[key] = False
        else:
            pass  # Loop through and convert strings to bools
    return parsed_header
