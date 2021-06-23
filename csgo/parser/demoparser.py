import json
import logging
import os
import re
import subprocess
import pandas as pd

from csgo.utils import check_go_version


class DemoParser:
    """This class can parse a CSGO demofile to various outputs, such as JSON or CSV. Accessible via csgo.parser import DemoParser

    Attributes:
        demofile (string) : A string denoting the path to the demo file, which ends in .dem
        log (boolean)     : A boolean denoting if a log will be written. If true, log is written to "csgo_parser.log"
        demo_id (string) : A unique demo name/game id. Default is inferred from demofile name
        parse_rate (int)  : One of 128, 64, 32, 16, 8, 4, 2, or 1. The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks. Default is 32.

    Raises:
        ValueError : Raises a ValueError if the Golang version is lower than 1.14
    """

    def __init__(
        self, demofile="", outpath=None, log=False, demo_id=None, parse_rate=None
    ):
        # Set up logger
        if log:
            logging.basicConfig(
                filename="csgo_demoparser.log",
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            self.logger = logging.getLogger("CSGODemoParser")
            self.logger.handlers = []
            fh = logging.FileHandler("csgo_demoparser.log")
            fh.setLevel(logging.INFO)
            self.logger.addHandler(fh)
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            self.logger = logging.getLogger("CSGODemoParser")

        # Check if Golang is >= 1.14
        acceptable_go = check_go_version()
        if not acceptable_go:
            self.logger.error("Go version too low! Needs 1.14.0")
            raise ValueError("Go version too low! Needs 1.14.0")
        else:
            self.logger.info("Go version>=1.14.0")

        # Check if demofile exists
        if not os.path.exists(os.path.abspath(demofile)):
            self.logger.error("Demofile path does not exist!")
            raise ValueError("Demofile path does not exist!")

        # Handle demofile and demo_id name. Finds right most '/' in case demofile is a specified path.
        self.demofile = os.path.abspath(demofile)
        self.logger.info("Initialized CSGODemoParser with demofile " + self.demofile)
        if demo_id is None:
            self.demo_id = demofile[demofile.rfind("/") + 1 : -4]
        else:
            self.demo_id = demo_id
        if outpath is None:
            self.outpath = os.path.abspath(os.getcwd())
        else:
            self.outpath = os.path.abspath(outpath)
        self.logger.info("Setting demo id to " + self.demo_id)

        # Handle parse rate. Must be a power of 2^0 to 2^7. If not, then default to 2^5.
        if parse_rate is None:
            self.logger.warning("No parse rate set")
            self.parse_rate = 32
        elif parse_rate == 1:
            self.logger.warning("A parse rate of 1 will parse EVERY tick. This process will be very slow.")
            self.parse_rate = 1
        elif parse_rate not in [1, 2, 4, 8, 16, 32, 64, 128]:
            self.logger.warning(
                "Parse rate of "
                + str(parse_rate)
                + " not acceptable! Parse rate must be a power of 2 between 2^0 and 2^7. Setting to DEFAULT value of 32."
            )
            self.parse_rate = 32
        else:
            self.parse_rate = parse_rate
        self.logger.info("Setting parse rate to " + str(self.parse_rate))

        # Set parse error to False
        self.parse_error = False

    def _parse_demo(self):
        """Parse a demofile using the Go script parse_demo.go -- this function takes no arguments, all arguments are set in initialization.

        Returns:
            Outputs a JSON file to current working directory.
        """
        path = os.path.join(os.path.dirname(__file__), "")
        self.logger.info("Running Golang parser from " + path)
        self.logger.info("Looking for file at " + self.demofile)
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_demo.go",
                "-demo",
                self.demofile,
                "-parserate",
                str(self.parse_rate),
                "-demoid",
                str(self.demo_id),
                "-out",
                self.outpath,
            ],
            stdout=subprocess.PIPE,
            cwd=path,
        )
        stdout = proc.stdout.read().splitlines()
        self.output_file = self.demo_id + ".json"
        if os.path.isfile(self.output_file):
            self.logger.info("Wrote demo parse output to " + self.output_file)
            self.parse_error = False
        else:
            self.parse_error = True
            self.logger.error("No file produced, error in calling Golang")
            self.logger.error(stdout)

    def _read_json(self):
        """Reads the JSON file created by _parse_demo()

        Returns:
            A dictionary of the JSON output of _parse_demo()
        """
        json_path = self.outpath + "/" + self.output_file
        self.logger.info("Reading in JSON from " + self.output_file)
        with open(json_path) as f:
            demo_data = json.load(f)
        self.json = demo_data
        self.logger.info(
            "JSON data loaded, available in the `json` attribute to parser"
        )
        return demo_data

    def parse(self, return_type="json"):
        """Wrapper for _parse_demo() and _read_json(). Provided for user convenience.

        Args:
            return_type (string) : Either "json" or "df"

        Returns:
            A dictionary of output
        """
        self._parse_demo()
        self._read_json()
        if self.json:
            self.logger.info("Successfully parsed JSON output")
            self.logger.info("Successfully returned JSON output")
            if return_type == "json":
                return self.json
            elif return_type == "df":
                demo_data = {}
                demo_data["MatchId"] = self.json["MatchId"]
                demo_data["ClientName"] = self.json["ClientName"]
                demo_data["MapName"] = self.json["MapName"]
                demo_data["TickRate"] = self.json["TickRate"]
                demo_data["PlaybackTicks"] = self.json["PlaybackTicks"]
                demo_data["Rounds"] = self._parse_rounds(return_type=return_type)
                demo_data["Kills"] = self._parse_kills(return_type=return_type)
                demo_data["Damages"] = self._parse_damages(return_type=return_type)
                demo_data["Grenades"] = self._parse_grenades(return_type=return_type)
                demo_data["Flashes"] = self._parse_flashes(return_type=return_type)
                demo_data["BombEvents"] = self._parse_bomb_events(
                    return_type=return_type
                )
                demo_data["Frames"] = self._parse_frames(return_type=return_type)
                demo_data["PlayerFrames"] = self._parse_player_frames(
                    return_type=return_type
                )
                self.logger.info("Returned dataframe output")
                return demo_data
            else:
                self.logger.error("Parse return_type must be either 'json' or 'df'")
                raise ValueError("return_type must be either 'json' or 'df'")
        else:
            self.logger.error("JSON couldn't be returned")
            raise AttributeError("No JSON parsed!")

    def _parse_frames(self, return_type):
        """Returns frames as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse frames return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")
        try:
            frames_dataframes = []
            keys = ["Tick", "Second", "PositionToken", "TToken", "CTToken"]
            for r in self.json["GameRounds"]:
                for frame in r["Frames"]:
                    frame_item = {}
                    frame_item["BombDistanceToA"] = frame["BombDistanceToA"]
                    frame_item["BombDistanceToB"] = frame["BombDistanceToB"]
                    frame_item["RoundNum"] = r["RoundNum"]
                    for k in keys:
                        frame_item[k] = frame[k]
                    for side in ["CT", "T"]:
                        if side == "CT":
                            frame_item["CTTeamName"] = frame["CT"]["TeamName"]
                            frame_item["CTEqVal"] = frame["CT"]["TeamEqVal"]
                            frame_item["CTAlivePlayers"] = frame["CT"]["AlivePlayers"]
                            frame_item["CTUtility"] = frame["CT"]["TotalUtility"]
                            frame_item["CTUtilityLevel"] = frame["CT"]["UtilityLevel"]
                            frame_item["CTToken"] = frame["CT"]["PositionToken"]
                        else:
                            frame_item["TTeamName"] = frame["T"]["TeamName"]
                            frame_item["TEqVal"] = frame["T"]["TeamEqVal"]
                            frame_item["TAlivePlayers"] = frame["T"]["AlivePlayers"]
                            frame_item["TUtility"] = frame["T"]["TotalUtility"]
                            frame_item["TUtilityLevel"] = frame["T"]["UtilityLevel"]
                            frame_item["TToken"] = frame["T"]["PositionToken"]
                    frames_dataframes.append(frame_item)
            frames_df = pd.DataFrame(frames_dataframes)
            frames_df["MatchId"] = self.demo_id
            frames_df["MapName"] = self.json["MapName"]
            if return_type == "list":
                self.logger.info("Parsed frames to list")
                return frames_dataframes
            elif return_type == "df":
                self.logger.info("Parsed frames to Pandas DataFrame")
                return pd.DataFrame(frames_dataframes)
        except AttributeError:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_player_frames(self, return_type):
        """Returns player frames as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error(
                "Parse player frames return_type must be either 'list' or 'df'"
            )
            raise ValueError("return_type must be either 'list' or 'df'")
        try:
            player_frames = []
            for r in self.json["GameRounds"]:
                for frame in r["Frames"]:
                    for side in ["CT", "T"]:
                        if frame[side]["Players"] is not None and (
                            len(frame[side]["Players"]) == 5
                        ):
                            for player in frame[side]["Players"]:
                                player_item = {}
                                player_item["RoundNum"] = r["RoundNum"]
                                player_item["Tick"] = frame["Tick"]
                                player_item["Second"] = frame["Second"]
                                player_item["Side"] = side
                                player_item["TeamName"] = frame[side]["TeamName"]
                                player_item["PlayerName"] = player["Name"]
                                player_item["PlayerSteamId"] = player["SteamId"]
                                player_item["X"] = player["X"]
                                player_item["Y"] = player["Y"]
                                player_item["Z"] = player["Z"]
                                player_item["ViewX"] = player["ViewX"]
                                player_item["ViewY"] = player["ViewY"]
                                player_item["AreaId"] = player["AreaId"]
                                player_item["Hp"] = player["Hp"]
                                player_item["Armor"] = player["Armor"]
                                player_item["IsAlive"] = player["IsAlive"]
                                player_item["IsFlashed"] = player["IsFlashed"]
                                player_item["IsAirborne"] = player["IsAirborne"]
                                player_item["IsDucking"] = player["IsDucking"]
                                player_item["IsScoped"] = player["IsScoped"]
                                player_item["IsWalking"] = player["IsWalking"]
                                player_item["EqValue"] = player["EquipmentValue"]
                                player_item["HasHelmet"] = player["HasHelmet"]
                                player_item["HasDefuse"] = player["HasDefuse"]
                                player_item["DistToBombsiteA"] = player[
                                    "DistToBombsiteA"
                                ]
                                player_item["DistToBombsiteB"] = player[
                                    "DistToBombsiteB"
                                ]
                                player_frames.append(player_item)
            player_frames_df = pd.DataFrame(player_frames)
            player_frames_df["MatchId"] = self.demo_id
            player_frames_df["MapName"] = self.json["MapName"]
            if return_type == "list":
                self.logger.info("Parsed player frames to list")
                return player_frames
            elif return_type == "df":
                self.logger.info("Parsed player frames to Pandas DataFrame")
                return pd.DataFrame(player_frames_df)
        except AttributeError:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_rounds(self, return_type):
        """Returns rounds as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse rounds return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")

        try:
            rounds = []
            keys = [
                "RoundNum",
                "StartTick",
                "FreezeTimeEnd",
                "EndTick",
                "EndOfficialTick",
                "TScore",
                "CTScore",
                "WinningSide",
                "WinningTeam",
                "LosingTeam",
                "RoundEndReason",
                "CTStartEqVal",
                "CTBuyType",
                "TStartEqVal",
                "TBuyType",
            ]
            for r in self.json["GameRounds"]:
                round_item = {}
                for k in keys:
                    round_item[k] = r[k]
                    round_item["MatchId"] = self.demo_id
                    round_item["MapName"] = self.json["MapName"]
                rounds.append(round_item)
            if return_type == "list":
                self.logger.info("Parsed rounds to list")
                return rounds
            elif return_type == "df":
                self.logger.info("Parsed rounds to Pandas DataFrame")
                return pd.DataFrame(rounds)
        except AttributeError:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_kills(self, return_type):
        """Returns kills as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse kills return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")

        try:
            kills = []
            for r in self.json["GameRounds"]:
                if r["Kills"] is not None:
                    for k in r["Kills"]:
                        new_k = k
                        new_k["RoundNum"] = r["RoundNum"]
                        new_k["MatchId"] = self.demo_id
                        new_k["MapName"] = self.json["MapName"]
                        kills.append(new_k)
            if return_type == "list":
                self.logger.info("Parsed kills to list")
                return kills
            elif return_type == "df":
                self.logger.info("Parsed kills to Pandas DataFrame")
                return pd.DataFrame(kills)
        except AttributeError:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_damages(self, return_type):
        """Returns damages as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse damages return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")

        if self.json:
            damages = []
            for r in self.json["GameRounds"]:
                if r["Damages"] is not None:
                    for d in r["Damages"]:
                        new_d = d
                        new_d["RoundNum"] = r["RoundNum"]
                        new_d["MatchId"] = self.demo_id
                        new_d["MapName"] = self.json["MapName"]
                        damages.append(new_d)
            if return_type == "list":
                self.logger.info("Parsed damages to list")
                return damages
            elif return_type == "df":
                self.logger.info("Parsed damages to Pandas DataFrame")
                return pd.DataFrame(damages)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_grenades(self, return_type):
        """Returns grenades as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error(
                "Parse grenades return_type must be either 'list' or 'df'"
            )
            raise ValueError("return_type must be either 'list' or 'df'")

        if self.json:
            grenades = []
            for r in self.json["GameRounds"]:
                if r["Grenades"] is not None:
                    for g in r["Grenades"]:
                        new_g = g
                        new_g["RoundNum"] = r["RoundNum"]
                        new_g["MatchId"] = self.demo_id
                        new_g["MapName"] = self.json["MapName"]
                        grenades.append(new_g)
            if return_type == "list":
                self.logger.info("Parsed grenades to list")
                return grenades
            elif return_type == "df":
                self.logger.info("Parsed grenades to Pandas DataFrame")
                return pd.DataFrame(grenades)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_bomb_events(self, return_type):
        """Returns bomb events as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error(
                "Parse bomb events return_type must be either 'list' or 'df'"
            )
            raise ValueError("return_type must be either 'list' or 'df'")

        if self.json:
            bomb_events = []
            for r in self.json["GameRounds"]:
                if r["BombEvents"] is not None:
                    for b in r["BombEvents"]:
                        new_b = b
                        new_b["RoundNum"] = r["RoundNum"]
                        new_b["MatchId"] = self.demo_id
                        new_b["MapName"] = self.json["MapName"]
                        bomb_events.append(new_b)
            if return_type == "list":
                self.logger.info("Parsed bomb_events to list")
                return bomb_events
            elif return_type == "df":
                self.logger.info("Parsed bomb_events to Pandas DataFrame")
                return pd.DataFrame(bomb_events)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_flashes(self, return_type):
        """Returns flashes as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse flashes return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")

        if self.json:
            flashes = []
            for r in self.json["GameRounds"]:
                if r["Flashes"] is not None:
                    for f in r["Flashes"]:
                        new_f = f
                        new_f["RoundNum"] = r["RoundNum"]
                        new_f["MatchId"] = self.demo_id
                        new_f["MapName"] = self.json["MapName"]
                        flashes.append(new_f)
            if return_type == "list":
                self.logger.info("Parsed flashes to list")
                return flashes
            elif return_type == "df":
                self.logger.info("Parsed flashes to Pandas DataFrame")
                return pd.DataFrame(flashes)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")
