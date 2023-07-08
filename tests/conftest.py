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


@pytest.fixture(scope="session")
def teardown() -> None:  # noqa: PT004
    """Cleans testing environment by deleting all .dem and .json files."""
    yield
    files_in_directory = os.listdir()
    if filtered_files := [
        file for file in files_in_directory if file.endswith((".dem", ".json"))
    ]:
        for f in filtered_files:
            os.remove(f)


def _get_demofile(demo_link: str, demo_name: str) -> None:
    """Sends a request to get a demofile from MediaFire.

    Args:
        demo_link (str): Link to demo.
        demo_name (str): `<file>.dem` styled filename.
    """
    if os.path.exists(f"tests/{demo_name}.dem"):
        pass
    else:
        r = requests.get(demo_link, timeout=100)
        with open(f"tests/{demo_name}.dem", "wb") as demo_file:
            demo_file.write(r.content)
