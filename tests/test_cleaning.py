"""Tests cleaning module."""
import pandas as pd
import pytest

from awpy.parser.cleaning import associate_entities, replace_entities


class TestCleaning:
    """Class to test CSGO data cleaning functions."""

    def test_association(self):
        """Test entity association."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b)
        assert c["misutaaa-"] == "misuta"

    def test_lcss_metric(self):
        """Test LCSS metric."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b, metric="lcss")
        assert c["misutaaa-"] == "misuta"

    def test_hamming_metric(self):
        """Test Hamming metric."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b, metric="hamming")
        assert c["misutaaa-"] == "misuta"

    def test_levenshtein_metric(self):
        """Test Levenshtein metric."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b, metric="levenshtein")
        assert c["misutaaa-"] == "misuta"

    def test_jaro_metric(self):
        """Test Jaro-Winkler metric."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b, metric="jaro")
        assert c["misutaaa-"] == "misuta"

    def test_difflib(self):
        """Test difflib."""
        a = ["misutaaa-", "ZyW0o//", "peeter"]
        b = ["misuta", "Zywoo", "peter"]
        c = associate_entities(a, b, metric="difflib")
        assert c["misutaaa-"] == "misuta"

    def test_wrong_metric(self):
        """Tests if submitting a wrong metric raises an error."""
        a = ["misutaaa-", "ZyW0o//"]
        b = ["misuta", "Zywoo", "peter"]
        with pytest.raises(
            ValueError,
            match="Metric can only be",
        ):
            associate_entities(a, b, metric="bad_metric")

    def test_empty_input(self):
        """Tests empty input."""
        a = None
        b = None
        c = associate_entities(a, b, "difflib")
        assert len(c) == 1
        assert c[None] is None
        a = [None]
        b = [None]
        c = associate_entities(a, b, "difflib")
        assert len(c) == 1
        assert c[None] is None
        a = ["Test"]
        b = []
        c = associate_entities(a, b, "difflib")
        assert len(c) == 2
        assert c["Test"] is None
        a = [None]
        b = [None]
        c = associate_entities(a, b, "hamming")
        assert len(c) == 1
        assert c[None] is None
        a = ["", "Test"]
        b = []
        c = associate_entities(a, b, "hamming")
        assert len(c) == 2
        assert c[""] is None

    def test_entity_replace(self):
        """Tests if entity replacement works for a dataframe."""
        test_dataframe = pd.DataFrame(
            {"Person": ["sid", "peter", "joao"], "Country": ["DE", "US", "BR"]}
        )
        entities = {"DE": "Germany", "US": "USA", "BR": "Brazil"}
        new_df = replace_entities(test_dataframe, "Country", entities)
        assert new_df.Country.tolist() == ["Germany", "USA", "Brazil"]

    def test_entity_replace_no_col(self):
        """Tests if entity replacement fails on a non-contained column."""
        test_dataframe = pd.DataFrame(
            {"Person": ["sid", "peter", "joao"], "Country": ["DE", "US", "BR"]}
        )
        entities = {"DE": "Germany", "US": "USA", "BR": "Brazil"}
        with pytest.raises(KeyError, match="Column does not exist!"):
            replace_entities(test_dataframe, "Countryyy", entities)
