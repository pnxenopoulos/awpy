""" Parsing class for a folder of demofiles
"""

import logging

from os import listdir
from os.path import exists, isfile, join

from csgo.parser import DemoParser


class MatchParser:
    """ This class parses a folder of CSGO demofiles and outputs a dictionary
    with the keys as the maps.

    Attributes:
        match_dir: Directory to match with multiple demofiles
        logfile: A string denoting the path to the output log file
        demo_name: A unique demo name/game id
    """

    def __init__(
        self, match_dir="", logfile="parser.log", demo_name="",
    ):
        """ Initialize a GameParser object
        """
        if not exists(match_dir):
            raise NotADirectoryError("Given match directory does not exist!")
        dir_files = [f for f in listdir(match_dir) if isfile(join(match_dir, f))]
        self.demofiles = []
        for file in dir_files:
            if file[-4:] == ".dem":
                self.demofiles.append(file)
        if len(self.demofiles) == 0:
            raise ValueError("Given match directory has no demofiles!")
        self.match_dir = match_dir
        self.game_id = demo_name
        self.game_data = {}
        self.logfile = logfile
        logging.basicConfig(
            filename=self.logfile,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("GameParser")
        self.logger.info("Initialized CSGO GameParser in path " + self.match_dir)

    def parse(self, write_json=False):
        """ Parses the demofiles in self.match_dir

        Attributes:
            - write_json (bool) : Boolean indicating if JSON will write
        """
        for f in self.demofiles:
            map_name = f[3:-4]
            parser = DemoParser(demofile=self.match_dir + f, demo_name=self.game_id)
            self.game_data[map_name] = parser.parse()
            if write_json:
                parser.write_json()
        return self.game_data
