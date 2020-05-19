import os
import pytest
import pandas as pd

from csgo.parser import MatchParser


class TestMatchParser:
    """ Class to test the game parser
    """

    def setup_class(self):
        """ Setup class by instantiating parser
        """
        self.parser = MatchParser(
            match_dir="tests/",
            competition_name="IEM-Katowice-2020",
            match_name="Natus-Vincere-vs-Astralis",
            game_date="02-29-2020",
            game_time="13:35",
        )

    def teardown_class(self):
        """ Set parser to none
        """
        self.parser = None

    def test_nonexistant_dir(self):
        """ Tests if the game parser issues a ValueError on a nonexistant directory
        """
        with pytest.raises(NotADirectoryError):
            test_parser = MatchParser(
                match_dir="fake_dir/",
                competition_name="IEM-Katowice-2020",
                match_name="Natus-Vincere-vs-Astralis",
                game_date="02-29-2020",
                game_time="13:35",
            )

    def test_no_demofiles_dir(self):
        """ Tests if the game parser issues a ValueError on a dir with no demofiles
        """
        with pytest.raises(ValueError):
            test_parser = MatchParser(
                match_dir="csgo/",
                competition_name="IEM-Katowice-2020",
                match_name="Natus-Vincere-vs-Astralis",
                game_date="02-29-2020",
                game_time="13:35",
            )

    def test_demofile_list(self):
        """ Tests if the game parser finds all demofiles
        """
        assert len(self.parser.demofiles) == 1

    def test_game_parse(self):
        """ Tests if the game parser can parse the demofiles
        """
        game_data = self.parser.parse()
        assert type(game_data) == type({})
        assert len(game_data.keys()) == 1

    def test_game_parse_write_json(self):
        """ Tests if the game parser writes JSON files
        """
        game_data = self.parser.parse(write_json=True)
        assert os.path.exists(
            "IEM-Katowice-2020_Natus-Vincere-vs-Astralis_02-29-2020_13:35_de_dust2.json"
        )
