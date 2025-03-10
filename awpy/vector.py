"""Simple Vector3 representation to represent 3D points."""

from __future__ import annotations  # Enables postponed evaluation of type hints

from typing import TypedDict

from cs2_nav import Position as Vector3  # noqa: F401


class Vector3Dict(TypedDict):
    """Typed dictionary for Vector3."""

    x: float
    y: float
    z: float
