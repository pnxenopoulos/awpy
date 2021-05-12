import requests
import os
import pytest
import pandas as pd

from csgo.parser import DemoParser

class TestDemoParser:
    """Class to test the match parser

    We use the following demofiles:
        - [1] https://www.hltv.org/matches/2347706/ence-vs-endpoint-european-development-championship-3
        - [2] https://www.hltv.org/matches/2346568/evil-geniuses-vs-astralis-iem-katowice-2021
        - [3] https://www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
        - [4] https://www.hltv.org/matches/2337844/astralis-vs-liquid-blast-pro-series-global-final-2019
    """

    def setup_class(self):
        """Setup class by instantiating parser
        """
        self.parser = None
        self.demofiles = {
            "astralis-vs-liquid-m1-inferno": "https://storage.googleapis.com/csgo-tests/astralis-vs-liquid-m1-inferno.dem",
            "astralis-vs-liquid-m2-nuke": "https://storage.googleapis.com/csgo-tests/astralis-vs-liquid-m2-nuke.dem",
            "ence-vs-endpoint-m1-inferno": "https://storage.googleapis.com/csgo-tests/ence-vs-endpoint-m1-inferno.dem",
            "ence-vs-endpoint-m2-train": "https://storage.googleapis.com/csgo-tests/ence-vs-endpoint-m2-train.dem",
            "evil-geniuses-vs-astralis-m1-train": "https://storage.googleapis.com/csgo-tests/evil-geniuses-vs-astralis-m1-train.dem",
            "evil-geniuses-vs-astralis-m2-dust2": "https://storage.googleapis.com/csgo-tests/evil-geniuses-vs-astralis-m2-dust2.dem",
            "og-vs-natus-vincere-m1-dust2": "https://storage.googleapis.com/csgo-tests/og-vs-natus-vincere-m1-dust2.dem",
            "og-vs-natus-vincere-m2-mirage": "https://storage.googleapis.com/csgo-tests/og-vs-natus-vincere-m2-mirage.dem",
            "og-vs-nature-vincere-m3-nuke": "https://storage.googleapis.com/csgo-tests/og-vs-natus-vincere-m3-nuke.dem"
        }

    def teardown_class(self):
        """Set parser to none, deletes all demofiles
        """
        self.parser = None
        files_in_directory = os.listdir(directory)
        filtered_files = [file for file in files_in_directory if file.endswith(".dem") or file.endswith(".json")]
        if len(filtered_files) > 0:
            os.remove(path_to_file)

    def _get_demofile(self, demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    def _delete_demofile(self, demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    def test_parse(self):
        parse_errors = 0
        for file in self.demofiles:
            self._get_demofile(self.demofiles[file], file)
            self.parser = DemoParser(
                demofile=file + ".dem",
                log=True,
                demo_id=file,
                parse_rate=128,
            )
            self.parser.parse()
            if self.parser.parse_error == True:
                parse_errors += 1
            self._delete_demofile(file)
        assert parse_errors == 0

    