"""Awpy test configuration."""

import json
import os
import pathlib

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def setup():  # noqa: ANN201
    """Sets up testing environment by downloading demofiles."""
    with open("tests/test_data.json", encoding="utf-8") as file:
        test_data = json.load(file)
    for file_id in test_data:
        path = pathlib.Path(f"tests/{file_id}{test_data[file]['extension']}")
        if not path.exists():
            _get_test_file(url=test_data[file_id]["url"], path=path)


@pytest.fixture(scope="session", autouse=True)
def teardown():  # noqa: ANN201
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    for file in os.listdir():
        if file.endswith((".json", ".dem", ".zip", ".nav")):
            os.remove(file)


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
