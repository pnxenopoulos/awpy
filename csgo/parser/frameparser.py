import logging
import os
import subprocess

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
        self.match_id = match_id
        self.rounds = []
        self.demo_error = False
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

    def parse(self):
        """ Parse a demofile using the Go script parse_frames.go -- this function takes no arguments

        Args:
        output_file (string) : The output file path for the resulting XML file

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
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_frames.go",
                "-demo",
                os.getcwd() + "/" + self.demofile,
                ">",
                "match_id" + ".xml",
            ],
            stdout=subprocess.PIPE,
            cwd=path,
        )
        self.logger.info(
            "Demofile parsing complete, output written to " + self.match_id + ".xml"
        )
