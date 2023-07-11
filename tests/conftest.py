"""Global test configuration."""
import json
import os

import pytest
import requests


@pytest.fixture(scope="session", autouse=True)
def setup() -> None:  # noqa: PT004
    """Sets up testing environment by downloading demofiles."""
    with open("tests/test_data.json", encoding="utf-8") as f:
        demo_data = json.load(f)
    for file in demo_data:
        _get_demofile(demo_link=demo_data[file]["url"], demo_name=file)


@pytest.fixture(scope="session", autouse=True)
def teardown() -> None:  # noqa: PT004
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    for file in os.listdir():
        if file.endswith(".json"):
            os.remove(file)


def _get_demofile(demo_link: str, demo_name: str) -> None:
    """Sends a request to get a demofile from MediaFire.

    Args:
        demo_link (str): Link to demo.
        demo_name (str): `<file>.dem` styled filename.
    """
    if not os.path.exists(demo_path := f"tests/{demo_name}.dem"):
        r = requests.get(demo_link, timeout=100)
        with open(demo_path, "wb") as demo_file:
            demo_file.write(r.content)
