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
        start_round = 0
        start_round_elem = None
        for i, round_elem in enumerate(self.game):
            if (
                int(round_elem.attrib["ctScore"]) + int(round_elem.attrib["tScore"])
                == 0
            ):
                start_round = i
        for j, round_elem in enumerate(self.game):
            if start_round < j:
                self.game.remove(round_elem)
        tree.write(open(self.match_id + ".xml", "w"), encoding="unicode")
        self.logger.info("Cleaned the round XML to remove noisy rounds")

    def parse(self, df=True):
        """ Parse the given demofile into an XML file of game "frames"

        Returns:
            Returns a written file named match_id.xml
            If df==True, returns a Pandas dataframe of the frames
        """
        self._parse_xml()
        self._clean_xml()
        if df == True:
            i = 0
            all_frames = []
            game_map = self.game.attrib["map"]
            for idx, game_round in enumerate(self.game):
                frames = []
                for frame in game_round:
                    if frame.tag == "roundEnd":
                        round_winner = frame.attrib["winningTeam"]
                    for team in frame:
                        for player in team:
                            # wow this is efficient
                            infos_dict = {"gameRound": idx}
                            infos_dict.update(team.attrib)
                            infos_dict.update(player.attrib)
                            infos_dict.update(frame.attrib)
                            frames.append(infos_dict)
                [frame.update({"winningTeam": round_winner}) for frame in frames]
                all_frames.extend(frames)
            df = pd.DataFrame.from_dict(all_frames)
            return df
