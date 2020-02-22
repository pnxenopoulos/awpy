import pytest

from csgo.parser.match_parser import CSGOMatchParser

def test_parser_error():
    """ Tests if the parser encountered a corrupted demofile. If it did, the
    parser would set the `demo_error` attribute to True. Since this demofile is
    not corrupted, this test should have parser.demo_error as FALSE
    """
    parser = CSGOMatchParser(demofile="avant-vs-formidable-dust2.dem",competition_name="ESEA-MDL-Season-33-Australia", match_name="AVANT-v-Formidable")
    parser.parse_demofile()
    assert not parser.demo_error
