import pytest

from csgo.parser.cleaning import associate_players


class TestCleaning:
    """ Class to test CSGO data cleaning functions
    """

    def test_player_association(self):
        """ Test player association
        """
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_players(a, b)
        assert c["misutaaa-"] == "misuta"

    def test_player_association_length(self):
        """ Tests associate players function errors on lists on unequal length.
        """
        a = ["misutaaa-", "ZyW0o//"]
        b = ["misuta", "Zywoo", "peter"]
        with pytest.raises(ValueError):
            associate_players(a, b)
