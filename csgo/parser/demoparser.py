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
        with open(json_path, encoding="utf8") as f:
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
                demo_data = self._parse_json()
                self.logger.info("Returned dataframe output")
                return demo_data
            else:
                self.logger.error("Parse return_type must be either 'json' or 'df'")
                raise ValueError("return_type must be either 'json' or 'df'")
        else:
            self.logger.error("JSON couldn't be returned")
            raise AttributeError("No JSON parsed!")

    def _parse_json(self):
        """Returns JSON into dictionary where keys correspond to data frames

        Returns:
            A dictionary of output
        """
        demo_data = {}
        demo_data["matchID"] = self.json["matchID"]
        demo_data["clientName"] = self.json["clientName"]
        demo_data["mapName"] = self.json["mapName"]
        demo_data["tickRate"] = self.json["tickRate"]
        demo_data["playbackTicks"] = self.json["playbackTicks"]
        demo_data["rounds"] = self._parse_rounds()
        demo_data["kills"] = self._parse_kills()
        demo_data["damages"] = self._parse_damages()
        demo_data["grenades"] = self._parse_grenades()
        demo_data["flashes"] = self._parse_flashes()
        demo_data["weaponFires"] = self._parse_weapon_fires()
        demo_data["bombEvents"] = self._parse_bomb_events()
        demo_data["frames"] = self._parse_frames()
        demo_data["playerFrames"] = self._parse_player_frames()
        self.logger.info("Returned dataframe output")
        return demo_data

    def _parse_frames(self):
        """Returns frames as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
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
            return pd.DataFrame(frames_dataframes)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_player_frames(self):
        """Returns player frames as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
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
            return pd.DataFrame(player_frames_df)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_rounds(self):
        """Returns rounds as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
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
            return pd.DataFrame(rounds)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_kills(self):
        """Returns kills as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            kills = []
            for r in self.json["gameRounds"]:
                if r["kills"] is not None:
                    for k in r["kills"]:
                        new_k = k
                        new_k["roundNum"] = r["roundNum"]
                        new_k["matchID"] = self.json["matchID"]
                        new_k["mapName"] = self.json["mapName"]
                        kills.append(new_k)
            return pd.DataFrame(kills)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_weapon_fires(self):
        """Returns weapon fires as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            shots = []
            for r in self.json["gameRounds"]:
                if r["weaponFires"] is not None:
                    for wf in r["weaponFires"]:
                        new_wf = wf
                        new_wf["roundNum"] = r["roundNum"]
                        new_wf["matchID"] = self.json["matchID"]
                        new_wf["mapName"] = self.json["mapName"]
                        shots.append(new_wf)
            return pd.DataFrame(shots)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_damages(self):
        """Returns damages as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
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
            return pd.DataFrame(damages)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_grenades(self):
        """Returns grenades as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
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
            return pd.DataFrame(grenades)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_bomb_events(self):
        """Returns bomb events as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
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
            return pd.DataFrame(bomb_events)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def _parse_flashes(self):
        """Returns flashes as either a list or Pandas dataframe

        Returns:
            A list or Pandas dataframe
        """
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
            return pd.DataFrame(flashes)
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def clean_rounds(
        self,
        remove_warmups=True,
        remove_knifes=True,
        bad_round_endings=["Draw", "Unknown", ""],
        remove_time=True,
    ):
        """Cleans rounds to remove warmups, knives, bad round endings, etc."""
        if self.json:
            self.remove_warmups()
            self.remove_time_rounds()
            self.remove_knife_rounds()
            self.remove_excess_kill_rounds()
            self.remove_end_round()
            self.renumber_rounds()
            self.rescore_rounds()
            self.write_json()
            return self.json
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def write_json(self):
        """Rewrite the JSON file"""
        with open(self.output_file, "w", encoding="utf8") as fp:
            json.dump(self.json, fp, indent=4)

    def renumber_rounds(self):
        """Renumbers rounds"""
        if self.json["gameRounds"]:
            for i, r in enumerate(self.json["gameRounds"]):
                self.json["gameRounds"][i]["roundNum"] = i + 1
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def rescore_rounds(self):
        """Rescores the rounds"""
        if self.json["gameRounds"]:
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
                    self.json["gameRounds"][i]["tScore"] = self.json["gameRounds"][i-1]["endTScore"]
                    self.json["gameRounds"][i]["ctScore"] = self.json["gameRounds"][i-1]["endCTScore"]
                    if self.json["gameRounds"][i]["winningSide"] == "ct":
                        self.json["gameRounds"][i]["endCTScore"] = self.json["gameRounds"][i]["ctScore"] + 1
                        self.json["gameRounds"][i]["endTScore"] = self.json["gameRounds"][i]["tScore"]
                    if self.json["gameRounds"][i]["winningSide"] == "t":
                        self.json["gameRounds"][i]["endCTScore"] = self.json["gameRounds"][i]["ctScore"]
                        self.json["gameRounds"][i]["endTScore"] = self.json["gameRounds"][i]["tScore"] + 1
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def remove_warmups(self):
        """Remove warmup rounds from JSON."""
        if self.json:
            cleaned_rounds = []
            # Remove warmups where the demo may have started recording in the middle of a warmup round
            if "warmupChanged" in self.json["matchPhases"]:
                if len(self.json["matchPhases"]["warmupChanged"]) > 1:
                    last_warmup_changed = self.json["matchPhases"]["warmupChanged"][1]
                    for r in self.json["gameRounds"]:
                        if (r["startTick"] > last_warmup_changed) and (not r["isWarmup"]):
                            cleaned_rounds.append(r)
                else:
                    for r in self.json["gameRounds"]:
                        if not r["isWarmup"]:
                            cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def remove_end_round(self, bad_endings=["Draw", "Unknown", ""]):
        """Remove rounds with bad endings from JSON."""
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"]:
                if r["roundEndReason"] not in bad_endings:
                    cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def remove_knife_rounds(self):
        """Remove knife round."""
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"]:
                if not r["isWarmup"] and r["kills"]:
                    total_kills = len(r["kills"])
                    total_knife_kills = 0
                    for k in r["kills"]:
                        if k["weapon"] == "Knife":
                            total_knife_kills += 1
                    if total_knife_kills != total_kills:
                        cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def remove_excess_kill_rounds(self):
        """Removes rounds with too many kills."""
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"]:
                if not r["isWarmup"]:
                    if r["kills"] is not None:
                        total_kills = len(r["kills"])
                        if total_kills <= 10:
                            cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")

    def remove_time_rounds(self, time_minimum=10):
        """Removes rounds with incorrect start/end ticks."""
        if self.json:
            cleaned_rounds = []
            for r in self.json["gameRounds"]:
                if (r["startTick"] <= r["endTick"]) or (r["startTick"] <= r["endOfficialTick"]) or (r["startTick"] <= r["freezeTimeEndTick"]):
                    cleaned_rounds.append(r)
            self.json["gameRounds"] = cleaned_rounds
        else:
            self.logger.error("JSON not found. Run .parse()")
            raise AttributeError("JSON not found. Run .parse()")
