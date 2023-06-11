import pytest
import json
import requests
import os


@pytest.fixture(scope="session")
def setup():
    with open("tests/test_data.json", encoding="utf-8") as f:
        demo_data = json.load(f)
    for file in demo_data:
        _get_demofile(demo_link=demo_data[file]["url"], demo_name=file)


@pytest.fixture(scope="session", autouse=True)
def teardown():
    files_in_directory = os.listdir()
    if filtered_files := [
        file for file in files_in_directory if file.endswith((".dem", ".json"))
    ]:
        for f in filtered_files:
            os.remove(f)


def _get_demofile(demo_link: str, demo_name: str) -> None:
    print(f"Requesting {demo_link}")
    r = requests.get(demo_link, timeout=100)
    with open(f"{demo_name}.dem", "wb") as demo_file:
        demo_file.write(r.content)


def _delete_demofile(demo_name: str) -> None:
    print(f"Removing {demo_name}")
    os.remove(f"{demo_name}.dem")
