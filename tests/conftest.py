"""Awpy test configuration."""

import json
import os

import pytest
import requests

from loguru import logger


@pytest.fixture(scope="session", autouse=True)
def setup():  # noqa: PT004, ANN201
    """Sets up testing environment by downloading demofiles."""
    with open("tests/test_data.json", encoding="utf-8") as file:
        demo_data = json.load(file)
    for file in demo_data:
        if file not in os.listdir("tests"):
            dl_demo_msg = f"Downloading {file}.dem..."
            logger.debug(dl_demo_msg)
            _get_demofile(demo_link=demo_data[file]["url"], demo_name=file)


@pytest.fixture(scope="session", autouse=True)
def teardown():  # noqa: PT004, ANN201
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    for file in os.listdir():
        if file.endswith((".json", ".dem", ".zip")):
            os.remove(file)


def _get_demofile(demo_link: str, demo_name: str) -> None:
    """Sends a request to get a demofile from the object storage.

    Args:
        demo_link (str): Link to demo.
        demo_name (str): `<file>.dem` styled filename.
    """
    if not os.path.exists(demo_path := f"tests/{demo_name}.dem"):
        request = requests.get(demo_link, timeout=100)
        with open(demo_path, "wb") as demo_file:
            demo_file.write(request.content)
