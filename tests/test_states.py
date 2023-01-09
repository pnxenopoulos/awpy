import json
import os
import requests

from awpy.parser import DemoParser
from awpy.analytics.states import (
    generate_vector_state,
    generate_graph_state,
    generate_set_state,
)


class TestStates:
    """Class to test the state parsing

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

    def test_vector_output(self):
        """Tests that vector output is a dict with 3 keys"""
        game_state = generate_vector_state(
            self.data["gameRounds"][7]["frames"][0], self.data["mapName"]
        )
        assert isinstance(game_state, dict)
        assert "ctAlive" in game_state
        assert game_state["ctAlive"] == 5
        game_state = generate_vector_state(
            self.data["gameRounds"][7]["frames"][6], self.data["mapName"]
        )
        assert game_state["ctAlive"] == 2
        assert game_state["tAlive"] == 4

    def test_graph_output(self):
        """Tests that vector output is a dict with 3 keys"""
        game_state = generate_graph_state(self.data["gameRounds"][7]["frames"][0])
        assert isinstance(game_state, dict)

        assert "ct" in game_state
        assert isinstance(game_state["ct"], list)
        assert "t" in game_state
        assert isinstance(game_state["t"], list)
        assert "global" in game_state
        assert isinstance(game_state["global"], list)

    def test_set_output(self):
        """Tests that set output is a dict with 3 keys"""
        game_state = generate_set_state(self.data["gameRounds"][7]["frames"][0])
        assert isinstance(game_state, dict)

        assert "ct" in game_state
        assert isinstance(game_state["ct"], list)
        assert "t" in game_state
        assert isinstance(game_state["t"], list)
        assert "global" in game_state
        assert isinstance(game_state["global"], list)
