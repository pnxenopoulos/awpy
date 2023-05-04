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
from typing import TYPE_CHECKING, Any, Literal, cast, get_args

import pandas as pd

if TYPE_CHECKING:
    from pandas.core.arrays.base import ExtensionArray

from awpy.types import ColsType, Game, GameActionKey, GameRound, PlayerInfo
from awpy.utils import check_go_version


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
        parse_rate: int = 128,
        parse_frames: bool = True,
        parse_kill_frames: bool = False,
        trade_time: int = 5,
        dmg_rolled: bool = False,
        parse_chat: bool = False,
        buy_style: str = "hltv",
        json_indentation: bool = False,
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
            parse_rate (int, optional):
                One of 128, 64, 32, 16, 8, 4, 2, or 1.
                The lower the value, the more frames are collected.
                Indicates spacing between parsed demo frames in ticks. Default is 128.
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

        self.set_demo_id(demo_id, demofile)

        self.logger.info("Setting demo id to %s", self.demo_id)

        self.output_file = self.demo_id + ".json"

        if outpath is None:
            self.outpath = os.path.abspath(os.getcwd())
        else:
            self.outpath = os.path.abspath(outpath)

        self._parse_rate = 128
        self.parse_rate = parse_rate
        self._trade_time = 5
        self.trade_time = trade_time

        self.logger.info("Setting trade time to %d", self.trade_time)

        # Handle buy style
        if buy_style not in ["hltv", "csgo"]:
            self.logger.warning(
                "Buy style specified is not one of hltv, csgo, "
                "will be set to hltv by default"
            )
            self.buy_style = "hltv"
        else:
            self.buy_style = buy_style
        self.logger.info("Setting buy style to %s", str(self.buy_style))

        self.dmg_rolled = dmg_rolled
        self.parse_chat = parse_chat
        self.parse_frames = parse_frames
        self.parse_kill_frames = parse_kill_frames
        self.json_indentation = json_indentation

        self.log_settings()

        # Set parse error to False
        self.parse_error = False

        # Initialize json attribute as None
        self.json: Game | None = None

    def log_settings(self) -> None:
        """Log the settings produced in the cosntructor."""
        self.logger.info("Rollup damages set to %s", str(self.dmg_rolled))
        self.logger.info("Parse chat set to %s", str(self.parse_chat))
        self.logger.info("Parse frames set to %s", str(self.parse_frames))
        self.logger.info("Parse kill frames set to %s", str(self.parse_kill_frames))
        self.logger.info(
            "Output json indentation set to %s", str(self.json_indentation)
        )

    @property
    def trade_time(self) -> int:
        """Trade time getter.

        Returns:
            int: Current trade time.
        """
        return self._trade_time

    @trade_time.setter
    def trade_time(self, trade_time: int) -> None:
        """Set trade time of the parser.

        User will be warned about unusual values.

        Args:
            trade_time (int): Trade time to user.
        """
        # Handle trade time
        trade_time_default = 5
        trade_time_upper_bound = 7
        self._trade_time = trade_time
        if trade_time <= 0:
            self.logger.warning(
                "Trade time can't be negative, setting to default value of %d seconds.",
                trade_time_default,
            )
            self._trade_time = trade_time_default
        elif trade_time > trade_time_upper_bound:
            self.logger.warning(
                "Trade time of %d is rather long. Consider a value between 4-%d.",
                trade_time,
                trade_time_upper_bound,
            )

    @trade_time.deleter
    def trade_time(self) -> None:
        """Trade time deleter."""
        del self._trade_time

    @property
    def parse_rate(self) -> int:
        """Parse rate getter.

        Returns:
            int: Current parse rate.
        """
        return self._parse_rate

    @parse_rate.setter
    def parse_rate(self, parse_rate: int) -> None:
        """Set the parse rate of the parser.

        Should be a positive integer.
        User will be warned about values that are unusually
        high or low.

        Args:
            parse_rate (int): Parse rate to use.
        """
        # Handle parse rate. If the parse rate is less than 64, likely to be slow
        if parse_rate < 1:
            self.logger.warning(
                "Parse rate of %s not acceptable! "
                "Parse rate must be an integer greater than 0.",
                str(parse_rate),
            )
            parse_rate = 128
            self._parse_rate = parse_rate
        parse_rate_lower_bound = 64
        parse_rate_upper_bound = 256
        if 1 < parse_rate < parse_rate_lower_bound:
            self.logger.warning(
                "A parse rate lower than %s may be slow depending on the tickrate "
                "of the demo, which is usually 64 for MM and 128 for pro demos.",
                parse_rate_lower_bound,
            )
            self._parse_rate = parse_rate
        elif parse_rate >= parse_rate_upper_bound:
            self.logger.warning(
                "A high parse rate means very few frames. "
                "Only use for testing purposes."
            )
            self._parse_rate = parse_rate
        else:
            self._parse_rate = parse_rate
        self.logger.info("Setting parse rate to %s", str(self.parse_rate))

    @parse_rate.deleter
    def parse_rate(self) -> None:
        """Parse rate deleter."""
        del self._parse_rate

    def set_demo_id(self, demo_id: str | None, demofile: str) -> None:
        """Set demo_id.

        If a demo_id was passed in that is used directly.
        Otherwise the demoid is inferred from the demofile.

        Args:
            demo_id (str | None): Optionally demo_id passed to __init__
            demofile (str | None): Name of the demofile
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
            self.outpath,
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
        with subprocess.Popen(
            parser_cmd,  # noqa: S603
            stdout=subprocess.PIPE,
            cwd=path,
        ) as proc:
            stdout = (
                proc.stdout.read().splitlines() if proc.stdout is not None else None
            )
        self.output_file = self.demo_id + ".json"
        if os.path.isfile(self.outpath + "/" + self.output_file):
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

    def parse(
        self, *, return_type: str = "json", clean: bool = True
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
        self.read_json(json_path=self.outpath + "/" + self.output_file)
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
        """Returns JSON into dictionary where keys correspond to data frames.

        Returns:
            A dictionary of output

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            demo_data: dict[str, Any] = {}
            demo_data["matchID"] = self.json["matchID"]
            demo_data["clientName"] = self.json["clientName"]
            demo_data["mapName"] = self.json["mapName"]
            demo_data["tickRate"] = self.json["tickRate"]
            demo_data["playbackTicks"] = self.json["playbackTicks"]
            # Rounds
            demo_data["rounds"] = self._parse_rounds()
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

    def _parse_frames(self) -> pd.DataFrame:
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
                    frame_item: dict[str, Any] = {}
                    frame_item["roundNum"] = game_round["roundNum"]
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
                            player_item: dict[str, Any] = {}
                            player_item["roundNum"] = game_round["roundNum"]
                            player_item["tick"] = frame["tick"]
                            player_item["seconds"] = frame["seconds"]
                            player_item["side"] = side
                            player_item["teamName"] = frame[side]["teamName"]
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
        self.logger.error(
            msg
        )
        raise AttributeError(
            msg
        )

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
        return_type: str = "json",
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
        with open(
            self.outpath + "/" + self.output_file, "w", encoding="utf8"
        ) as file_path:
            json.dump(
                self.json, file_path, indent=(1 if self.json_indentation else None)
            )

    def renumber_rounds(self) -> None:
        """Renumbers the rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute
                has a "gameRounds" key.
        """
        if self.json and self.json["gameRounds"]:
            for i, _r in enumerate(self.json["gameRounds"]):
                self.json["gameRounds"][i]["roundNum"] = i + 1
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            raise AttributeError(msg)

    def rescore_rounds(self) -> None:
        """Rescore the rounds based on round end reason.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute
                has no "gameRounds" key.
        """
        if self.json and self.json["gameRounds"]:
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
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
        if self.json and self.json["gameRounds"]:
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
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
                cleaned_rounds = []
                for game_round in self.json["gameRounds"] or []:
                    if len(game_round["frames"] or []) > 0:
                        cleaned_rounds.append(game_round)
                self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
                    if game_round["frames"] and len(game_round["frames"]) > 0:
                        game_frame = game_round["frames"][0]
                        if game_frame["ct"]["players"] is None:
                            if game_frame["t"]["players"] is None:
                                pass
                            elif len(game_frame["t"]["players"]) <= n_players:
                                cleaned_rounds.append(game_round)
                        elif len(game_frame["ct"]["players"]) <= n_players and (
                            (game_frame["t"]["players"] is None)
                            or (len(game_frame["t"]["players"]) <= n_players)
                        ):
                            cleaned_rounds.append(game_round)
                self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
                    for game_round in self.json["gameRounds"] or []:
                        if not game_round["isWarmup"]:
                            cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
            cleaned_rounds = []
            for game_round in self.json["gameRounds"] or []:
                if game_round["roundEndReason"] not in bad_endings:
                    cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            raise AttributeError(msg)

    def remove_knife_rounds(self) -> None:
        """Removes knife rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json and self.json["gameRounds"]:
            cleaned_rounds = []
            for game_round in self.json["gameRounds"]:
                if not game_round["isWarmup"]:
                    kill_actions = game_round["kills"]
                    if kill_actions is None:
                        continue
                    total_kills = len(kill_actions)
                    total_knife_kills = 0
                    if total_kills > 0:
                        # We know this is save because the len call gives 0
                        # and this if never gets enteres if game_round["kills"] is None
                        # but mypy does not know this
                        for k in kill_actions:
                            if k["weapon"] == "Knife":
                                total_knife_kills += 1
                    if (total_knife_kills != total_kills) | (total_knife_kills == 0):
                        cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            raise AttributeError(msg)

    def remove_excess_kill_rounds(self) -> None:
        """Removes rounds with more than 10 kills.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        n_total_players = 10
        if self.json:
            cleaned_rounds = []
            for game_round in self.json["gameRounds"] or []:
                if (
                    not game_round["isWarmup"]
                    and len(game_round["kills"] or []) <= n_total_players
                ):
                    cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            raise AttributeError(msg)

    def remove_time_rounds(self) -> None:
        """Remove rounds with odd round timings.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            for game_round in self.json["gameRounds"] or []:
                if (
                    (game_round["startTick"] <= game_round["endTick"])
                    and (game_round["startTick"] <= game_round["endOfficialTick"])
                    and (game_round["startTick"] <= game_round["freezeTimeEndTick"])
                ):
                    cleaned_rounds.append(game_round)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            msg = "JSON not found. Run .parse() or .read_json() if JSON already exists"
            raise AttributeError(msg)
