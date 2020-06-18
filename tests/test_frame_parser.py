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
            match_id="test",
        )

    def teardown_class(self):
        """ Set parser to none
        """
        self.parser = None

    def test_logger_write(self):
        """ Tests if the parser logs correctly.
        """
        self.parser.log = True
        assert self.parser.logger.name == "CSGODemoParser"
        assert os.path.exists("csgo_parser.log")

    def test_parse(self):
        """ Tests if the parser parses the match and writes the XML file
        """
        self.parser.parse()
        assert os.path.exists("test.xml")
