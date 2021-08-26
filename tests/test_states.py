import os
import pytest
import pandas as pd

from csgo.parser import DemoParser
from csgo.parser.states import generate_game_state


class TestStates:
    """Class to test the state parsing

    Uses https://www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser"""
        self.parser = DemoParser(
            demofile="tests/og-vs-natus-vincere-m1-dust2.dem",
            log=True,
            demo_id="test",
            parse_rate=128,
        )
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none"""
        self.parser = None
        self.data = None

    def test_wrong_frame_input(self):
        """Tests that wrong frame type raises error"""
        frame = "not a dict"
        with pytest.raises(ValueError):
            generate_game_state(frame)
    
    def test_wrong_state_type(self):
        """Tests that wrong state type raises error"""
        with pytest.raises(ValueError):
            generate_game_state(self.data["GameRounds"][0]["Frames"][0])
