"""Awpy test configuration."""

import json
import os
from pathlib import Path

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def setup():  # noqa: PT004, ANN201
    """Sets up testing environment by downloading demofiles."""
    with Path("tests/test_data.json").open(encoding="utf-8") as file:
        demo_data = json.load(file)
    for file in demo_data:
        if file not in os.listdir("tests"):
            _get_demofile(demo_link=demo_data[file]["url"], demo_name=file)


@pytest.fixture(scope="session", autouse=True)
def teardown():  # noqa: PT004, ANN201
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    for file in os.listdir():
        if file.endswith((".json", ".dem", ".zip")):
            Path(file).unlink()


def _get_demofile(demo_link: str, demo_name: str) -> None:
    """Sends a request to get a demofile from the object storage.

    Args:
        demo_link (str): Link to demo.
        demo_name (str): `<file>.dem` styled filename.
    """
    if not (demo_path := Path(f"tests/{demo_name}.dem")).exists():
        request = requests.get(demo_link, timeout=100)
        with demo_path.open("wb") as demo_file:
            demo_file.write(request.content)
