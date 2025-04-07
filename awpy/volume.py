"""Module to parse .vents files to get map volumes."""

from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Self, TypedDict

import awpy.vector
from awpy.visibility import Triangle, VisibilityChecker

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


class VolumeDict(TypedDict):
    """Typed dictionary for callout."""

    inside_point: awpy.vector.Vector3Dict
    origin: awpy.vector.Vector3Dict
    triangles: list[dict[str, awpy.vector.Vector3Dict]]


@dataclass
class Volume:
    """Base class for other CS2 volumes.

    Examples include callouts, bombsites, buyzones.
    """

    inside_point: awpy.vector.Vector3
    origin: awpy.vector.Vector3
    triangles: list[Triangle]

    @cached_property
    def collision_checker(self) -> VisibilityChecker:
        """Visibility checker for the callout."""
        return VisibilityChecker(triangles=self.triangles)

    @staticmethod
    def get_inside_point(triangles: list[Triangle]) -> awpy.vector.Vector3:
        """Get a point inside a volume bound by triangles."""
        return sum(
            (triangle.p1 + triangle.p2 + triangle.p3 for triangle in triangles), awpy.vector.Vector3(0, 0, 0)
        ) / (3 * len(triangles))

    def to_dict(self) -> VolumeDict:
        """Converts the spawns to a dictionary."""
        return {
            "inside_point": self.inside_point.to_dict(),
            "origin": self.origin.to_dict(),
            "triangles": [triangle.to_dict() for triangle in self.triangles],
        }

    @classmethod
    def from_dict(cls, callout_dict: VolumeDict) -> Self:
        """Convert a dictionary to a Callout object.

        Args:
            callout_dict (CalloutDict): Dictionary representation of a Callout.

        Returns:
            Callout: Callout object created from the dictionary.
        """
        return cls(
            origin=awpy.vector.Vector3.from_dict(callout_dict["origin"]),
            inside_point=awpy.vector.Vector3.from_dict(callout_dict["inside_point"]),
            triangles=[Triangle.from_dict(triangle) for triangle in callout_dict["triangles"]],
        )

    def to_json(self, path: str | pathlib.Path) -> None:
        """Writes the callout data to a JSON file.

        Args:
            path: Path to the JSON file to write.
        """
        callout_dict = self.to_dict()
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(callout_dict, json_file)
            json_file.write("\n")

    @classmethod
    def multiple_to_json(cls, volumes: Iterable[Volume], /, path: str | pathlib.Path) -> None:
        """Write multiple callouts to a JSON file.

        Args:
            volumes (Iterable[Volume]): List of Callout objects to write to JSON.
            path (str | pathlib.Path): Path to the JSON file to write.
        """
        callouts_list = [volume.to_dict() for volume in volumes]
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(callouts_list, json_file)
            json_file.write("\n")

    @classmethod
    def multiple_from_json(cls, path: str | pathlib.Path) -> Sequence[Self]:
        """Read multiple callouts from a JSON file.

        Args:
            path (str | pathlib.Path): Path to the JSON file to read.

        Returns:
            list[Callout]: List of Callout objects read from the JSON file.
        """
        with open(path, encoding="utf-8") as json_file:
            callouts_list = json.load(json_file)
            return [cls.from_dict(callout) for callout in callouts_list]


VentsValue = str | int | float | bool | tuple[float, ...]

VentData = dict[int, dict[str, VentsValue]]


def parse_vents_file_to_dict(file_content: str) -> VentData:
    """Parse the content of a .vents file into a dictionary.

    Args:
        file_content (str): The content of the .vents file.

    Returns:
        dict[int, dict[str, VentsValue]]: A dictionary with the parsed data.
    """
    # Dictionary to hold parsed data
    parsed_data: VentData = {}
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


def extract_phys_blocks(content: str) -> dict[str, str]:
    """Extracts the PHYS blocks from the given content.

    Extract a mapping of file name to PHYS block from the output of
    ./Source2Viewer-CLI.exe -i $filePath -e "vmdl_c" -f "maps/MAP_NAME/entities/" --block "PHYS" 2>&1

    Args:
        content (str): The content of the file.
    """
    phys_blocks: dict[str, str] = {}

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
