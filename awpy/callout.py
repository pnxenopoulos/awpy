"""Module to parse .vents files to get map spawns."""

from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass
from functools import cached_property
from typing import TypedDict, cast

import awpy.vector
from awpy.spawn import parse_vents_file_to_dict
from awpy.visibility import Triangle, VisibilityChecker, VphysParser


class CalloutDict(TypedDict):
    """Typed dictionary for callout."""

    callout: str
    inside_point: awpy.vector.Vector3Dict
    origin: awpy.vector.Vector3Dict
    triangles: list[dict[str, awpy.vector.Vector3Dict]]


@dataclass
class Callout:
    """Callout."""

    callout: str
    inside_point: awpy.vector.Vector3
    origin: awpy.vector.Vector3
    triangles: list[Triangle]

    def __repr__(self) -> str:
        """String representation of the callout."""
        return f"Callout(callout={self.callout}, origin={self.origin}, triangles={len(self.triangles)})"

    @cached_property
    def collision_checker(self) -> VisibilityChecker:
        """Visibility checker for the callout."""
        return VisibilityChecker(triangles=self.triangles)

    def to_dict(self) -> CalloutDict:
        """Converts the spawns to a dictionary."""
        return {
            "callout": self.callout,
            "inside_point": self.inside_point.to_dict(),
            "origin": self.origin.to_dict(),
            "triangles": [triangle.to_dict() for triangle in self.triangles],
        }

    def to_json(self, path: str | pathlib.Path) -> None:
        """Writes the callout data to a JSON file.

        Args:
            path: Path to the JSON file to write.
        """
        callout_dict = self.to_dict()
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(callout_dict, json_file)
            json_file.write("\n")

    @staticmethod
    def callout_from_position(player_pos: awpy.vector.Vector3, places: list[Callout]) -> str | None:
        """Get the callout from a position.

        Args:
            player_pos (awpy.vector.Vector3): The position of the player.
            places (list[Callout]): The list of callouts to check against.
        """
        for place in places:
            if place.collision_checker.is_visible(player_pos, place.inside_point):
                return place.callout
        return None

    @staticmethod
    def extract_phys_blocks(content: str) -> dict[str, str]:
        """Extracts the PHYS blocks from the given content.

        Extract a mapping of file name to PHYS block from the output of
        ./Source2Viewer-CLI.exe -i $filePath -e "vmdl_c" -f "maps/MAP_NAME/entities/" --block "PHYS" 2>&1

        Args:
            content (str): The content of the file.
        """
        phys_blocks = {}

        # Match file entries like: [2/73] maps/de_anubis/entities/unnamed_2_20341.vmdl_c
        file_entry_pattern = re.compile(r"\[\d+/\d+\]\s+([\w/.-]+)")

        # Match the PHYS block, ensuring it starts with `{` on a new line and ends with `}` on a new line.
        # This regex handles nested braces properly by matching balanced opening and closing braces.
        phys_pattern = re.compile(r"--- Data for block \"PHYS\" ---\n.*?\n(^\{$\n.*?^\}$)", re.DOTALL | re.MULTILINE)

        # Find all file entries and PHYS blocks
        file_entries = list(file_entry_pattern.finditer(content))
        phys_blocks_iter = phys_pattern.finditer(content)
        file_index = 0  # Pointer to the first list (matches_first)
        for phys_match in phys_blocks_iter:
            while file_index < len(file_entries) and file_entries[file_index].start() < phys_match.start():
                file_index += 1
            if file_index > 0:
                filename = file_entries[file_index - 1].group(1)
                filestem = pathlib.Path(filename.replace("\\", "/")).stem
                phys_blocks[filestem] = phys_match.group(1)

        return phys_blocks

    @staticmethod
    def from_data(vents_file: str | pathlib.Path, models_file: pathlib.Path) -> list[Callout]:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_file (str | pathlib.Path): The path to the .vents file.
            models_file (pathlib.Path): The path to the output of extracting the PHYS blocks from .vmdl_c files.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
        vents_data = parse_vents_file_to_dict(pathlib.Path(vents_file).read_text())
        phys_blocks = Callout.extract_phys_blocks(pathlib.Path(models_file).read_text())

        callouts: list[Callout] = []
        for properties in vents_data.values():
            if properties.get("classname") != "env_cs_place":
                continue

            callout_name: str = properties["place_name"]  # pyright: ignore[reportAssignmentType]
            x, y, z = properties["origin"]  # pyright: ignore[reportGeneralTypeIssues]
            origin = awpy.vector.Vector3(x=x, y=y, z=z)  # pyright: ignore[reportArgumentType]

            model_name = cast("str", properties.get("model", "")).replace("\\", "/")
            model = pathlib.Path(model_name).stem

            # Get the PHYS block for this callout
            phys_block = phys_blocks.get(model)
            if not phys_block:
                continue

            triangles: list[Triangle] = VphysParser(
                vphys_file=None, vphys_data=phys_block, include_everything=True
            ).triangles

            triangles = [
                Triangle(p1=triangle.p1 + origin, p2=triangle.p2 + origin, p3=triangle.p3 + origin)
                for triangle in triangles
            ]

            inside_point = sum(
                (triangle.p1 + triangle.p2 + triangle.p3 for triangle in triangles), awpy.vector.Vector3(0, 0, 0)
            ) / (3 * len(triangles))

            callouts.append(
                Callout(callout=callout_name, origin=origin, inside_point=inside_point, triangles=triangles)
            )

        return callouts

    @staticmethod
    def multiple_to_json(callouts: list[Callout], path: str | pathlib.Path) -> None:
        """Write multiple callouts to a JSON file.

        Args:
            callouts (list[Callout]): List of Callout objects to write to JSON.
            path (str | pathlib.Path): Path to the JSON file to write.
        """
        callouts_list = [callout.to_dict() for callout in callouts]
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(callouts_list, json_file)
            json_file.write("\n")

    @staticmethod
    def from_dict(callout_dict: CalloutDict) -> Callout:
        """Convert a dictionary to a Callout object.

        Args:
            callout_dict (CalloutDict): Dictionary representation of a Callout.

        Returns:
            Callout: Callout object created from the dictionary.
        """
        return Callout(
            callout=callout_dict["callout"],
            origin=awpy.vector.Vector3.from_dict(callout_dict["origin"]),
            inside_point=awpy.vector.Vector3.from_dict(callout_dict["inside_point"]),
            triangles=[Triangle.from_dict(triangle) for triangle in callout_dict["triangles"]],
        )

    @staticmethod
    def multiple_from_json(path: str | pathlib.Path) -> list[Callout]:
        """Read multiple callouts from a JSON file.

        Args:
            path (str | pathlib.Path): Path to the JSON file to read.

        Returns:
            list[Callout]: List of Callout objects read from the JSON file.
        """
        with open(path, encoding="utf-8") as json_file:
            callouts_list = json.load(json_file)
            return [Callout.from_dict(callout) for callout in callouts_list]
