import os
import pytest
import pandas as pd

from csgo.parser import DemoParser
from csgo.parser.graph import frame_to_graph


class TestDemoParser:
    """Class to test the match parser

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

    def test_graph_output_graph_dist(self):
        """Tests if the graph output is of correct dimension using graph distance"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][0],
            metric="graph",
            map_name=self.data["MapName"],
            full=True,
        )
        assert X.shape[0] == 10
        assert X.shape[1] == 10
        assert A.shape[0] == 10
        assert A.shape[1] == 10

    def test_graph_output_graph_dist_nonfull(self):
        """Tests if the graph output is of correct dimension using graph distance and non-full parameters"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][40],
            metric="graph",
            map_name=self.data["MapName"],
            full=False,
        )
        assert X.shape[0] == 5
        assert X.shape[1] == 9
        assert A.shape[0] == 5
        assert A.shape[1] == 5

    def test_graph_output_non_graph_dist(self):
        """Tests if the graph output is of correct dimension using non-graph distance"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][0],
            metric="euclidean",
            map_name=self.data["MapName"],
            full=True,
        )
        assert X.shape[0] == 10
        assert X.shape[1] == 10
        assert A.shape[0] == 10
        assert A.shape[1] == 10

    def test_graph_output_non_graph_dist_not_full(self):
        """Tests if the graph output is of correct dimension using non-graph distance"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][40],
            metric="euclidean",
            map_name=self.data["MapName"],
            full=False,
        )
        assert X.shape[0] == 5
        assert X.shape[1] == 9
        assert A.shape[0] == 5
        assert A.shape[1] == 5

    def test_frame_to_graph_bad_map(self):
        """Tests if frame to graph fails on bad map name"""
        with pytest.raises(ValueError):
            X, A = frame_to_graph(
                frame=self.data["GameRounds"][0]["Frames"][0],
                metric="graph",
                map_name="not_a_correct_map_name",
            )

    def test_frame_to_graph_no_players(self):
        """Tests if frame to graph fails on no players in T or CT"""
        with pytest.raises(ValueError):
            X, A = frame_to_graph(
                frame=self.data["GameRounds"][-1]["Frames"][-1],
                metric="graph",
                map_name=self.data["MapName"],
            )

    def test_frame_to_graph_places(self):
        """Tests if frame to graph fails on places=True"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][40],
            metric="euclidean",
            map_name=self.data["MapName"],
            full=True,
            places=True,
        )
        assert X.shape[0] == 10
        assert X.shape[1] == 120
        assert A.shape[0] == 10
        assert A.shape[1] == 10

    def test_frame_to_graph_coordinates(self):
        """Tests if frame to graph fails on places=True"""
        X, A = frame_to_graph(
            frame=self.data["GameRounds"][0]["Frames"][40],
            metric="euclidean",
            map_name=self.data["MapName"],
            full=True,
            places=False,
            coordinates=True
        )
        assert X.shape[0] == 10
        assert X.shape[1] == 13
        assert A.shape[0] == 10
        assert A.shape[1] == 10

