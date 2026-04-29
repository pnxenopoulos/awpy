"""Module to parse .vents files to get map spawns."""

from __future__ import annotations

import itertools
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
        with open(vents_file, encoding="utf-8") as f:
            return Spawns.from_vents_content(f.read())


@dataclass
class SpawnPoint:
    """Representation of the relevant information for spawn points."""

    priority: int
    origin: awpy.vector.Vector3

    @staticmethod
    def collect_by_priority(spawn_points: list[SpawnPoint], *, n: int = 5) -> list[SpawnPoint]:
        """Collects the spawn points with the highest priority.

        Args:
            spawn_points (list[SpawnPoint]): List of spawn points.
            n (int, optional): Number of spawn points to collect. Defaults to 5.

        Returns:
            list[SpawnPoint]: List of the spawn points with the highest priority.
        """
        spawn_points_sorted = sorted(spawn_points, key=lambda sp: sp.priority)

        collected: list[SpawnPoint] = []
        for _priority, group in itertools.groupby(spawn_points_sorted, key=lambda sp: sp.priority):
            collected.extend(list(group))
            if len(collected) >= n:
                break
        return collected


def filter_vents_data(data: VentData) -> Spawns:
    """Filter the data to get the positions."""
    ct_candidates: list[SpawnPoint] = []
    t_candidates: list[SpawnPoint] = []

    for properties in data.values():
        if properties.get("classname") == "info_player_terrorist" and properties.get("enabled"):
            x, y, z = properties["origin"]
            t_candidates.append(SpawnPoint(priority=properties["priority"], origin=awpy.vector.Vector3(x=x, y=y, z=z)))
        elif properties.get("classname") == "info_player_counterterrorist" and properties.get("enabled"):
            x, y, z = properties["origin"]
            ct_candidates.append(SpawnPoint(priority=properties["priority"], origin=awpy.vector.Vector3(x=x, y=y, z=z)))

    ct_spawns = [spawn.origin for spawn in SpawnPoint.collect_by_priority(ct_candidates, n=5)]
    t_spawns = [spawn.origin for spawn in SpawnPoint.collect_by_priority(t_candidates, n=5)]

    return Spawns(CT=ct_spawns, T=t_spawns)
