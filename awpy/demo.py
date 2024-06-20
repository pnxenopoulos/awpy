"""Defines the Demo class."""

from pathlib import Path
from typing import Optional

from demoparser2 import DemoParser  # pylint: disable=E0611
from loguru import logger

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
        self.get_round_info = rounds if rounds else False

        # Parser & Metadata
        self.parser = None  # DemoParser
        self.header = None  # DemoHeader
        self.player_props = (
            [
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
                "rank",
                "ping",
            ]
            if player_props is None
            else player_props
        )
        self.other_props = (
            [
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
            if other_props is None
            else other_props
        )
        self.events = {}  # Dictionary of [event, dataframe]

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

        self._success(f"Parsed header for {self.path}")

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

        self.rounds = parse_rounds(self.parser)

        self.kills = apply_round_num(self.rounds, parse_kills(self.events))
        self.damages = apply_round_num(self.rounds, parse_damages(self.events))
        self.bomb = apply_round_num(self.rounds, parse_bomb(self.events))
        self.smokes = apply_round_num(
            self.rounds, parse_smokes(self.events), tick_col="start_tick"
        )
        self.infernos = apply_round_num(
            self.rounds, parse_infernos(self.events), tick_col="start_tick"
        )
        self.weapon_fires = apply_round_num(
            self.rounds, parse_weapon_fires(self.events)
        )
        self.grenades = apply_round_num(self.rounds, parse_grenades(self.parser))

        # Parse ticks
        if self.parse_ticks is True:
            if len(self.player_props) + len(self.other_props) > 40:
                self._warn(
                    f"""
                    Trying to get
                    {len(self.player_props) + len(self.other_props)} properties.
                    This may take a while or cause an out-of-memory error!
                    Try using fewer props or set them
                    dynamically in .player_props and .other_props
                    """
                )
            self.ticks = apply_round_num(
                self.rounds,
                parse_ticks(self.parser, self.player_props, self.other_props),
            )

        # Get round info for every event
        if self.get_round_info is True:
            for event_name, event in self.events.items():
                if "tick" in event.columns:
                    self.events[event_name] = apply_round_num(
                        self.rounds, self.events[event_name]
                    )

    @property
    def is_parsed(self) -> bool:
        """Check if the demo has been parsed."""
        return all(
            [
                self.parser,
                self.header,
                self.events,
                self.kills is not None,
                self.damages is not None,
                self.bomb is not None,
                self.smokes is not None,
                self.infernos is not None,
                self.weapon_fires is not None,
                self.rounds is not None,
                self.grenades is not None,
                self.ticks is not None,
            ]
        )


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
