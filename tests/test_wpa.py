"""Tests WPA module."""
import json
import os

import pytest
import requests

from awpy.analytics.wpa import round_win_probability, state_win_probability
from awpy.parser import DemoParser


class TestStates:
    """Class to test WPA.

    Uses:
    www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser."""
        with open("tests/test_data.json", encoding="utf-8") as f:
            self.demo_data = json.load(f)
        self._get_demofile(
            demo_link=self.demo_data["default"]["url"], demo_name="default"
        )
        self.parser = DemoParser(demofile="default.dem", log=True, parse_rate=256)
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none."""
        self.parser = None
        self.data = None
        files_in_directory = os.listdir()
        if filtered_files := [
            file for file in files_in_directory if file.endswith((".dem", ".json"))
        ]:
            for f in filtered_files:
                os.remove(f)

    @staticmethod
    def _get_demofile(demo_link: str, demo_name: str) -> None:
        print(f"Requesting {demo_link}")
        r = requests.get(demo_link, timeout=100)
        with open(f"{demo_name}.dem", "wb") as demo_file:
            demo_file.write(r.content)

    @staticmethod
    def _delete_demofile(demo_name: str) -> None:
        print(f"Removing {demo_name}")
        os.remove(f"{demo_name}.dem")

    def test_state_win_probability(self):
        """Tests state_win_probability."""
        my_model = 0
        with pytest.raises(NotImplementedError):
            state_win_probability(self.data["gameRounds"][7]["frames"][0], my_model)

    def test_round_win_probability(self):
        """Tests round_win_probability."""
        with pytest.raises(NotImplementedError):
            round_win_probability(5, 2, "de_inferno")
