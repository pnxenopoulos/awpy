"""Module to parse .vents files to get map spawns."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import awpy.vector

VentsValue = str | int | float | bool | tuple[float, ...]


@dataclass
class Spawns:
    """Spawns of a map."""

    CT: list[awpy.vector.Vector3]
    T: list[awpy.vector.Vector3]

    def to_dict(self) -> dict[str, list[dict[str, float]]]:
        """Converts the spawns to a dictionary."""
        return {
            "CT": [{"x": ct.x, "y": ct.y, "z": ct.z} for ct in self.CT],
            "T": [{"x": t.x, "y": t.y, "z": t.z} for t in self.T],
        }

    def to_json(self, path: str | pathlib.Path) -> None:
        """Writes the spawns data to a JSON file.

        Args:
            path: Path to the JSON file to write.
        """
        spawns_dict = self.to_dict()
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(spawns_dict, json_file)
            json_file.write("\n")

    @staticmethod
    def from_vents_content(vents_content: str) -> Spawns:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_content (str): The content of the .vents file.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
        parsed_data = parse_vents_file_to_dict(vents_content)

        return filter_vents_data(parsed_data)

    @staticmethod
    def from_vents_file(vents_file: str | pathlib.Path) -> Spawns:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_file (str | pathlib.Path): The path to the .vents file.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
        with open(vents_file) as f:
            return Spawns.from_vents_content(f.read())


def parse_vents_file_to_dict(file_content: str) -> dict[int, dict[str, VentsValue]]:
    """Parse the content of a .vents file into a dictionary.

    Args:
        file_content (str): The content of the .vents file.

    Returns:
        dict[int, dict[str, VentsValue]]: A dictionary with the parsed data.
    """
    # Dictionary to hold parsed data
    parsed_data: dict[int, dict[str, VentsValue]] = {}
    block_id = 0
    block_content: dict[str, VentsValue] = {}

    for line in file_content.splitlines():
        if match := re.match(r"^====(\d+)====$", line):
            block_id = int(match.group(1))
            block_content = {}
            continue

        if not line.strip():
            continue
        try:
            key, value = line.split(maxsplit=1)
        except Exception as _e:  # noqa: S112
            continue
        key = key.strip()
        value = value.strip()

        # Attempt to parse the value
        if value in ("True", "False"):
            value = value == "True"  # Convert to boolean
        elif re.match(r"^-?\d+$", value):
            value = int(value)  # Convert to integer
        elif re.match(r"^-?\d*\.\d+$", value):
            value = float(value)  # Convert to float
        elif re.match(r"^-?\d*\.\d+(?:\s-?\d*\.\d+)+$", value):
            value = tuple(map(float, value.split()))  # Convert to tuple of floats

        block_content[key] = value

        parsed_data[block_id] = block_content

    return parsed_data


def filter_vents_data(data: dict[int, dict[str, VentsValue]]) -> Spawns:
    """Filter the data to get the positions."""
    ct_spawns: list[awpy.vector.Vector3] = []
    t_spawns: list[awpy.vector.Vector3] = []

    for properties in data.values():
        if (
            properties.get("classname") == "info_player_terrorist"
            and properties.get("enabled")
            and properties.get("priority") == 0
        ):
            x, y, z = properties["origin"]
            t_spawns.append(awpy.vector.Vector3(x=x, y=y, z=z))
        elif (
            properties.get("classname") == "info_player_counterterrorist"
            and properties.get("enabled")
            and properties.get("priority") == 0
        ):
            x, y, z = properties["origin"]
            ct_spawns.append(awpy.vector.Vector3(x=x, y=y, z=z))

    return Spawns(CT=ct_spawns, T=t_spawns)
