"""Defines the Demo class."""

from pathlib import Path

from demoparser2 import DemoParser  # pylint: disable=E0611

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

    def __init__(self, path: Path) -> None:
        """Instantiate a Demo object.

        Args:
            path (Path): Path to demofile.

        Raises:
            FileNotFoundError: If the specified `path` does not exist.
        """
        # Pathify any input
        path = Path(path)

        # Parser & Metadata
        self.parser = None  # DemoParser
        self.header = None  # DemoHeader
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

        if path.exists():
            self.parser = DemoParser(str(path))
            self._parse_demo()
            self._parse_events()
        else:
            demo_path_not_found_msg = f"{path} does not exist!"
            raise FileNotFoundError(demo_path_not_found_msg)

    def _parse_demo(self) -> None:
        """Parse the demo header and file."""
        if not self.parser:
            no_parser_error_msg = "No parser found!"
            raise ValueError(no_parser_error_msg)

        self.header = parse_header(self.parser.parse_header())
        self.events = dict(
            self.parser.parse_events(
                self.parser.list_game_events(),
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
                    "armor_value",
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

    def _parse_events(self) -> None:
        """Process the raw parsed data."""
        if len(self.events.keys()) == 0:
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
        self.ticks = apply_round_num(self.rounds, parse_ticks(self.parser))

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
