"""This module defines the DemoParser class that handles the core functionality.

Core functionality is parsing and cleaning a csgo demo file.

Example::

    from awpy.parser import DemoParser

    # Create parser object
    # Set log=True above if you want to produce a logfile for the parser
    demo_parser = DemoParser(
        demofile = "og-vs-natus-vincere-m1-dust2.dem",
        demo_id = "OG-NaVi-BLAST2020",
        parse_rate=128,
        trade_time=5,
        buy_style="hltv"
    )

    # Parse the demofile, output results to dictionary
    data = demo_parser.parse()

https://github.com/pnxenopoulos/awpy/blob/main/examples/00_Parsing_a_CSGO_Demofile.ipynb
"""

import json
import logging
import os
import subprocess
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Literal, Unpack, get_args, overload

import pandas as pd
from pydantic import TypeAdapter, ValidationError

from awpy.types import (
    BuyStyle,
    FullParserArgs,
    Game,
    GameActionKey,
    GameRound,
    ParserArgs,
    ParseRate,
    PlayerInfo,
    RoundReturnType,
)
from awpy.utils import check_go_version

if TYPE_CHECKING:
    from pandas.core.arrays.base import ExtensionArray


class DemoParser:
    """DemoParser can parse, load and clean data from a CSGO demofile.

    Can be instantiated without a specified demofile.

    Attributes:
        demofile (string): A string denoting the path to the demo file,
            which ends in .dem. Defaults to ''
        outpath (string): Path where to save the outputfile to.
            Default is current directory
        demo_id (string): A unique demo name/game id.
            Default is inferred from demofile name
        output_file (str): The output file name. Default is 'demoid'+".json"
        log (bool): A boolean indicating if the log should print to stdout.
            Default is False
        parse_rate (int, optional): One of 128, 64, 32, 16, 8, 4, 2, or 1.
            The lower the value, the more frames are collected.
            Indicates spacing between parsed demo frames in ticks. Default is 128.
        parse_frames (bool): Flag if you want to parse frames (trajectory data) or not.
            Default is True
        parse_kill_frames (bool): Flag if you want to parse frames on kills.
            Default is False
        trade_time (int, optional): Length of the window for a trade (in seconds).
            Default is 5.
        dmg_rolled (bool): Boolean if you want damages rolled up.
            As multiple damages for a player can happen in 1 tick from the same weapon.
            Default is False
        parse_chat (bool): Flag if you want to parse chat messages. Default is False
        buy_style (string): Buy style string, one of "hltv" or "csgo"
            Default is "hltv"
        json_indentation (bool): Whether the json file should be pretty printed
            with indentation (larger, more readable)
            or not (smaller, less human readable)
            Default is False
        json (dict): Dictionary containing the parsed json file

    Raises:
        ValueError: Raises a ValueError if the Golang version is lower than 1.18
    """

    def __init__(
        self,
        *,
        demofile: str = "",
        outpath: str | None = None,
        demo_id: str | None = None,
        log: bool = False,
        **parser_args: Unpack[ParserArgs],
    ) -> None:
        """Instatiate a DemoParser.

        Args:
            demofile (string):
                A string denoting the path to the demo file,
                which ends in .dem. Defaults to ''
            outpath (string):
                Path where to save the outputfile to.
                Default is current directory
            demo_id (string):
                A unique demo name/game id.
                Default is inferred from demofile name
            log (bool, optional):
                A boolean indicating if the log should print to stdout.
                Default is False
            **parser_args (ParserArgs): Further keyword args:
                parse_rate (int, optional):
                    One of 128, 64, 32, 16, 8, 4, 2, or 1.
                    The lower the value, the more frames are collected.
                    Indicates spacing between parsed demo frames in ticks.
                    Default is 128.
                parse_frames (bool, optional):
                    Flag if you want to parse frames (trajectory data) or not.
                    Default is True
                parse_kill_frames (bool, optional):
                    Flag if you want to parse frames on kills.
                    Default is False
                trade_time (int, optional):
                    Length of the window for a trade (in seconds).
                    Default is 5.
                dmg_rolled (bool, optional):
                    Boolean if you want damages rolled up.
                    Default is False
                parse_chat (bool, optional):
                    Flag if you want to parse chat messages. Default is False
                buy_style (str, optional):
                    Buy style string, one of "hltv" or "csgo"
                    Default is "hltv"
                json_indentation (bool, optional):
                    Whether the json file should be pretty printed
                    with indentation (larger, more readable)
                    or not (smaller, less human readable)
                    Default is False
        """
        # Set up logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("awpy")
        self.logger.propagate = log

        # Handle demofile and demo_id name.
        # Only take the file name and remove the last extension.
        self.demofile = os.path.abspath(demofile)
        self.logger.info("Initialized awpy DemoParser with demofile %s", self.demofile)

        self._set_demo_id(demo_id, demofile)

        self.logger.info("Setting demo id to %s", self.demo_id)

        if outpath is None:
            outpath = os.path.abspath(os.getcwd())
        else:
            outpath = os.path.abspath(outpath)
        self.output_file = os.path.join(outpath, self.demo_id + ".json")

        self.parser_args: FullParserArgs = {
            "parse_rate": 128,
            "trade_time": 5,
            "parse_frames": True,
            "parse_kill_frames": False,
            "dmg_rolled": False,
            "parse_chat": False,
            "json_indentation": False,
            "buy_style": "hltv",
        }

        self.parser_args.update(parser_args)

        self._check_trade_time()
        self._check_parse_rate()
        self._check_buy_style()

        self.log_settings()

        # Set parse error to False
        self.parse_error = False

        # Initialize json attribute as None
        self._json: Game | None = None

    def log_settings(self) -> None:
        """Log the settings produced in the cosntructor."""
        self.logger.info("Rollup damages set to %s", str(self.dmg_rolled))
        self.logger.info("Parse chat set to %s", str(self.parse_chat))
        self.logger.info("Parse frames set to %s", str(self.parse_frames))
        self.logger.info("Parse kill frames set to %s", str(self.parse_kill_frames))
        self.logger.info(
            "Output json indentation set to %s",
            str(self.json_indentation),
        )
        self.logger.info("Setting trade time to %d", self.trade_time)
        self.logger.info("Setting buy style to %s", str(self.buy_style))

    @property
    def json(self) -> Game | None:
        """Json getter.

        Returns:
            Game: Parsed demo information in json format
        """
        return self._json

    @json.setter
    def json(self, new_json: Game | None) -> None:
        """Validate json shape via pydantic.

        Args:
            new_json (Game | None): Game dict to use.
        """
        if new_json is not None:
            try:
                TypeAdapter(Game).validate_python(new_json)
            except ValidationError:
                self.logger.exception(
                    "Loaded json file does not have correct fields."
                    " This may cause issues later."
                )
        self._json = new_json

    @property
    def buy_style(self) -> BuyStyle:
        """buy_style getter.

        Returns:
            BuyStyle: Current buy_style.
        """
        return self.parser_args["buy_style"]

    @buy_style.setter
    def buy_style(self, buy_style: BuyStyle) -> None:
        """buy_style setter.

        Args:
            buy_style (BuyStyle): buy_style to use.
        """
        self.parser_args["buy_style"] = buy_style

    @property
    def json_indentation(self) -> bool:
        """json_indentation getter.

        Returns:
            bool: Current json_indentation.
        """
        return self.parser_args["json_indentation"]

    @json_indentation.setter
    def json_indentation(self, json_indentation: bool) -> None:
        """json_indentation setter.

        Args:
            json_indentation (bool): json_indentation to use.
        """
        self.parser_args["json_indentation"] = json_indentation

    @property
    def parse_kill_frames(self) -> bool:
        """parse_kill_frames getter.

        Returns:
            bool: Current parse_kill_frames.
        """
        return self.parser_args["parse_kill_frames"]

    @parse_kill_frames.setter
    def parse_kill_frames(self, parse_kill_frames: bool) -> None:
        """parse_kill_frames setter.

        Args:
            parse_kill_frames (bool): parse_kill_frames to use.
        """
        self.parser_args["parse_kill_frames"] = parse_kill_frames

    @property
    def parse_frames(self) -> bool:
        """parse_frames getter.

        Returns:
            bool: Current parse_frames.
        """
        return self.parser_args["parse_frames"]

    @parse_frames.setter
    def parse_frames(self, parse_frames: bool) -> None:
        """parse_frames setter.

        Args:
            parse_frames (bool): parse_frames to use.
        """
        self.parser_args["parse_frames"] = parse_frames

    @property
    def parse_chat(self) -> bool:
        """parse_chat getter.

        Returns:
            bool: Current parse_chat.
        """
        return self.parser_args["parse_chat"]

    @parse_chat.setter
    def parse_chat(self, parse_chat: bool) -> None:
        """parse_chat setter.

        Args:
            parse_chat (bool): parse_chat to use.
        """
        self.parser_args["parse_chat"] = parse_chat

    @property
    def dmg_rolled(self) -> bool:
        """dmg_rolled getter.

        Returns:
            bool: Current dmg_rolled.
        """
        return self.parser_args["dmg_rolled"]

    @dmg_rolled.setter
    def dmg_rolled(self, dmg_rolled: bool) -> None:
        """dmg_rolled setter.

        Args:
            dmg_rolled (bool): dmg_rolled to use.
        """
        self.parser_args["dmg_rolled"] = dmg_rolled

    @property
    def trade_time(self) -> int:
        """Trade time getter.

        Returns:
            int: Current trade time.
        """
        return self.parser_args["trade_time"]

    @trade_time.setter
    def trade_time(self, trade_time: int) -> None:
        """Trade time setter.

        Args:
            trade_time (int): Trade time to use.
        """
        self.parser_args["trade_time"] = trade_time

    def _check_trade_time(self) -> None:
        """Check that trade time is positive and not too large."""
        trade_time_upper_bound = 7
        if self.trade_time <= 0:
            # Handle trade time
            trade_time_default = 5
            self.logger.warning(
                "Trade time can't be negative, setting to default value of %d seconds.",
                trade_time_default,
            )
            self.parser_args["trade_time"] = trade_time_default
        elif self.trade_time > trade_time_upper_bound:
            self.logger.warning(
                "Trade time of %d is rather long. Consider a value between 4-%d.",
                self.trade_time,
                trade_time_upper_bound,
            )

    @property
    def parse_rate(self) -> ParseRate:
        """Parse rate getter.

        Returns:
            int: Current parse rate.
        """
        return self.parser_args["parse_rate"]

    @parse_rate.setter
    def parse_rate(self, parse_rate: ParseRate) -> None:
        """Parse rate setter.

        Args:
            parse_rate (int): Parse rate to use.
        """
        self.parser_args["parse_rate"] = parse_rate

    def _check_parse_rate(self) -> None:
        """Check that parse rate is not too high or low."""
        # Handle parse rate. If the parse rate is less than 64, likely to be slow
        parse_rate_lower_bound = 64
        parse_rate_upper_bound = 256
        if not isinstance(self.parse_rate, int) or self.parse_rate < 1:
            self.logger.warning(
                "Parse rate of %s not acceptable! "
                "Parse rate must be an integer greater than 0.",
                str(self.parse_rate),
            )
            self.parser_args["parse_rate"] = 128
        elif 1 < self.parse_rate < parse_rate_lower_bound:
            self.logger.warning(
                "A parse rate lower than %s may be slow depending on the tickrate "
                "of the demo, which is usually 64 for MM and 128 for pro demos.",
                parse_rate_lower_bound,
            )
        elif self.parse_rate >= parse_rate_upper_bound:
            self.logger.warning(
                "A high parse rate means very few frames. "
                "Only use for testing purposes."
            )
        self.logger.info("Setting parse rate to %s", str(self.parse_rate))

    def _check_buy_style(self) -> None:
        """Check that buy style is valid."""
        # Handle parse rate. If the parse rate is less than 64, likely to be slow
        if self.buy_style not in get_args(BuyStyle):
            self.logger.warning(
                "Buy style specified is not one of %s, "
                "will be set to hltv by default",
                get_args(BuyStyle),
            )
            self.parser_args["buy_style"] = "hltv"
        self.logger.info("Setting buy style to %s", str(self.buy_style))

    def _set_demo_id(self, demo_id: str | None, demofile: str) -> None:
        """Set demo_id.

        If a demo_id was passed in that is used directly.
        Otherwise the demoid is inferred from the demofile.

        Args:
            demo_id (str | None): Optionally demo_id passed to __init__
            demofile (str): Name of the demofile
        """
        if not demo_id:
            self.demo_id = os.path.splitext(
                os.path.basename(demofile.replace("\\", "/"))
            )[0]
        else:
            self.demo_id = demo_id

    def parse_demo(self) -> None:
        """Parse a demofile using the Go script parse_demo.go.

        This function needs the .demofile to be set in the class,
        and the file needs to exist.

        Returns:
            Outputs a JSON file to current working directory.

        Raises:
            ValueError: Raises a ValueError if the Golang version is lower than 1.18
            FileNotFoundError: Raises a FileNotFoundError
                if the demofile path does not exist.
        """
        # Check if Golang version is compatible
        acceptable_go = check_go_version()
        if not acceptable_go:
            error_message = (
                "Error calling Go. "
                "Check if Go is installed using 'go version'."
                " Need at least v1.18.0."
            )
            self.logger.error(error_message)
            raise ValueError(error_message)
        self.logger.info("Go version>=1.18.0")

        # Check if demofile exists
        if not os.path.exists(os.path.abspath(self.demofile)):
            msg = "Demofile path does not exist!"
            self.logger.error(msg)
            raise FileNotFoundError(msg)

        path = os.path.join(os.path.dirname(__file__), "")
        self.logger.info("Running Golang parser from %s", path)
        self.logger.info("Looking for file at %s", self.demofile)
        parser_cmd = [
            "go",
            "run",
            "parse_demo.go",
            "-demo",
            self.demofile,
            "-parserate",
            str(self.parse_rate),
            "-tradetime",
            str(self.trade_time),
            "-buystyle",
            str(self.buy_style),
            "-demoid",
            str(self.demo_id),
            "-out",
            os.path.dirname(self.output_file),
        ]
        if self.dmg_rolled:
            parser_cmd.append("--dmgrolled")
        if self.parse_frames:
            parser_cmd.append("--parseframes")
        if self.parse_kill_frames:
            parser_cmd.append("--parsekillframes")
        if self.json_indentation:
            parser_cmd.append("--jsonindentation")
        if self.parse_chat:
            parser_cmd.append("--parsechat")
        self.logger.debug(parser_cmd)
        with subprocess.Popen(
            parser_cmd,  # noqa: S603
            stdout=subprocess.PIPE,
            cwd=path,
        ) as proc:
            stdout = (
                proc.stdout.read().splitlines() if proc.stdout is not None else None
            )
        if os.path.isfile(self.output_file):
            self.logger.info("Wrote demo parse output to %s", self.output_file)
            self.parse_error = False
        else:
            self.parse_error = True
            self.logger.error("No file produced, error in calling Golang")
            self.logger.error(stdout)

    def read_json(self, json_path: str) -> Game:
        """Reads the JSON file given a JSON path.

        Can be used to read in already processed demofiles.

        Args:
            json_path (string): Path to JSON file

        Returns (Game):
            JSON in Python dictionary form

        Raises:
            FileNotFoundError: Raises a FileNotFoundError if the JSON path doesn't exist
        """
        # Check if JSON exists
        if not os.path.exists(json_path):
            self.logger.error("JSON path does not exist!")
            msg = "JSON path does not exist!"
            raise FileNotFoundError(msg)

        # Read in json to .json attribute
        with open(json_path, encoding="utf8") as game_data:
            demo_data: Game = json.load(game_data)

        self.json = demo_data
        self.logger.info(
            "JSON data loaded, available in the `json` attribute to parser"
        )
        return demo_data

    @overload
    def parse(
        self, *, return_type: Literal["json"] = "json", clean: bool = ...
    ) -> Game:
        ...

    @overload
    def parse(self, *, return_type: Literal["df"], clean: bool = ...) -> dict[str, Any]:
        ...

    def parse(
        self, *, return_type: RoundReturnType = "json", clean: bool = True
    ) -> Game | dict[str, Any]:
        """Wrapper for parse_demo() and read_json(). Use to parse a demo.

        Args:
            return_type (string, optional): Either "json" or "df". Default is "json"
            clean (bool, optional): True to run clean_rounds.
                Otherwise, uncleaned data is returned. Defaults to True.

        Returns:
            A dictionary of output which
            is parsed to a JSON file in the working directory.

        Raises:
            ValueError: Raises a ValueError if the return_type is not "json" or "df"
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        self.parse_demo()
        self.read_json(json_path=self.output_file)
        if clean:
            self.clean_rounds()
        if self.json:
            self.logger.info("JSON output found")
            if return_type == "json":
                return self.json
            if return_type == "df":
                demo_data = self.parse_json_to_df()
                self.logger.info("Returned dataframe output")
                return demo_data
            msg = "Parse return_type must be either 'json' or 'df'"
            self.logger.error(msg)
            raise ValueError(msg)
        msg = "No JSON parsed! Error in producing JSON."
        self.logger.error(msg)
        raise AttributeError(msg)

    def parse_json_to_df(self) -> dict[str, Any]:
        # sourcery skip: extract-method
        """Returns JSON into dictionary where keys correspond to data frames.

        Returns:
            A dictionary of output

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            demo_data: dict[str, Any] = {
                "matchID": self.json["matchID"],
                "clientName": self.json["clientName"],
                "mapName": self.json["mapName"],
                "tickRate": self.json["tickRate"],
                "playbackTicks": self.json["playbackTicks"],
                "rounds": self._parse_rounds(),
            }
            # Kills
            demo_data["kills"] = self._parse_action("kills")
            # Damages
            demo_data["damages"] = self._parse_action("damages")
            # Grenades
            demo_data["grenades"] = self._parse_action("grenades")
            # Flashes
            demo_data["flashes"] = self._parse_action("flashes")
            # Weapon Fires
            demo_data["weaponFires"] = self._parse_action("weaponFires")
            # Bomb Events
            demo_data["bombEvents"] = self._parse_action("bombEvents")
            # Frames
            demo_data["frames"] = self._parse_frames()
            # Player Frames
            demo_data["playerFrames"] = self._parse_player_frames()
            self.logger.info("Returned dataframe output")
            return demo_data
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    # Can not easily extract due to type checking
    def _parse_frames(self) -> pd.DataFrame:  # sourcery skip: extract-method
        """Returns frames as a Pandas dataframe.

        Returns:
            A Pandas dataframe where each row is a frame (game state) in the demo,
            which is a discrete point of time.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            frames_dataframes = []
            for game_round in self.json["gameRounds"] or []:
                for frame in game_round["frames"] or []:
                    frame_item: dict[str, Any] = {"roundNum": game_round["roundNum"]}
                    for k in ("tick", "seconds"):
                        frame_item[k] = frame[k]
                    frame_item["ctTeamName"] = frame["ct"]["teamName"]
                    frame_item["ctEqVal"] = frame["ct"]["teamEqVal"]
                    frame_item["ctAlivePlayers"] = frame["ct"]["alivePlayers"]
                    frame_item["ctUtility"] = frame["ct"]["totalUtility"]
                    frame_item["tTeamName"] = frame["t"]["teamName"]
                    frame_item["tEqVal"] = frame["t"]["teamEqVal"]
                    frame_item["tAlivePlayers"] = frame["t"]["alivePlayers"]
                    frame_item["tUtility"] = frame["t"]["totalUtility"]
                    frames_dataframes.append(frame_item)
            frames_df = pd.DataFrame(frames_dataframes)
            frames_df["matchID"] = self.json["matchID"]
            frames_df["mapName"] = self.json["mapName"]
            return pd.DataFrame(frames_dataframes)
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    def add_player_specific_information(
        self, player_item: dict[str, Any], player: PlayerInfo
    ) -> None:
        """Add player specific information to player_item dict.

        Args:
            player_item (dict[str, Any]): Dictionary containing player specific
                and general information for a frame.
            player (PlayerInfo): TypedDict containing information for a single player
                for a specific frame.
        """
        for col, val in player.items():
            if col != "inventory":
                player_item[col] = val

    def _parse_player_frames(self) -> pd.DataFrame:
        # Can not easily extract due to type checking
        # sourcery skip: extract-method
        """Returns player frames as a Pandas dataframe.

        Returns:
            A Pandas dataframe where each row is a player's attributes
            at a given frame (game state).

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            player_frames = []
            for game_round in self.json["gameRounds"] or []:
                for frame in game_round["frames"] or []:
                    for side in ("ct", "t"):
                        players = frame[side]["players"]
                        if players is None:
                            continue
                        for player in players:
                            player_item: dict[str, Any] = {
                                "roundNum": game_round["roundNum"],
                                "tick": frame["tick"],
                                "seconds": frame["seconds"],
                                "side": side,
                                "teamName": frame[side]["teamName"],
                            }
                            self.add_player_specific_information(player_item, player)
                            player_frames.append(player_item)
            player_frames_df = pd.DataFrame(player_frames)
            player_frames_df["matchID"] = self.json["matchID"]
            player_frames_df["mapName"] = self.json["mapName"]
            return pd.DataFrame(player_frames_df)
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    def _parse_rounds(self) -> pd.DataFrame:
        """Returns rounds as a Pandas dataframe.

        Returns:
            A Pandas dataframe where each row is a round

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            rounds = []
            cols = (
                "roundNum",
                "startTick",
                "freezeTimeEndTick",
                "endTick",
                "endOfficialTick",
                "tScore",
                "ctScore",
                "endTScore",
                "endCTScore",
                "tTeam",
                "ctTeam",
                "winningSide",
                "winningTeam",
                "losingTeam",
                "roundEndReason",
                "ctFreezeTimeEndEqVal",
                "ctRoundStartEqVal",
                "ctRoundSpendMoney",
                "ctBuyType",
                "tFreezeTimeEndEqVal",
                "tRoundStartEqVal",
                "tRoundSpendMoney",
                "tBuyType",
            )
            for game_round in self.json["gameRounds"] or []:
                round_item: dict[str, Any] = {}
                for k in cols:
                    round_item[k] = game_round[k]
                    round_item["matchID"] = self.json["matchID"]
                    round_item["mapName"] = self.json["mapName"]
                rounds.append(round_item)
            return pd.DataFrame(rounds)
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    def _parse_action(self, action: GameActionKey) -> pd.DataFrame:
        """Returns action as a Pandas dataframe.

        Args:
            action (str): Action dict to convert to dataframe.

        Returns:
            A Pandas dataframe where each row is a damage event.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            actions: dict[str, list] = defaultdict(list)
            for game_round in self.json["gameRounds"] or []:
                for game_action in game_round[action] or []:
                    for key, value in game_action.items():
                        actions[key].append(value)
                    actions["roundNum"].append(game_round["roundNum"])
                    actions["matchID"].append(self.json["matchID"])
                    actions["mapName"].append(self.json["mapName"])
            # pd.array automatically infors nullable ints.
            actions_array: dict[str, ExtensionArray] = {
                key: pd.array(value_list) for key, value_list in actions.items()
            }
            return pd.DataFrame(actions_array)
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    @overload
    def clean_rounds(
        self,
        *,
        remove_no_frames: bool = ...,
        remove_warmups: bool = ...,
        remove_knifes: bool = ...,
        remove_bad_timings: bool = ...,
        remove_excess_players: bool = ...,
        remove_excess_kills: bool = ...,
        remove_bad_endings: bool = ...,
        remove_bad_scoring: bool = ...,
        return_type: Literal["json"] = "json",
        save_to_json: bool = ...,
    ) -> Game:
        ...

    @overload
    def clean_rounds(
        self,
        *,
        remove_no_frames: bool = ...,
        remove_warmups: bool = ...,
        remove_knifes: bool = ...,
        remove_bad_timings: bool = ...,
        remove_excess_players: bool = ...,
        remove_excess_kills: bool = ...,
        remove_bad_endings: bool = ...,
        remove_bad_scoring: bool = ...,
        return_type: Literal["df"] = ...,
        save_to_json: bool = ...,
    ) -> dict[str, Any]:
        ...

    def clean_rounds(
        self,
        *,
        remove_no_frames: bool = True,
        remove_warmups: bool = True,
        remove_knifes: bool = True,
        remove_bad_timings: bool = True,
        remove_excess_players: bool = True,
        remove_excess_kills: bool = True,
        remove_bad_endings: bool = True,
        remove_bad_scoring: bool = True,
        return_type: RoundReturnType = "json",
        save_to_json: bool = True,
    ) -> Game | dict[str, Any]:
        """Cleans a parsed demofile JSON.

        Args:
            remove_no_frames (bool, optional): Remove rounds where there are no frames.
                Default to True.
            remove_warmups (bool, optional): Remove warmup rounds. Defaults to True.
            remove_knifes (bool, optional): Remove knife rounds. Defaults to True.
            remove_bad_timings (bool, optional): Remove bad timings. Defaults to True.
            remove_excess_players (bool, optional):
                Remove rounds with more than 5 players. Defaults to True.
            remove_excess_kills (bool, optional): Remove rounds with more than 10 kills.
                Defaults to True.
            remove_bad_endings (bool, optional):
                Remove rounds with bad round end reasons. Defaults to True.
            remove_bad_scoring (bool, optional): Remove rounds where the scoring is off
                Like scores going below the previous round's. Defaults to False.
            return_type (str, optional): Return JSON or DataFrame. Defaults to "json".
            save_to_json (bool, optional): Whether to write the JSON to a file.
                Defaults to True.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
            ValueError: Raises a ValueError if the return type is neither
                'json' nor 'df'

        Returns:
            dict: A dictionary of the cleaned demo.
        """
        if self.json:
            if remove_no_frames:
                self.remove_rounds_with_no_frames()
            if remove_warmups:
                self.remove_warmups()
            if remove_knifes:
                self.remove_knife_rounds()
            if remove_bad_timings:
                self.remove_time_rounds()
            if remove_excess_players:
                self.remove_excess_players()
            if remove_excess_kills:
                self.remove_excess_kill_rounds()
            if remove_bad_endings:
                self.remove_end_round()
            if remove_bad_scoring:
                self.remove_bad_scoring()
            self.renumber_rounds()
            self.renumber_frames()
            # self.rescore_rounds() -- Need to edit to take into account half switches
            if save_to_json:
                self.write_json()
            if return_type == "json":
                return self.json
            if return_type == "df":
                demo_data = self.parse_json_to_df()
                self.logger.info("Returned cleaned dataframe output")
                return demo_data
            msg = f"Invalid return_type of {return_type}. Use 'json' or 'df' instead!"
            raise ValueError(msg)
        msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
        self.logger.error(msg)
        raise AttributeError(msg)

    def write_json(self) -> None:
        """Rewrite the JSON file."""
        with open(self.output_file, "w", encoding="utf8") as file_path:
            json.dump(
                self.json, file_path, indent=(1 if self.json_indentation else None)
            )

    def renumber_rounds(self) -> None:
        """Renumbers the rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute
                has no "gameRounds" key.
        """
        if self.json:
            if self.json["gameRounds"] is None:
                return
            for i, _r in enumerate(self.json["gameRounds"]):
                self.json["gameRounds"][i]["roundNum"] = i + 1
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def renumber_frames(self) -> None:
        """Renumbers the frames.

        Needed since cleaning can remove frames and cause
        some indices to be skipped.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute
                has no "gameRounds" key.
        """
        if self.json:
            if self.json["gameRounds"] is None:
                return
            for index, frame in enumerate(
                frame
                for game_round in self.json["gameRounds"]
                for frame in game_round["frames"] or []
            ):
                frame["globalFrameID"] = index
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def rescore_rounds(self) -> None:
        """Rescore the rounds based on round end reason.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute
                has no "gameRounds" key.
        """
        if self.json:
            if self.json["gameRounds"] is None:
                return
            for i, _r in enumerate(self.json["gameRounds"]):
                if i == 0:
                    self.json["gameRounds"][i]["tScore"] = 0
                    self.json["gameRounds"][i]["ctScore"] = 0
                    if self.json["gameRounds"][i]["winningSide"] == "ct":
                        self.json["gameRounds"][i]["endCTScore"] = 1
                        self.json["gameRounds"][i]["endTScore"] = 0
                    if self.json["gameRounds"][i]["winningSide"] == "t":
                        self.json["gameRounds"][i]["endCTScore"] = 0
                        self.json["gameRounds"][i]["endTScore"] = 1
                elif i > 0:
                    self.json["gameRounds"][i]["tScore"] = self.json["gameRounds"][
                        i - 1
                    ]["endTScore"]
                    self.json["gameRounds"][i]["ctScore"] = self.json["gameRounds"][
                        i - 1
                    ]["endCTScore"]
                    if self.json["gameRounds"][i]["winningSide"] == "ct":
                        self.json["gameRounds"][i]["endCTScore"] = (
                            self.json["gameRounds"][i]["ctScore"] + 1
                        )
                        self.json["gameRounds"][i]["endTScore"] = self.json[
                            "gameRounds"
                        ][i]["tScore"]
                    if self.json["gameRounds"][i]["winningSide"] == "t":
                        self.json["gameRounds"][i]["endCTScore"] = self.json[
                            "gameRounds"
                        ][i]["ctScore"]
                        self.json["gameRounds"][i]["endTScore"] = (
                            self.json["gameRounds"][i]["tScore"] + 1
                        )
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def _has_winner_and_not_winner(self, game_round: GameRound) -> bool:
        tie_score = 15
        ot_tie_score = 3
        regular_valid_t_win = (game_round["endTScore"] == tie_score + 1) and (
            game_round["endCTScore"] < tie_score
        )
        regular_valid_ct_win = (
            game_round["endCTScore"] == tie_score + 1
            and game_round["endTScore"] < tie_score
        )
        # OT win scores are of the type:
        # 15 + (4xN) with N a natural numbers (1, 2, 3, ...)
        # So 19, 23, 27, ...
        # So if you substract 15 from an OT winning round
        # the number is divisible by 4
        ot_valid_ct_win = (game_round["endCTScore"] - tie_score) % (
            ot_tie_score + 1
        ) == 0 and game_round["endTScore"] < game_round["endCTScore"]
        ot_valid_t_win = (game_round["endTScore"] - tie_score) % (
            ot_tie_score + 1
        ) == 0 and game_round["endCTScore"] < game_round["endTScore"]
        return (
            regular_valid_ct_win
            or regular_valid_t_win
            or ot_valid_ct_win
            or ot_valid_t_win
        )

    def remove_bad_scoring(self) -> None:
        """Removes rounds where the scoring is bad.

        We loop through the rounds:
        If the round ahead has equal or less score, we do not add the current round.
        If the round ahead has +1 score, we add the current round

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if self.json["gameRounds"] is None:
                return
            cleaned_rounds = []
            for i, game_round in enumerate(self.json["gameRounds"]):
                current_round_total = (
                    game_round["tScore"]
                    + game_round["endTScore"]
                    + game_round["ctScore"]
                    + game_round["endCTScore"]
                )
                if i < len(self.json["gameRounds"]) - 1:
                    # Non-OT rounds
                    lookahead_round = self.json["gameRounds"][i + 1]
                    lookahead_round_total = (
                        lookahead_round["tScore"]
                        + lookahead_round["endTScore"]
                        + lookahead_round["ctScore"]
                        + lookahead_round["endCTScore"]
                    )

                    if (
                        # Next round should have higher score than current
                        (lookahead_round_total > current_round_total)
                        # Valid rounds have a winner and a not winner
                        or self._has_winner_and_not_winner(game_round=game_round)
                    ):
                        cleaned_rounds.append(game_round)
                else:
                    lookback_round = self.json["gameRounds"][i - 1]
                    lookback_round_total = (
                        lookback_round["tScore"]
                        + lookback_round["endTScore"]
                        + lookback_round["ctScore"]
                        + lookback_round["endCTScore"]
                    )
                    if current_round_total > lookback_round_total:
                        cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_rounds_with_no_frames(self) -> None:
        """Removes rounds with no frames.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if not self.parse_frames:
                self.logger.warning(
                    "parse_frames is set to False, "
                    "must be true for remove_no_frames to work. "
                    "Skipping remove_no_frames."
                )
            else:
                cleaned_rounds = [
                    game_round
                    for game_round in self.json["gameRounds"] or []
                    if len(game_round["frames"] or []) > 0
                ]
                self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_excess_players(self) -> None:
        """Removes rounds where there are more than 5 players on a side.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if not self.parse_frames:
                self.logger.warning(
                    "parse_frames is set to False, "
                    "must be true for remove_excess_players to work. "
                    "Skipping remove_excess_players."
                )
            else:
                cleaned_rounds = []
                # Remove rounds where the number of players is too large
                n_players = 5
                for game_round in self.json["gameRounds"] or []:
                    if not game_round["frames"]:
                        continue
                    game_frame = game_round["frames"][0]
                    player_lists = (
                        game_frame["t"]["players"],
                        game_frame["ct"]["players"],
                    )
                    # Remove if any side has > 5 players
                    # Remove if both sides are None
                    if all(
                        len(player_list or []) <= n_players
                        for player_list in player_lists
                    ) and any(player_list is not None for player_list in player_lists):
                        cleaned_rounds.append(game_round)
                self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_warmups(self) -> None:
        """Removes warmup rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            # Remove warmups where the demo may have started recording
            # in the middle of a warmup round
            if "warmupChanged" in self.json["matchPhases"]:
                if (
                    self.json["matchPhases"]["warmupChanged"] is not None
                    and len(self.json["matchPhases"]["warmupChanged"]) > 1
                ):
                    last_warmup_changed = self.json["matchPhases"]["warmupChanged"][1]
                    for game_round in self.json["gameRounds"] or []:
                        if (game_round["startTick"] > last_warmup_changed) and (
                            not game_round["isWarmup"]
                        ):
                            cleaned_rounds.append(game_round)
                        if game_round["startTick"] == last_warmup_changed:
                            cleaned_rounds.append(game_round)
                else:
                    cleaned_rounds.extend(
                        game_round
                        for game_round in self.json["gameRounds"] or []
                        if not game_round["isWarmup"]
                    )
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_end_round(self, bad_endings: list[str] | None = None) -> None:
        """Removes rounds with bad end reason.

        Args:
            bad_endings (list, optional): List of bad round end reasons.
                Defaults to ["Draw", "Unknown", ""].

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if bad_endings is None:
            bad_endings = ["Draw", "Unknown", ""]
        if self.json:
            if (game_rounds := self.json["gameRounds"]) is None:
                return
            cleaned_rounds = [
                game_round
                for game_round in game_rounds
                if game_round["roundEndReason"] not in bad_endings
            ]
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_knife_rounds(self) -> None:
        """Removes knife rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if (game_rounds := self.json["gameRounds"]) is None:
                return
            cleaned_rounds = []
            for game_round in game_rounds:
                if game_round["isWarmup"]:
                    continue
                if (kill_actions := game_round["kills"]) is None:
                    continue
                total_kills = len(kill_actions)
                total_knife_kills = sum(
                    1 for k in kill_actions if k["weapon"] == "Knife"
                )
                if (total_knife_kills != total_kills) | (total_knife_kills == 0):
                    cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_excess_kill_rounds(self) -> None:
        """Removes rounds with more than 10 kills.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            n_total_players = 10
            cleaned_rounds = [
                game_round
                for game_round in self.json["gameRounds"] or []
                if (
                    not game_round["isWarmup"]
                    and len(game_round["kills"] or []) <= n_total_players
                )
            ]
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)

    def remove_time_rounds(self) -> None:
        """Remove rounds with odd round timings.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = [
                game_round
                for game_round in self.json["gameRounds"] or []
                if (
                    (game_round["startTick"] <= game_round["endTick"])
                    and (game_round["startTick"] <= game_round["endOfficialTick"])
                    and (game_round["startTick"] <= game_round["freezeTimeEndTick"])
                )
            ]
            self.json["gameRounds"] = cleaned_rounds
        else:
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            self.logger.error(msg)
            raise AttributeError(msg)
