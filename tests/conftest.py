"""Awpy test configuration."""

import json
import os
import pathlib

import pytest
import requests

import awpy.demo


@pytest.fixture(scope="session", autouse=True)
def setup():  # noqa: ANN201
    """Sets up testing environment by downloading demofiles."""
    with open("tests/test_data.json", encoding="utf-8") as test_data_file:
        test_data = json.load(test_data_file)
    for file_id in test_data:
        path = pathlib.Path(f"tests/{file_id}{test_data[file_id]['extension']}")
        if not path.exists():
            _get_test_file(url=test_data[file_id]["url"], path=path)


@pytest.fixture(scope="session", autouse=True)
def teardown():  # noqa: ANN201
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    for file in os.listdir():
        if file.endswith((".json", ".dem", ".zip", ".nav")):
            os.remove(file)


@pytest.fixture(scope="session")
def parsed_hltv_demo() -> awpy.demo.Demo:
    """Fixture that returns a parsed HLTV Demo object.

    https://www.hltv.org/matches/2378917/vitality-vs-spirit-iem-katowice-2025
    """
    dem = awpy.demo.Demo(path="tests/vitality-vs-spirit-m2-nuke.dem")
    dem.parse()
    return dem


@pytest.fixture(scope="session")
def parsed_faceit_demo() -> awpy.demo.Demo:
    """Fixture that returns a parsed FACEIT Demo object.

    https://www.faceit.com/en/cs2/room/1-efdaace4-2fd4-4884-babf-1a5a2c83e344
    """
    dem = awpy.demo.Demo(path="tests/1-efdaace4-2fd4-4884-babf-1a5a2c83e344.dem")
    dem.parse()
    return dem


@pytest.fixture(scope="session")
def parsed_mm_demo() -> awpy.demo.Demo:
    """Fixture that returns a parsed Matchmaking Demo object.

    https://csstats.gg/match/249286425
    """
    dem = awpy.demo.Demo(path="tests/match730_003736456444682174484_1173793269_201.dem")
    dem.parse()
    return dem


def _get_test_file(url: str, path: pathlib.Path) -> None:
    """Sends a request to get a demofile from the object storage.

    Args:
        url (str): Link to demo.
        path (pathlib.Path): Filepath to write.
    """
    if not path.exists():
        request = requests.get(url, timeout=100)
        with open(path, "wb") as demo_file:
            demo_file.write(request.content)
