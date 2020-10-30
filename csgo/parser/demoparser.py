import json
import logging
import os
import re
import subprocess
import pandas as pd

from csgo.utils import NpEncoder, check_go_version


class DemoParser:
    """ This class can parse a CSGO demofile to various outputs, such as JSON or CSV. Accessible via csgo.parser import DemoParser

    Attributes:
        demofile (string) : A string denoting the path to the demo file, which ends in .dem
        log (boolean)     : A boolean denoting if a log will be written. If true, log is written to "csgo_parser.log"
        demo_id (string) : A unique demo name/game id. Default is inferred from demofile name
        parse_rate (int)  : One of 128, 64, 32, 16, 8, 4, 2, or 1. The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks. Default is 32.
    
    Raises:
        ValueError : Raises a ValueError if the Golang version is lower than 1.14
    """

    def __init__(self, demofile="", log=False, demo_id=None, parse_rate=None):
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
        if not os.path.exists(demofile):
            self.logger.error("Demofile path does not exist!")
            raise ValueError("Demofile path does not exist!")
        
        # Handle demofile and demo_id name. Finds right most '/' in case demofile is a specified path.
        self.demofile = demofile
        self.logger.info("Initialized CSGODemoParser with demofile " + self.demofile)
        if demo_id is None:
            self.demo_id = demofile[demofile.rfind("/") + 1 : -4]
        else:
            self.demo_id = demo_id
        self.logger.info("Setting demo id to " + self.demo_id)

        # Handle parse rate. Must be a power of 2^0 to 2^7. If not, then default to 2^5.
        if parse_rate is None:
            self.logger.warning("No parse rate set")
            self.parse_rate = 32
        elif parse_rate not in [1, 2, 4, 8, 16, 32, 64, 128]:
            self.logger.warning(
                "Parse rate of "
                + str(parse_rate)
                + " not acceptable! Parse rate must be between 2^0 and 2^7. Setting to DEFAULT value of 32."
            )
            self.parse_rate = 32
        else:
            self.parse_rate = parse_rate
        self.logger.info("Setting parse rate to " + str(self.parse_rate))

    def _parse_demo(self):
        """ Parse a demofile using the Go script parse_demo.go -- this function takes no arguments, all arguments are set in initialization.

        Returns:
            Outputs a JSON file to current working directory.
        """
        path = os.path.join(os.path.dirname(__file__), "")
        self.logger.info("Running Golang parser from " + path)
        self.logger.info("Looking for file at " + os.getcwd() + "/" + self.demofile)
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_demo.go",
                "-demo",
                os.getcwd() + "/" + self.demofile,
                "-parserate",
                str(self.parse_rate),
                "-demoid",
                str(self.demo_id),
                "-out",
                os.getcwd(),
            ],
            stdout=subprocess.PIPE,
            cwd=path,
        )
        output = proc.stdout.read().splitlines()
        if os.path.isfile(str(self.demo_id) + ".json"):
            self.logger.info(
                "Wrote demo parse output to " + str(self.demo_id) + ".json"
            )
        else:
            self.logger.error("No file produced, error in calling Golang")

    def _read_json(self):
        """ Reads the JSON file created by _parse_demo()

        Returns:
            A dictionary of the JSON output of _parse_demo()
        """
        json_path = str(self.demo_id) + ".json"
        self.logger.info("Reading in JSON from " + json_path)
        with open(json_path) as f:
            demo_data = json.load(f)
        self.json = demo_data
        self.logger.info(
            "JSON data loaded, available in the `json` attribute to parser"
        )
        return demo_data

    def _generate_stats(self):
        """ Generates stats based on the JSON file created from _parse_demo and _read_json

        Returns:
            A dictionary with a "Stats" key
        """
        self.json["Stats"] = dict()
        return NotImplementedError

    def parse(self):
        """ Wrapper for _parse_demo() and _read_json(). Provided for user convenience.

        Returns:
            A dictionary of JSON output
        """
        self._parse_demo()
        self._read_json()
        if self.json:
            self.logger.info("Successfully returned JSON output")
            return self.json
        else:
            self.logger.error("JSON couldn't be returned")
            return None

    def _parse_kills(self, return_type):
        """ Returns kills as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if return_type not in ["list", "df"]:
            self.logger.error("Parse kills return_type must be either 'list' or 'df'")
            raise ValueError("return_type must be either 'list' or 'df'")
        
        if self.json:
            kills = []
                for r in self.json["GameRounds"]:
                    for k in r["Kills"]:
                        kills.append(k)
            if return_type == "list":
                self.logger.info("Parsed kills to list")
                return kills
            elif return_type == "df":
                self.logger.info("Parsed kills to Pandas DataFrame")
                return pd.DataFrame(kills)
        else:
            self.logger.error("JSON not found")
            return None

    def _parse_damages(self, return_type):
        """ Returns damages as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            damages = []
                for r in self.json["GameRounds"]:
                    for d in r["Damages"]:
                        damages.append(d)
            if return_type == "list":
                self.logger.info("Parsed damages to list")
                return damages
            elif return_type == "df":
                self.logger.info("Parsed damages to Pandas DataFrame")
                return pd.DataFrame(damages)
        else:
            self.logger.error("JSON not found")
            return None

    def _parse_grenades(self, return_type):
        """ Returns grenades as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            grenades = []
                for r in self.json["GameRounds"]:
                    for g in r["Grenades"]:
                        grenades.append(g)
            if return_type == "list":
                self.logger.info("Parsed grenades to list")
                return grenades
            elif return_type == "df":
                self.logger.info("Parsed grenades to Pandas DataFrame")
                return pd.DataFrame(grenades)
        else:
            self.logger.error("JSON not found")
            return None

    def _parse_bomb_events(self, return_type):
        """ Returns bomb events as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            bomb_events = []
                for r in self.json["GameRounds"]:
                    for b in r["BombEvents"]:
                        bomb_events.append(b)
            if return_type == "list":
                self.logger.info("Parsed bomb_events to list")
                return bomb_events
            elif return_type == "df":
                self.logger.info("Parsed bomb_events to Pandas DataFrame")
                return pd.DataFrame(bomb_events)
        else:
            self.logger.error("JSON not found")
            return None
        return NotImplementedError

    def _parse_flashes(self, return_type):
        """ Returns flashes as either a list or Pandas dataframe

        Args:
            return_type (string) : Either "list" or "df"

        Returns:
            A list or Pandas dataframe
        """
        if self.json:
            flashes = []
                for r in self.json["GameRounds"]:
                    for g in r["Flashes"]:
                        flashes.append(g)
            if return_type == "list":
                self.logger.info("Parsed flashes to list")
                return flashes
            elif return_type == "df":
                self.logger.info("Parsed flashes to Pandas DataFrame")
                return pd.DataFrame(flashes)
        else:
            self.logger.error("JSON not found")
            return None