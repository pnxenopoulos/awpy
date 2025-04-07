"""Module to parse .vents files to get map callouts."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import cast

import awpy.vector
from awpy.visibility import Triangle, VphysParser
from awpy.volume import VentData, Volume, VolumeDict


class BuyzoneDict(VolumeDict):
    """Typed dictionary for Buyzone."""

    associated_team: str


class AssociatedTeam(Enum):
    """Enum for Buyzone designations."""

    CT = "CT"
    T = "T"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_teamnum_integer(cls, teamnum: int) -> AssociatedTeam:
        """Create a designation from the `teamnum` integer in the entities data.

        Normally, 3 should be CT and 2 should be T.

        Args:
            teamnum (int): Value of `teamnum` in the entities data.

        Raises:
            ValueError: If the teamnum is not 2 or 3.

        Returns:
            BuyzoneDesignation: The BuyzoneDesignation enum value.
        """
        match teamnum:
            case 3:
                return cls.CT
            case 2:
                return cls.T
            case _:
                return cls.UNKNOWN


@dataclass
class Buyzone(Volume):
    """Buyzone."""

    associated_team: AssociatedTeam

    def __repr__(self) -> str:
        """String representation of the callout."""
        return f"Buyzone(associated_team={self.associated_team}, origin={self.origin}, triangles={len(self.triangles)})"

    def to_dict(self) -> BuyzoneDict:
        """Converts the spawns to a dictionary."""
        return {
            "associated_team": self.associated_team.value,
            "inside_point": self.inside_point.to_dict(),
            "origin": self.origin.to_dict(),
            "triangles": [triangle.to_dict() for triangle in self.triangles],
        }

    @staticmethod
    def from_dict(buyzone_dict: BuyzoneDict) -> Buyzone:
        """Convert a dictionary to a Callout object.

        Args:
            buyzone_dict (BuyzoneDict): Dictionary representation of a Buyzone.

        Returns:
            Bomnbsite: Buyzone object created from the dictionary.
        """
        return Buyzone(
            associated_team=AssociatedTeam(buyzone_dict["associated_team"]),
            origin=awpy.vector.Vector3.from_dict(buyzone_dict["origin"]),
            inside_point=awpy.vector.Vector3.from_dict(buyzone_dict["inside_point"]),
            triangles=[Triangle.from_dict(triangle) for triangle in buyzone_dict["triangles"]],
        )

    @classmethod
    def from_data(cls, vents_data: VentData, phys_blocks: dict[str, str]) -> list[Buyzone]:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_data (VentData): Data of the the .vents file.
            phys_blocks (dict[str, str]): Extracted PHYS blocks from .vmdl_c files.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
        buyzones: list[Buyzone] = []
        for properties in vents_data.values():
            if properties.get("classname") != "func_buyzone" or "2v2" in properties.get("targetname", ""):  # pyright: ignore[reportOperatorIssue]
                continue

            associated_team = AssociatedTeam.from_teamnum_integer(properties["teamnum"])  # pyright: ignore[reportArgumentType]
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

            buyzones.append(
                Buyzone(associated_team=associated_team, origin=origin, inside_point=inside_point, triangles=triangles)
            )

        return buyzones
