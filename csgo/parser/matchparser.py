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
        competition_name: A string denoting the competition name of the demo
        match_name: A string denoting the match name of the demo
        game_date: A string denoting the date of the demo
        game_time: A string denoting the time of day of the demo
    """

    def __init__(
        self,
        match_dir="",
        logfile="parser.log",
        competition_name="",
        match_name="",
        game_date="",
        game_time="",
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
        self.competition_name = competition_name
        self.match_name = match_name
        self.game_date = game_date
        self.game_time = game_time
        self.game_id = (
            competition_name + "_" + match_name + "_" + game_date + "_" + game_time
        )
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
            parser = DemoParser(
                demofile=self.match_dir + f,
                competition_name=self.competition_name,
                match_name=self.match_name,
                game_date=self.game_date,
                game_time=self.game_time,
            )
            self.game_data[map_name] = parser.parse()
            if write_json:
                parser.write_json()
        return self.game_data
