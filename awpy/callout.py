"""Module to parse .vents files to get map callouts."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Self, cast

import awpy.vector
from awpy.visibility import Triangle, VphysParser
from awpy.volume import VentData, Volume, VolumeDict


class CalloutDict(VolumeDict):
    """Typed dictionary for callout."""

    callout: str


@dataclass
class Callout(Volume):
    """Callout."""

    callout: str

    def __repr__(self) -> str:
        """String representation of the callout."""
        return f"Callout(callout={self.callout}, origin={self.origin}, triangles={len(self.triangles)})"

    def to_dict(self) -> CalloutDict:
        """Converts the spawns to a dictionary."""
        return {
            "callout": self.callout,
            "inside_point": self.inside_point.to_dict(),
            "origin": self.origin.to_dict(),
            "triangles": [triangle.to_dict() for triangle in self.triangles],
        }

    @classmethod
    def from_dict(cls, callout_dict: CalloutDict) -> Self:
        """Convert a dictionary to a Callout object.

        Args:
            callout_dict (CalloutDict): Dictionary representation of a Callout.

        Returns:
            Callout: Callout object created from the dictionary.
        """
        return cls(
            callout=callout_dict["callout"],
            origin=awpy.vector.Vector3.from_dict(callout_dict["origin"]),
            inside_point=awpy.vector.Vector3.from_dict(callout_dict["inside_point"]),
            triangles=[Triangle.from_dict(triangle) for triangle in callout_dict["triangles"]],
        )

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

    @classmethod
    def from_data(cls, vents_data: VentData, phys_blocks: dict[str, str]) -> list[Callout]:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_data (VentData): Data of the the .vents file.
            phys_blocks (dict[str, str]): Extracted PHYS blocks from .vmdl_c files.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
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

            inside_point = cls.get_inside_point(triangles)

            callouts.append(
                Callout(callout=callout_name, origin=origin, inside_point=inside_point, triangles=triangles)
            )

        return callouts
