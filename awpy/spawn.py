"""Module to parse .vents files to get map spawns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from awpy.volume import VentData, parse_vents_file_to_dict

if TYPE_CHECKING:
    import pathlib

import awpy.vector


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


def filter_vents_data(data: VentData) -> Spawns:
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
