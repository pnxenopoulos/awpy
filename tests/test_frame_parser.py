import os
import pytest

from csgo.parser import FrameParser


class TestFrameParser:
    """ Class to test the frame parser
    """

    def setup_class(self):
        """ Setup class by instantiating parser
        """
        self.parser = FrameParser(
            demofile="tests/natus-vincere-vs-astralis-m1-dust2.dem",
            log=True,
            match_id="natus-vincere-vs-astralis-m1-dust2",
        )

    def teardown_class(self):
        """ Set parser to none
        """
        self.parser = None

    def test_match_id(self):
        """ Tests if a match_id is not given is parsed properly
        """
        self.parser = FrameParser(
            demofile="tests/natus-vincere-vs-astralis-m1-dust2.dem", log=False,
        )
        assert self.parser.match_id == "natus-vincere-vs-astralis-m1-dust2"

    def test_logger_write(self):
        """ Tests if the parser logs correctly.
        """
        self.parser.log = True
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_parser.log")

    def test_parse(self):
        """ Tests if the parser parses the match and writes the XML file
        """
        self.parser.parse(df=False)
        assert os.path.exists("natus-vincere-vs-astralis-m1-dust2.xml")
        assert self.parser.demo_map == "de_dust2"

    def test_parse_df(self):
        """ Tests if the parser returns a full Pandas dataframe
        """
        df = self.parser.parse(df=True)
        assert df.shape[0] > 0

    def test_correct_round_num(self):
        """ Tests if the parser returns the correct number of rounds
        """
        df = self.parser.parse(df=True)
        assert len(df.RoundNum.unique()) == 21

