"""This module defines the DemoParser class that handles the core functionality of parsing and cleaning a csgo demo file

    Typical usage example:
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
from typing import Optional, Union, Any, Literal, cast, get_args
import logging
import os
import subprocess
import pandas as pd

from awpy.utils import check_go_version
from awpy.types import Game


class DemoParser:
    """DemoParser can parse, load and clean data from a CSGO demofile. Can be instantiated without a specified demofile.

    Attributes:
        demofile (string): A string denoting the path to the demo file, which ends in .dem
            Defaults to ''
        outpath (string): Path where to save the outputfile to. Default is current directory
        demo_id (string): A unique demo name/game id. Default is inferred from demofile name
        output_file (str): The output file name. Default is 'demoid'+".json"
        log (bool): A boolean indicating if the log should print to stdout. Default is False
        parse_rate (int, optional): One of 128, 64, 32, 16, 8, 4, 2, or 1.
            The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks. Default is 128.
        parse_frames (bool): Flag if you want to parse frames (trajectory data) or not. Default is True
        parse_kill_frames (bool): Flag if you want to parse frames on kills. Default is False
        trade_time (int, optional): Length of the window for a trade (in seconds). Default is 5.
        dmg_rolled (bool): Boolean if you want damages rolled up
            (since multiple damages for a player can happen in 1 tick from the same weapon.)
            Default is False
        parse_chat (bool): Flag if you want to parse chat messages. Default is False
        buy_style (string): Buy style string, one of "hltv" or "csgo"
            Default is "hltv"
        json_indentation (bool): Whether the json file should be pretty printed
            with indentation (larger, more readable) or not (smaller, less human readable)
            Default is False
        json (dict): Dictionary containing the parsed json file

    Raises:
        ValueError: Raises a ValueError if the Golang version is lower than 1.17
    """

    def __init__(
        self,
        demofile: str = "",
        outpath: Optional[str] = None,
        demo_id: Optional[str] = None,
        log: bool = False,
        parse_rate: int = 128,
        parse_frames: bool = True,
        parse_kill_frames: bool = False,
        trade_time: int = 5,
        dmg_rolled: bool = False,
        parse_chat: bool = False,
        buy_style: str = "hltv",
        json_indentation: bool = False,
    ):
        # Set up logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("awpy")
        self.logger.propagate = log

        # Handle demofile and demo_id name. Only take the file name and remove the last extension.
        self.demofile = os.path.abspath(demofile)

        self.logger.info("Initialized awpy DemoParser with demofile %s", self.demofile)
        if not demo_id:  # (demo_id is None) | (demo_id == "")
            self.demo_id = os.path.splitext(
                os.path.basename(demofile.replace("\\", "/"))
            )[0]
        else:
            self.demo_id = demo_id

        self.logger.info("Setting demo id to %s", self.demo_id)

        self.output_file = self.demo_id + ".json"

        if outpath is None:
            self.outpath = os.path.abspath(os.getcwd())
        else:
            self.outpath = os.path.abspath(outpath)

        # Handle parse rate. If the parse rate is less than 64, likely to be slow
        if parse_rate < 1 or not isinstance(parse_rate, int):
            self.logger.warning(
                "Parse rate of %s not acceptable! Parse rate must be an integer greater than 0.",
                str(parse_rate),
            )
            parse_rate = 128
            self.parse_rate = parse_rate

        if parse_rate < 64 and parse_rate > 1:
            self.logger.warning(
                "A parse rate lower than 64 may be slow depending on the tickrate of the demo, which is usually 64 for MM and 128 for pro demos."
            )
            self.parse_rate = parse_rate
        elif parse_rate >= 256:
            self.logger.warning(
                "A high parse rate means very few frames. Only use for testing purposes."
            )
            self.parse_rate = parse_rate
        else:
            self.parse_rate = parse_rate
        self.logger.info("Setting parse rate to %s", str(self.parse_rate))

        # Handle trade time
        self.trade_time = trade_time
        if trade_time <= 0:
            self.logger.warning(
                "Trade time can't be negative, setting to default value of 5 seconds."
            )
            self.trade_time = 5
        elif trade_time > 7:
            self.logger.warning(
                "Trade time of %s is rather long. Consider a value between 4-7.",
                str(trade_time),
            )

        self.logger.info("Setting trade time to %s", str(self.trade_time))

        # Handle buy style
        if buy_style not in ["hltv", "csgo"]:
            self.logger.warning(
                "Buy style specified is not one of hltv, csgo, will be set to hltv by default"
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
        self.logger.info("Rollup damages set to %s", str(self.dmg_rolled))
        self.logger.info("Parse chat set to %s", str(self.parse_chat))
        self.logger.info("Parse frames set to %s", str(self.parse_frames))
        self.logger.info("Parse kill frames set to %s", str(self.parse_kill_frames))
        self.logger.info(
            "Output json indentation set to %s", str(self.json_indentation)
        )

        # Set parse error to False
        self.parse_error = False

        # Initialize json attribute as None
        self.json: Optional[Game] = None

    def parse_demo(self) -> None:
        """Parse a demofile using the Go script parse_demo.go -- this function needs the .demofile to be set in the class, and the file needs to exist.

        Returns:
            Outputs a JSON file to current working directory.

        Raises:
            ValueError: Raises a ValueError if the Golang version is lower than 1.17
            FileNotFoundError: Raises a FileNotFoundError if the demofile path does not exist.
        """
        # Check if Golang version is compatible
        acceptable_go = check_go_version()
        if not acceptable_go:
            error_message = "Error calling Go. Check if Go is installed using 'go version'. Need at least v1.17.0."
            self.logger.error(
                error_message
            )
            raise ValueError(
               error_message
            )
        else:
            self.logger.info("Go version>=1.17.0")

        # Check if demofile exists
        if not os.path.exists(os.path.abspath(self.demofile)):
            self.logger.error("Demofile path does not exist!")
            raise FileNotFoundError("Demofile path does not exist!")

        path = os.path.join(os.path.dirname(__file__), "")
        self.logger.info("Running Golang parser from %s", path)
        self.logger.info("Looking for file at %s", self.demofile)
        self.parser_cmd = [
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
            self.parser_cmd.append("--dmgrolled")
        if self.parse_frames:
            self.parser_cmd.append("--parseframes")
        if self.parse_kill_frames:
            self.parser_cmd.append("--parsekillframes")
        if self.json_indentation:
            self.parser_cmd.append("--jsonindentation")
        if self.parse_chat:
            self.parser_cmd.append("--parsechat")
        proc = subprocess.Popen(
            self.parser_cmd,
            stdout=subprocess.PIPE,
            cwd=path,
        )
        stdout = proc.stdout.read().splitlines() if proc.stdout is not None else None
        self.output_file = self.demo_id + ".json"
        if os.path.isfile(self.outpath + "/" + self.output_file):
            self.logger.info("Wrote demo parse output to %s", self.output_file)
            self.parse_error = False
        else:
            self.parse_error = True
            self.logger.error("No file produced, error in calling Golang")
            self.logger.error(stdout)

    def read_json(self, json_path: str):
        """Reads the JSON file given a JSON path. Can be used to read in already processed demofiles.

        Args:
            json_path (string): Path to JSON file

        Returns:
            JSON in Python dictionary form

        Raises:
            FileNotFoundError: Raises a FileNotFoundError if the JSON path doesn't exist
        """
        # Check if JSON exists
        if not os.path.exists(json_path):
            self.logger.error("JSON path does not exist!")
            raise FileNotFoundError("JSON path does not exist!")

        # Read in json to .json attribute
        with open(json_path, encoding="utf8") as f:
            demo_data: Game = json.load(f)

        self.json = demo_data
        self.logger.info(
            "JSON data loaded, available in the `json` attribute to parser"
        )
        return demo_data

    def parse(
        self, return_type: str = "json", clean: bool = True
    ) -> Union[Game, dict[str, Any]]:
        """Wrapper for parse_demo() and read_json(). Use to parse a demo.

        Args:
            return_type (string, optional): Either "json" or "df". Default is "json"
            clean (bool, optional): True to run clean_rounds, otherwise, uncleaned data is returned. Defaults to True.

        Returns:
            A dictionary of output (which is parsed to a JSON file in the working directory)

        Raises:
            ValueError: Raises a ValueError if the return_type is not "json" or "df"
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        self.parse_demo()
        self.read_json(json_path=self.outpath + "/" + self.output_file)
        if clean:
            clean_data = self.clean_rounds()
        if self.json:
            self.logger.info("JSON output found")
            if return_type == "json":
                return self.json
            elif return_type == "df":
                demo_data = self.parse_json_to_df()
                self.logger.info("Returned dataframe output")
                return demo_data
            else:
                self.logger.error("Parse return_type must be either 'json' or 'df'")
                raise ValueError("return_type must be either 'json' or 'df'")
        else:
            self.logger.error("JSON couldn't be returned")
            raise AttributeError("No JSON parsed! Error in producing JSON.")

    def parse_json_to_df(self) -> dict[str, Any]:
        """Returns JSON into dictionary where keys correspond to data frames

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
            demo_data["kills"] = self._parse_kills()
            demo_data["kills"]["attackerSteamID"] = demo_data["kills"][
                "attackerSteamID"
            ].astype(pd.Int64Dtype())
            demo_data["kills"]["victimSteamID"] = demo_data["kills"][
                "victimSteamID"
            ].astype(pd.Int64Dtype())
            demo_data["kills"]["assisterSteamID"] = demo_data["kills"][
                "assisterSteamID"
            ].astype(pd.Int64Dtype())
            demo_data["kills"]["flashThrowerSteamID"] = demo_data["kills"][
                "flashThrowerSteamID"
            ].astype(pd.Int64Dtype())
            # Damages
            demo_data["damages"] = self._parse_damages()
            demo_data["damages"]["attackerSteamID"] = demo_data["damages"][
                "attackerSteamID"
            ].astype(pd.Int64Dtype())
            demo_data["damages"]["victimSteamID"] = demo_data["damages"][
                "victimSteamID"
            ].astype(pd.Int64Dtype())
            # Grenades
            demo_data["grenades"] = self._parse_grenades()
            demo_data["grenades"]["throwerSteamID"] = demo_data["grenades"][
                "throwerSteamID"
            ].astype(pd.Int64Dtype())
            # Flashes
            demo_data["flashes"] = self._parse_flashes()
            demo_data["flashes"]["attackerSteamID"] = demo_data["flashes"][
                "attackerSteamID"
            ].astype(pd.Int64Dtype())
            demo_data["flashes"]["playerSteamID"] = demo_data["flashes"][
                "playerSteamID"
            ].astype(pd.Int64Dtype())
            # Weapon Fires
            demo_data["weaponFires"] = self._parse_weapon_fires()
            demo_data["weaponFires"]["playerSteamID"] = demo_data["weaponFires"][
                "playerSteamID"
            ].astype(pd.Int64Dtype())
            # Bomb Events
            demo_data["bombEvents"] = self._parse_bomb_events()
            demo_data["bombEvents"]["playerSteamID"] = demo_data["bombEvents"][
                "playerSteamID"
            ].astype(pd.Int64Dtype())
            # Frames
            demo_data["frames"] = self._parse_frames()
            # Player Frames
            demo_data["playerFrames"] = self._parse_player_frames()
            demo_data["playerFrames"]["steamID"] = demo_data["playerFrames"][
                "steamID"
            ].astype(pd.Int64Dtype())
            self.logger.info("Returned dataframe output")
            return demo_data
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_frames(self) -> pd.DataFrame:
        """Returns frames as a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a frame (game state) in the demo, which is a discrete point of time.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            frames_dataframes = []
            for r in self.json["gameRounds"] or []:
                for frame in r["frames"] or []:
                    frame_item: dict[str, Any] = {}
                    frame_item["roundNum"] = r["roundNum"]
                    for k in ("tick", "seconds"):
                        # Currently there is no better way:
                        # https://github.com/python/mypy/issues/9230
                        k = cast(Literal["tick", "seconds"], k)
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
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_player_frames(self) -> pd.DataFrame:
        """Returns player frames as a Pandas dataframe.

        Returns:
            A Pandas dataframe where each row is a player's attributes at a given frame (game state).

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            player_frames = []
            for r in self.json["gameRounds"] or []:
                for frame in r["frames"] or []:
                    for side in ["ct", "t"]:
                        # Currently there is no better way:
                        # https://github.com/python/mypy/issues/9230
                        side = cast(Literal["ct", "t"], side)
                        if frame[side]["players"] is not None and (
                            # The or [] should be unneccesary but mypy can not handle this
                            len(frame[side]["players"] or [])
                            > 0  # Used to be == 5, to ensure the sides were equal.
                        ):
                            # Same here
                            for player in frame[side]["players"] or []:
                                player_item: dict[str, Any] = {}
                                player_item["roundNum"] = r["roundNum"]
                                player_item["tick"] = frame["tick"]
                                player_item["seconds"] = frame["seconds"]
                                player_item["side"] = side
                                player_item["teamName"] = frame[side]["teamName"]
                                for col, val in player.items():
                                    if col != "inventory":
                                        player_item[col] = val
                                player_frames.append(player_item)
            player_frames_df = pd.DataFrame(player_frames)
            player_frames_df["matchID"] = self.json["matchID"]
            player_frames_df["mapName"] = self.json["mapName"]
            return pd.DataFrame(player_frames_df)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_rounds(self) -> pd.DataFrame:
        """Returns rounds as a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a round

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            rounds = []
            # There is currently no better way than this monstrosity...
            # https://github.com/python/mypy/issues/9230
            # https://stackoverflow.com/a/64522240/7895542
            cols_type = Literal[
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
            ]
            cols: list[cols_type] = list(get_args(cols_type))
            for r in self.json["gameRounds"] or []:
                round_item: dict[str, Any] = {}
                for k in cols:
                    round_item[k] = r[k]
                    round_item["matchID"] = self.json["matchID"]
                    round_item["mapName"] = self.json["mapName"]
                rounds.append(round_item)
            return pd.DataFrame(rounds)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_kills(self) -> pd.DataFrame:
        """Returns kills as either a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a kill

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            kills = []
            for r in self.json["gameRounds"] or []:
                if r["kills"] is not None:
                    for k in r["kills"]:
                        new_k: dict[str, Any] = dict(k)
                        new_k["roundNum"] = r["roundNum"]
                        new_k["matchID"] = self.json["matchID"]
                        new_k["mapName"] = self.json["mapName"]
                        kills.append(new_k)
            return pd.DataFrame(kills)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_weapon_fires(self) -> pd.DataFrame:
        """Returns weapon fires as either a list or Pandas dataframe

        Returns:
            A  Pandas dataframe where each row is a weapon fire event

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            shots = []
            for r in self.json["gameRounds"] or []:
                if r["weaponFires"] is not None:
                    for wf in r["weaponFires"]:
                        new_wf: dict[str, Any] = dict(wf)
                        new_wf["roundNum"] = r["roundNum"]
                        new_wf["matchID"] = self.json["matchID"]
                        new_wf["mapName"] = self.json["mapName"]
                        shots.append(new_wf)
            return pd.DataFrame(shots)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_damages(self) -> pd.DataFrame:
        """Returns damages as a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a damage event.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            damages = []
            for r in self.json["gameRounds"] or []:
                if r["damages"] is not None:
                    for d in r["damages"]:
                        new_d: dict[str, Any] = dict(d)
                        new_d["roundNum"] = r["roundNum"]
                        new_d["matchID"] = self.json["matchID"]
                        new_d["mapName"] = self.json["mapName"]
                        damages.append(new_d)
            return pd.DataFrame(damages)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_grenades(self) -> pd.DataFrame:
        """Returns grenades as a Pandas dataframe

        Returns:
            A list or Pandas dataframe where each row is a grenade throw

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            grenades = []
            for r in self.json["gameRounds"] or []:
                if r["grenades"] is not None:
                    for g in r["grenades"]:
                        new_g: dict[str, Any] = dict(g)
                        new_g["roundNum"] = r["roundNum"]
                        new_g["matchID"] = self.json["matchID"]
                        new_g["mapName"] = self.json["mapName"]
                        grenades.append(new_g)
            return pd.DataFrame(grenades)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_bomb_events(self) -> pd.DataFrame:
        """Returns bomb events as a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a bomb event (defuse, plant, etc.)

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            bomb_events = []
            for r in self.json["gameRounds"] or []:
                if r["bombEvents"] is not None:
                    for b in r["bombEvents"]:
                        new_b: dict[str, Any] = dict(b)
                        new_b["roundNum"] = r["roundNum"]
                        new_b["matchID"] = self.json["matchID"]
                        new_b["mapName"] = self.json["mapName"]
                        bomb_events.append(new_b)
            return pd.DataFrame(bomb_events)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def _parse_flashes(self) -> pd.DataFrame:
        """Returns flashes as a Pandas dataframe

        Returns:
            A Pandas dataframe where each row is a flash event.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            flashes = []
            for r in self.json["gameRounds"] or []:
                if r["flashes"] is not None:
                    for f in r["flashes"]:
                        new_f: dict[str, Any] = dict(f)
                        new_f["roundNum"] = r["roundNum"]
                        new_f["matchId"] = self.json["matchID"]
                        new_f["mapName"] = self.json["mapName"]
                        flashes.append(new_f)
            return pd.DataFrame(flashes)
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def clean_rounds(
        self,
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
    ) -> Union[Game, dict[str, Any]]:
        """Cleans a parsed demofile JSON.

        Args:
            remove_no_frames (bool, optional): Remove rounds where there are no frames. Default to True.
            remove_warmups (bool, optional): Remove warmup rounds. Defaults to True.
            remove_knifes (bool, optional): Remove knife rounds. Defaults to True.
            remove_bad_timings (bool, optional): Remove bad timings. Defaults to True.
            remove_excess_players (bool, optional): Remove rounds with more than 5 players. Defaults to True.
            remove_excess_kills (bool, optional): Remove rounds with more than 10 kills. Defaults to True.
            remove_bad_endings (bool, optional): Remove rounds with bad round end reasons. Defaults to True.
            remove_bad_scoring (bool, optional): Remove rounds where the scoring is off (like scores going below the previous round's). Defaults to False.
            return_type (str, optional): Return JSON or DataFrame. Defaults to "json".
            save_to_json (bool, optional): Whether to write the JSON to a file. Defaults to True.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
            ValueError: Raises a ValueError if the return type is neither 'json' nor 'df'

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
            elif return_type == "df":
                demo_data = self.parse_json_to_df()
                self.logger.info("Returned cleaned dataframe output")
                return demo_data
            raise ValueError(
                f"Invalid return_type of {return_type}. Use 'json' or 'df' instead!"
            )
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def write_json(self) -> None:
        """Rewrite the JSON file"""
        with open(self.outpath + "/" + self.output_file, "w", encoding="utf8") as fp:
            json.dump(self.json, fp, indent=(1 if self.json_indentation else None))

    def renumber_rounds(self) -> None:
        """Renumbers the rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute has a "gameRounds" key.
        """
        if self.json and self.json["gameRounds"]:
            for i, r in enumerate(self.json["gameRounds"]):
                self.json["gameRounds"][i]["roundNum"] = i + 1
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def rescore_rounds(self) -> None:
        """Rescore the rounds based on round end reason.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute has a "gameRounds" key.
        """
        if self.json and self.json["gameRounds"]:
            for i, r in enumerate(self.json["gameRounds"]):
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
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
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
            cleaned_rounds = []
            for i, r in enumerate(self.json["gameRounds"] or []):
                current_round_total = (
                    r["tScore"] + r["endTScore"] + r["ctScore"] + r["endCTScore"]
                )
                if i < len(self.json["gameRounds"]) - 1:  # type: ignore[arg-type]
                    # Non-OT rounds
                    lookahead_round = self.json["gameRounds"][i + 1]  # type: ignore[index]
                    lookahead_round_total = (
                        lookahead_round["tScore"]
                        + lookahead_round["endTScore"]
                        + lookahead_round["ctScore"]
                        + lookahead_round["endCTScore"]
                    )
                    if lookahead_round_total > current_round_total:
                        cleaned_rounds.append(r)
                    elif (r["endTScore"] == 16) & (r["endCTScore"] <= 14):
                        cleaned_rounds.append(r)
                    elif (r["endCTScore"] == 16) & (r["endTScore"] <= 14):
                        cleaned_rounds.append(r)
                    else:
                        # OT win scores are of the type:
                        # 15 + (4xN) with N a natural numbers (1, 2, 3, ...)
                        # So 19, 23, 27, ...
                        # So if you substract 15 from an OT winning round the number is divisible by 4
                        # OT_Scores = [19, 23, 27, 31, 35, 39, 43, 47]
                        if (
                            (r["endCTScore"] - 15) % 4 == 0
                            and r["endTScore"] < r["endCTScore"]
                        ) or (
                            (r["endTScore"] - 15) % 4 == 0
                            and r["endCTScore"] < r["endTScore"]
                        ):
                            cleaned_rounds.append(r)
                        # for s in OT_Scores:
                        #     if (r["endCTScore"] == s) & (r["endTScore"] < s - 1):
                        #         cleaned_rounds.append(r)
                        #     elif (r["endTScore"] == s) & (r["endCTScore"] < s - 1):
                        #         cleaned_rounds.append(r)
                else:
                    lookback_round = self.json["gameRounds"][i - 1]  # type: ignore[index]
                    lookback_round_total = (
                        lookback_round["tScore"]
                        + lookback_round["endTScore"]
                        + lookback_round["ctScore"]
                        + lookback_round["endCTScore"]
                    )
                    if current_round_total > lookback_round_total:
                        cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_rounds_with_no_frames(self) -> None:
        """Removes rounds with no frames

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if not self.parse_frames:
                self.logger.warning(
                    "parse_frames is set to False, must be true for remove_no_frames to work. Skipping remove_no_frames."
                )
            else:
                cleaned_rounds = []
                for r in self.json["gameRounds"] or []:
                    if len(r["frames"] or []) > 0:
                        cleaned_rounds.append(r)
                self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_excess_players(self) -> None:
        """Removes rounds where there are more than 5 players on a side.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            if not self.parse_frames:
                self.logger.warning(
                    "parse_frames is set to False, must be true for remove_excess_players to work. Skipping remove_excess_players."
                )
            else:
                cleaned_rounds = []
                # Remove rounds where the number of players is too large
                for r in self.json["gameRounds"] or []:
                    if len(r["frames"] or []) > 0:
                        f = r["frames"][0]  # type: ignore[index]
                        if f["ct"]["players"] is None:
                            if f["t"]["players"] is None:
                                pass
                            elif len(f["t"]["players"]) <= 5:
                                cleaned_rounds.append(r)
                        elif len(f["ct"]["players"]) <= 5:
                            if (f["t"]["players"] is None) or (
                                len(f["t"]["players"]) <= 5
                            ):
                                cleaned_rounds.append(r)
                self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_warmups(self) -> None:
        """Removes warmup rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            # Remove warmups where the demo may have started recording in the middle of a warmup round
            if "warmupChanged" in self.json["matchPhases"]:
                if len(self.json["matchPhases"]["warmupChanged"] or []) > 1:
                    last_warmup_changed = self.json["matchPhases"]["warmupChanged"][1]  # type: ignore[index]
                    for r in self.json["gameRounds"] or []:
                        if (r["startTick"] > last_warmup_changed) and (
                            not r["isWarmup"]
                        ):
                            cleaned_rounds.append(r)
                        if r["startTick"] == last_warmup_changed:
                            cleaned_rounds.append(r)
                else:
                    for r in self.json["gameRounds"] or []:
                        if not r["isWarmup"]:
                            cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_end_round(self, bad_endings: Optional[list[str]] = None) -> None:
        """Removes rounds with bad end reason.

        Args:
            bad_endings (list, optional): List of bad round end reasons. Defaults to ["Draw", "Unknown", ""].

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if bad_endings is None:
            bad_endings = ["Draw", "Unknown", ""]
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"] or []:
                if r["roundEndReason"] not in bad_endings:
                    cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_knife_rounds(self) -> None:
        """Removes knife rounds.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"] or []:
                if not r["isWarmup"]:
                    total_kills = len(r["kills"] or [])
                    total_knife_kills = 0
                    if total_kills > 0:
                        # We know this is save because the len call gives 0
                        # and this if never gets enteres if r["kills"] is None
                        # but mypy does not know this
                        for k in r["kills"]:  # type: ignore[union-attr]
                            if k["weapon"] == "Knife":
                                total_knife_kills += 1
                    if (total_knife_kills != total_kills) | (total_knife_kills == 0):
                        cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_excess_kill_rounds(self) -> None:
        """Removes rounds with more than 10 kills.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"] or []:
                if not r["isWarmup"]:
                    if len(r["kills"] or []) <= 10:
                        cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )

    def remove_time_rounds(self) -> None:
        """Remove rounds with odd round timings.

        Raises:
            AttributeError: Raises an AttributeError if the .json attribute is None
        """
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"] or []:
                if (
                    (r["startTick"] <= r["endTick"])
                    and (r["startTick"] <= r["endOfficialTick"])
                    and (r["startTick"] <= r["freezeTimeEndTick"])
                ):
                    cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
            raise AttributeError(
                "JSON not found. Run .parse() or .read_json() if JSON already exists"
            )
