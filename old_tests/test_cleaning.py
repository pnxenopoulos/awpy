"""Tests cleaning module."""
import pandas as pd
import pytest

from awpy.parser.cleaning import associate_entities, replace_entities


class TestCleaning:
    """Class to test CSGO data cleaning functions."""

    def setup_class(self):
        """Setup class by defining loading dictionary of test demo files."""
        self.game_names = ["misutaaa-", "ZyW0o//", "peeter"]
        self.entity_names = ["misuta", "Zywoo", "peter"]

    def test_association(self):
        """Test entity association."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy()
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_lcss_metric(self):
        """Test LCSS metric."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy(), metric="lcss"
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_hamming_metric(self):
        """Test Hamming metric."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy(), metric="hamming"
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_levenshtein_metric(self):
        """Test Levenshtein metric."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy(), metric="levenshtein"
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_jaro_metric(self):
        """Test Jaro-Winkler metric."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy(), metric="jaro"
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_difflib(self):
        """Test difflib."""
        associated_entities = associate_entities(
            self.game_names, self.entity_names.copy(), metric="difflib"
        )
        assert associated_entities["misutaaa-"] == "misuta"

    def test_wrong_metric(self):
        """Tests if submitting a wrong metric raises an error."""
        with pytest.raises(
            ValueError,
            match="Metric can only be",
        ):
            associate_entities(
                self.game_names, self.entity_names.copy(), metric="bad_metric"
            )

    def test_empty_input(self):
        """Tests empty input."""
        a = None
        b = None
        associated_entities = associate_entities(a, b, "difflib")
        assert len(associated_entities) == 1
        assert associated_entities[None] is None
        a = [None]
        b = [None]
        associated_entities = associate_entities(a, b, "difflib")
        assert len(associated_entities) == 1
        assert associated_entities[None] is None
        a = ["Test"]
        b = []
        associated_entities = associate_entities(a, b, "difflib")
        assert len(associated_entities) == 2
        assert associated_entities["Test"] is None
        a = [None]
        b = [None]
        associated_entities = associate_entities(a, b, "hamming")
        assert len(associated_entities) == 1
        assert associated_entities[None] is None
        a = ["", "Test"]
        b = []
        associated_entities = associate_entities(a, b, "hamming")
        assert len(associated_entities) == 2
        assert associated_entities[""] is None

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
