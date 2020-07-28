import logging
import os
import subprocess

import pandas as pd
import xml.etree.ElementTree as ET

from csgo.utils import NpEncoder, check_go_version


class FrameParser:
    """ This class can parse a CSGO demofile to output game data in a logical structure. Accessible via csgo.parser import FrameParser

    Attributes:
        demofile (string) : A string denoting the path to the demo file, which ends in .dem
        log (boolean)     : A boolean denoting if a log will be written. If true, log is written to "csgo_parser.log"
        match_id (string) : A unique demo name/game id
    
    Raises:
        ValueError : Raises a ValueError if the Golang version is lower than 1.14
    """

    def __init__(
        self, demofile="", log=False, match_id="",
    ):
        self.demofile = demofile
        self.demo_error = False
        if match_id == "":
            self.match_id = demofile[demofile.rfind("/") + 1 : -4]
        else:
            self.match_id = match_id
        if log:
            logging.basicConfig(
                filename="csgo_parser.log",
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            self.logger = logging.getLogger("CSGODemoParser")
            self.logger.handlers = []
            fh = logging.FileHandler("csgo_parser.log")
            fh.setLevel(logging.INFO)
            self.logger.addHandler(fh)
            self.logger.info(
                "Initialized CSGODemoParser with demofile " + self.demofile
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            self.logger = logging.getLogger("CSGODemoParser")
            self.logger.info(
                "Initialized CSGODemoParser with demofile " + self.demofile
            )
        acceptable_go = check_go_version()
        if not acceptable_go:
            raise ValueError("Go version too low! Needs 1.14.0")

    def _parse_xml(self):
        """ Parse a demofile using the Go script parse_frames.go -- this function takes no arguments

        Returns:
            Returns a written file named match_id.xml
        """
        self.logger.info(
            "Starting CSGO Golang demofile parser, reading in "
            + os.getcwd()
            + "/"
            + self.demofile
        )
        path = os.path.join(os.path.dirname(__file__), "")
        self.logger.info("Running Golang frame parser from " + path)
        f = open(self.match_id + ".xml", "w")
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_frames.go",
                "-demo",
                os.getcwd() + "/" + self.demofile,
            ],
            stdout=f,
            cwd=path,
        )
        ret_code = proc.wait()
        f.flush()
        self.logger.info(
            "Demofile parsing complete, output written to " + self.match_id + ".xml"
        )

    def _clean_xml(self):
        """ Clean the XML file from ._parse_xml()

        Returns:
            Returns a written file named match_id.xml
        """
        self.tree = ET.parse(self.match_id + ".xml")
        self.game = self.tree.getroot()
        self.demo_map = self.game.attrib["Map"]
        start_round = 0
        start_round_elem = None
        for i, round_elem in enumerate(self.game):
            if (
                int(round_elem.attrib["CTScore"]) + int(round_elem.attrib["TScore"])
                == 0
            ):
                start_round = i
        for j, round_elem in enumerate(self.game):
            if start_round > j:
                self.game.remove(round_elem)
        self.tree.write(open(self.match_id + ".xml", "w"), encoding="unicode")
        self.logger.info("Cleaned the round XML to remove noisy rounds")

    def parse(self, df=True):
        """ Parse the given demofile into an XML file of game "frames"

        Args:
            df (bool) : True if DataFrame is to be returned

        Returns:
            Returns a written file named match_id.xml
            If df==True, returns a Pandas dataframe of the frames
        """
        self._parse_xml()
        self._clean_xml()
        if df == True:
            i = 0
            all_frames = []
            game_map = self.demo_map
            for idx, game_round in enumerate(self.game):
                frames = []
                for frame in game_round:
                    for team in frame:
                        for player in team:
                            infos_dict = {"RoundNum": idx + 1}
                            infos_dict.update(team.attrib)
                            infos_dict.update(player.attrib)
                            infos_dict.update(frame.attrib)
                            frames.append(infos_dict)
                all_frames.extend(frames)
            df = pd.DataFrame.from_dict(all_frames)
            df = df.groupby(["SteamId", "RoundNum", "Tick"]).last().reset_index()
            df["MatchId"] = self.match_id
            df["MapName"] = game_map
            df["Seconds"] = pd.to_numeric(df["TicksSinceStart"]) / 128
            df["SteamId"] = df["SteamId"].astype(int)
            df["Tick"] = df["Tick"].astype(int)
            df["EqVal"] = df["EqVal"].astype(int)
            df["Hp"] = df["Hp"].astype(int)
            df["Armor"] = df["Armor"].astype(int)
            df["X"] = pd.to_numeric(df["X"])
            df["Y"] = pd.to_numeric(df["Y"])
            df["Z"] = pd.to_numeric(df["Z"])
            df["AreaId"] = df["AreaId"].astype(int)
            df["HasHelmet"] = df["HasHelmet"].astype(bool)
            df["HasDefuse"] = df["HasDefuse"].astype(bool)
            return df
