import json
import os
import requests
import pytest

from awpy.parser import DemoParser
from awpy.analytics.wpa import state_win_probability, round_win_probability


class TestStates:
    """Class to test WPA

    Uses https://www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser"""
        with open("tests/test_data.json", encoding="utf-8") as f:
            self.demo_data = json.load(f)
        self._get_demofile(
            demo_link=self.demo_data["default"]["url"], demo_name="default"
        )
        self.parser = DemoParser(demofile="default.dem", log=True, parse_rate=256)
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none"""
        self.parser = None
        self.data = None
        files_in_directory = os.listdir()
        filtered_files = [
            file
            for file in files_in_directory
            if file.endswith(".dem") or file.endswith(".json")
        ]
        if len(filtered_files) > 0:
            for f in filtered_files:
                os.remove(f)

    @staticmethod
    def _get_demofile(demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    @staticmethod
    def _delete_demofile(demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    def test_state_win_probability(self):
        """Tests state_win_probability"""
        with pytest.raises(NotImplementedError):
            my_model = 0
            state_win_probability(self.data["gameRounds"][7]["frames"][0], my_model)

    def test_round_win_probability(self):
        """Tests round_win_probability"""
        with pytest.raises(NotImplementedError):
            round_win_probability(5, 2, "de_inferno")
