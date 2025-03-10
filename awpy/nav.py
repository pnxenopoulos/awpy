"""Module to parse and represent navigation mesh files.

Reference: https://github.com/ValveResourceFormat/ValveResourceFormat/tree/master/ValveResourceFormat/NavMesh
"""

from enum import Enum
from typing import TypedDict

from cs2_nav import DynamicAttributeFlags, Nav, NavArea  # noqa: F401

from awpy.vector import Vector3Dict


class NavDirectionType(Enum):
    """Enumeration for navigation directions."""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class NavAreaDict(TypedDict):
    """Typed dict representation of a NavArea."""

    area_id: int
    hull_index: int
    dynamic_attribute_flags: int
    corners: list[Vector3Dict]
    connections: list[int]
    ladders_above: list[int]
    ladders_below: list[int]


class NavDict(TypedDict):
    """Typed dict representation of a Nav."""

    version: int
    sub_version: int
    is_analyzed: bool
    areas: dict[int, NavAreaDict]
