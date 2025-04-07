"""Module to parse .vents files to get map callouts."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import cast

import awpy.vector
from awpy.visibility import Triangle, VphysParser
from awpy.volume import VentData, Volume, VolumeDict


class PlantzoneDict(VolumeDict):
    """Typed dictionary for plantzone."""

    designation: str


class BombsiteDesignation(Enum):
    """Enum for bombsite designations."""

    A = "A"
    B = "B"

    @classmethod
    def from_designation_integer(cls, designation: int) -> BombsiteDesignation:
        """Create a designation from the `bomb_site_designation` integer in the entities data.

        Normally, 0 should be A and 1 should be B.
        But sometimes all sites have a designation of 0, then the first one represents A.

        Args:
            designation (int): Value of `bomb_site_designation` in the entities data.

        Raises:
            ValueError: If the designation is not 0 or 1.

        Returns:
            BombsiteDesignation: The BombsiteDesignation enum value.
        """
        match designation:
            case 0:
                return cls.A
            case 1:
                return cls.B
            case _:
                msg = f"Invalid designation integer: {designation}"
                raise ValueError(msg)


@dataclass
class Plantzone(Volume):
    """plantzone."""

    designation: BombsiteDesignation

    def __repr__(self) -> str:
        """String representation of the callout."""
        return f"Plantzone(designation={self.designation}, origin={self.origin}, triangles={len(self.triangles)})"

    def to_dict(self) -> PlantzoneDict:
        """Converts the spawns to a dictionary."""
        return {
            "designation": self.designation.value,
            "inside_point": self.inside_point.to_dict(),
            "origin": self.origin.to_dict(),
            "triangles": [triangle.to_dict() for triangle in self.triangles],
        }

    @staticmethod
    def from_dict(plantzone_dict: PlantzoneDict) -> Plantzone:
        """Convert a dictionary to a Callout object.

        Args:
            plantzone_dict (PlantzoneDict): Dictionary representation of a plantzone.

        Returns:
            Bomnbsite: plantzone object created from the dictionary.
        """
        return Plantzone(
            designation=BombsiteDesignation(plantzone_dict["designation"]),
            origin=awpy.vector.Vector3.from_dict(plantzone_dict["origin"]),
            inside_point=awpy.vector.Vector3.from_dict(plantzone_dict["inside_point"]),
            triangles=[Triangle.from_dict(triangle) for triangle in plantzone_dict["triangles"]],
        )

    @classmethod
    def from_data(cls, vents_data: VentData, phys_blocks: dict[str, str]) -> list[Plantzone]:
        """Parse the content of a vents file into Spawns information.

        Args:
            vents_data (VentData): Data of the the .vents file.
            phys_blocks (dict[str, str]): Extracted PHYS blocks from .vmdl_c files.

        Returns:
            Spawns: A Spawns object with the parsed data.
        """
        plantzones: list[Plantzone] = []
        specified_a = False
        for properties in vents_data.values():
            if properties.get("classname") != "func_bomb_target":
                continue

            designation = (
                BombsiteDesignation.B
                if specified_a
                else BombsiteDesignation.from_designation_integer(properties["bomb_site_designation"])  # pyright: ignore[reportArgumentType]
            )
            if designation == BombsiteDesignation.A:
                specified_a = True
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

            plantzones.append(
                Plantzone(designation=designation, origin=origin, inside_point=inside_point, triangles=triangles)
            )

        return plantzones
