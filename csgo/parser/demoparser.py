import json
import logging
import os
import subprocess
import pandas as pd

from csgo.utils import check_go_version


class DemoParser:
    """This class can parse a CSGO demofile to various outputs, such as JSON or CSV. Accessible via csgo.parser import DemoParser

    Attributes:
        demofile (string)   : A string denoting the path to the demo file, which ends in .dem
        log (boolean)       : A boolean denoting if a log will be written. If true, log is written to "csgo_parser.log"
        demo_id (string)    : A unique demo name/game id. Default is inferred from demofile name
        parse_rate (int)    : One of 128, 64, 32, 16, 8, 4, 2, or 1. The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks. Default is 128.
        parse_frames (bool) : Flag if you want to parse frames (trajectory data) or not
        trade_time (int)    : Length of the window for a trade (in seconds). Default is 5.
        dmg_rolled (bool)   : Boolean if you want damages rolled up (since multiple damages for a player can happen in 1 tick from the same weapon.)
        buy_style (string)  : Buy style string, one of "hltv" or "csgo"

    Raises:
        ValueError : Raises a ValueError if the Golang version is lower than 1.14
    """

    def __init__(
        self,
        demofile="",
        outpath=None,
        log=False,
        demo_id=None,
        parse_rate=128,
        parse_frames=True,
        trade_time=5,
        dmg_rolled=False,
        buy_style="hltv",
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
        if (demo_id is None) | (demo_id == ""):
            self.demo_id = demofile[demofile.rfind("/") + 1 : -4]
        else:
            self.demo_id = demo_id
        if outpath is None:
            self.outpath = os.path.abspath(os.getcwd())
        else:
            self.outpath = os.path.abspath(outpath)
        self.logger.info("Setting demo id to " + self.demo_id)

        # Handle parse rate. If the parse rate is less than 64, likely to be slow
        if parse_rate < 1 or type(parse_rate) is not int:
            self.logger.warning(
                "Parse rate of "
                + str(parse_rate)
                + " not acceptable! Parse rate must be an integer greater than 0."
            )
            parse_rate = 128
            self.parse_rate = parse_rate

        if parse_rate == 1:
            self.logger.warning(
                "A parse rate of 1 will parse EVERY tick. This process will be very slow."
            )
            self.parse_rate = 1
        elif parse_rate < 64 and parse_rate > 1:
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
        self.logger.info("Setting parse rate to " + str(self.parse_rate))

        # Handle trade time
        if trade_time <= 0:
            self.logger.warning(
                "Trade time can't be negative, setting to default value of 5 seconds."
            )
            self.trade_time = 5
        elif trade_time > 7:
            self.logger.warning(
                "Trade time of "
                + str(trade_time)
                + " is rather long. Consider a value between 4-7."
            )
        else:
            self.trade_time = trade_time
        self.logger.info("Setting trade time to " + str(self.trade_time))

        # Handle buy style
        if buy_style not in ["hltv", "csgo"]:
            self.logger.warning(
                "Buy style not one of hltv, csgo, will be set to hltv by default"
            )
            self.buy_style = "hltv"
        else:
            self.buy_style = buy_style
        self.logger.info("Setting buy style to " + str(self.buy_style))

        self.dmg_rolled = dmg_rolled
        self.parse_frames = parse_frames
        self.logger.info("Rollup damages set to " + str(self.dmg_rolled))
        self.logger.info("Parse frames set to " + str(self.parse_frames))

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
        proc = subprocess.Popen(
            self.parser_cmd,
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
                demo_data["matchID"] = self.json["matchID"]
                demo_data["clientName"] = self.json["clientName"]
                demo_data["mapName"] = self.json["mapName"]
                demo_data["tickRate"] = self.json["tickRate"]
                demo_data["playbackTicks"] = self.json["playbackTicks"]
                demo_data["rounds"] = self._parse_rounds(return_type=return_type)
                demo_data["kills"] = self._parse_kills(return_type=return_type)
                demo_data["damages"] = self._parse_damages(return_type=return_type)
                demo_data["grenades"] = self._parse_grenades(return_type=return_type)
                demo_data["flashes"] = self._parse_flashes(return_type=return_type)
                demo_data["weaponFires"] = self._parse_weapon_fires(
                    return_type=return_type
                )
                demo_data["bombEvents"] = self._parse_bomb_events(
                    return_type=return_type
                )
                demo_data["frames"] = self._parse_frames(return_type=return_type)
                demo_data["playerFrames"] = self._parse_player_frames(
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
            keys = ["tick", "seconds", "positionToken", "tToken", "ctToken"]
            for r in self.json["gameRounds"]:
                if r["frames"]:
                    for frame in r["frames"]:
                        frame_item = {}
                        frame_item["roundNum"] = r["roundNum"]
                        for k in keys:
                            frame_item[k] = frame[k]
                        for side in ["ct", "t"]:
                            if side == "ct":
                                frame_item["ctTeamName"] = frame["ct"]["teamName"]
                                frame_item["ctEqVal"] = frame["ct"]["teamEqVal"]
                                frame_item["ctAlivePlayers"] = frame["ct"][
                                    "alivePlayers"
                                ]
                                frame_item["ctUtility"] = frame["ct"]["totalUtility"]
                                frame_item["ctToken"] = frame["ct"]["positionToken"]
                            else:
                                frame_item["tTeamName"] = frame["t"]["teamName"]
                                frame_item["tEqVal"] = frame["t"]["teamEqVal"]
                                frame_item["tAlivePlayers"] = frame["t"]["alivePlayers"]
                                frame_item["tUtility"] = frame["t"]["totalUtility"]
                                frame_item["tToken"] = frame["t"]["positionToken"]
                    frames_dataframes.append(frame_item)
            frames_df = pd.DataFrame(frames_dataframes)
            frames_df["matchID"] = self.json["matchID"]
            frames_df["mapName"] = self.json["mapName"]
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
            for r in self.json["gameRounds"]:
                if r["frames"]:
                    for frame in r["frames"]:
                        for side in ["ct", "t"]:
                            if frame[side]["players"] is not None and (
                                len(frame[side]["players"])
                                > 0  # Used to be == 5, to ensure the sides were equal.
                            ):
                                for player in frame[side]["players"]:
                                    player_item = {}
                                    player_item["roundNum"] = r["roundNum"]
                                    player_item["tick"] = frame["tick"]
                                    player_item["seconds"] = frame["seconds"]
                                    player_item["side"] = side
                                    player_item["teamName"] = frame[side]["teamName"]
                                    for col in player.keys():
                                        if col != "inventory":
                                            player_item[col] = player[col]
                                    player_frames.append(player_item)
            player_frames_df = pd.DataFrame(player_frames)
            player_frames_df["matchID"] = self.json["matchID"]
            player_frames_df["mapName"] = self.json["mapName"]
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
            cols = [
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
                "tStartEqVal",
                "tRoundStartEqVal",
                "tRoundStartMoney",
                "tBuyType",
                "tSpend",
                "ctStartEqVal",
                "ctRoundStartEqVal",
                "ctRoundStartMoney",
                "ctBuyType",
                "ctSpend",
            ]
            for r in self.json["gameRounds"]:
                round_item = {}
                for k in cols:
                    round_item[k] = r[k]
                    round_item["matchID"] = self.json["matchID"]
                    round_item["mapName"] = self.json["mapName"]
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
            for r in self.json["gameRounds"]:
                if r["kills"] is not None:
                    for k in r["kills"]:
                        new_k = k
                        new_k["roundNum"] = r["roundNum"]
                        new_k["matchID"] = self.json["matchID"]
                        new_k["mapName"] = self.json["mapName"]
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

    def _parse_weapon_fires(self, return_type):
        """Returns weapon fires as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error(
                "Parse weapon fires return_type must be either 'list' or 'df'"
            )
            raise ValueError("return_type must be either 'list' or 'df'")

        try:
            shots = []
            for r in self.json["gameRounds"]:
                if r["weaponFires"] is not None:
                    for wf in r["weaponFires"]:
                        new_wf = wf
                        new_wf["roundNum"] = r["roundNum"]
                        new_wf["matchID"] = self.json["matchID"]
                        new_wf["mapName"] = self.json["mapName"]
                        shots.append(new_wf)
            if return_type == "list":
                self.logger.info("Parsed weapon fires to list")
                return shots
            elif return_type == "df":
                self.logger.info("Parsed weapon fires to Pandas DataFrame")
                return pd.DataFrame(shots)
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
            for r in self.json["gameRounds"]:
                if r["damages"] is not None:
                    for d in r["damages"]:
                        new_d = d
                        new_d["roundNum"] = r["roundNum"]
                        new_d["matchID"] = self.json["matchID"]
                        new_d["mapName"] = self.json["mapName"]
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
            for r in self.json["gameRounds"]:
                if r["grenades"] is not None:
                    for g in r["grenades"]:
                        new_g = g
                        new_g["roundNum"] = r["roundNum"]
                        new_g["matchID"] = self.json["matchID"]
                        new_g["mapName"] = self.json["mapName"]
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
            for r in self.json["gameRounds"]:
                if r["bombEvents"] is not None:
                    for b in r["bombEvents"]:
                        new_b = b
                        new_b["roundNum"] = r["roundNum"]
                        new_b["matchID"] = self.json["matchID"]
                        new_b["mapName"] = self.json["mapName"]
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
            for r in self.json["gameRounds"]:
                if r["flashes"] is not None:
                    for f in r["flashes"]:
                        new_f = f
                        new_f["roundNum"] = r["roundNum"]
                        new_f["matchId"] = self.json["matchID"]
                        new_f["mapName"] = self.json["mapName"]
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
