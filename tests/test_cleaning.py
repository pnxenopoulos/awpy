import pytest

from csgo.parser.cleaning import associate_entities


class TestCleaning:
    """ Class to test CSGO data cleaning functions
    """

    def test_association(self):
        """ Test entity association
        """
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b)
        assert c["misutaaa-"] == "misuta"

    def test_association_length(self):
        """ Tests association function errors on lists on unequal length.
        """
        a = ["misutaaa-", "ZyW0o//"]
        b = ["misuta", "Zywoo", "peter"]
        with pytest.raises(ValueError):
            associate_entities(a, b)

    def test_wrong_metric(self):
        """ Tests if submitting a wrong metric raises an error. 
        """
        a = ["misutaaa-", "ZyW0o//"]
        b = ["misuta", "Zywoo", "peter"]
        with pytest.raises(ValueError):
            associate_entities(a, b, metric="bad_metric")
