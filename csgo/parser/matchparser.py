import logging

from os import listdir
from os.path import exists, isfile, join

from csgo.parser import DemoParser
from csgo.utils import check_go_version


class MatchParser:
    """ This class parses a folder of CSGO demofiles and outputs a dictionary
    with the keys as the maps played.

    Attributes:
        match_dir (string) : Directory to match with multiple demofiles
        log (boolean)      : A boolean denoting if a log will be written. If true, log is written to "csgo_parser.log"
        match_id (string)  : A unique demo name/game id

    Raises:
        ValueError : Raises a ValueError if the Golang version is lower than 1.14
    """

    def __init__(
        self, match_dir="", log=False, match_id="",
    ):
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
        self.match_id = match_id
        self.game_data = {}
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
            self.logger.info("Initialized CSGODemoParser for " + self.match_dir)
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
            self.logger = logging.getLogger("CSGODemoParser")
            self.logger.info("Initialized CSGODemoParser for " + self.match_dir)
        acceptable_go = check_go_version()
        if not acceptable_go:
            raise ValueError("Go version too low! Needs 1.14.0")

    def parse(self, write_json=False):
        """ Parses the demofiles in self.match_dir

        Attributes:
            write_json (boolean) : Boolean indicating if JSON will write

        Returns:
            Dictionary of dictionaries, where the first level keys are maps, and the second level keys correspond to that map's set of data.
        """
        for f in self.demofiles:
            map_name = f[3:-4]
            parser = DemoParser(demofile=self.match_dir + f, match_id=self.match_id)
            self.game_data[map_name] = parser.parse()
            if write_json:
                parser.write_json()
        return self.game_data
