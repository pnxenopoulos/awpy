import pytest

from csgo.parser.match_parser import CSGOMatchParser

def test_parser_error():
    parser = CSGOMatchParser(demofile="avant-vs-formidable-dust2.dem",competition_name="ESEA-MDL-Season-33-Australia", match_name="AVANT-v-Formidable")
    parser.parse_demofile()
    assert not parser.demo_error
