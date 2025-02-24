"""Simple Vector3 representation to represent 3D points."""

from __future__ import annotations  # Enables postponed evaluation of type hints

from dataclasses import dataclass
from typing import Self, TypedDict

import numpy.typing as npt
from shapely import Point

from awpy.constants import GRAVITY, JUMP_SPEED, RUNNING_SPEED


class Vector3Dict(TypedDict):
    """Typed dictionary for Vector3."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Vector3:
    """A 3D vector representation.

    Attributes:
        x: X coordinate.
        y: Y coordinate.
        z: Z coordinate.
    """

    x: float
    y: float
    z: float

    @classmethod
    def from_input(cls, value: Vector3 | tuple | list | npt.NDArray) -> Vector3:
        """Creates a Vector3 instance from various input types.

        Args:
            value (Vector3 | tuple | list | np.ndarray): Input to be
                coerced into a Vector3.

        Returns:
            Vector3: A Vector3 instance.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, tuple | list) and len(value) == 3:
            return cls(*value)
        if isinstance(value, npt.NDArray) and value.shape == (3,):
            return cls(*value.tolist())
        erroneous_input_msg = "Input must be a Vector3, tuple, list of length 3, or a numpy array of shape (3,)"
        raise ValueError(erroneous_input_msg)

    def __sub__(self, other: Vector3) -> Vector3:
        """Subtract two vectors."""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: Vector3) -> Vector3:
        """Add two vectors."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def dot(self, other: Vector3) -> float:
        """Compute dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        """Compute cross product."""
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def distance(self, other: Vector3) -> float:
        """Compute distance between two vectors."""
        return (self - other).length()

    def distance_2d(self, other: Vector3) -> float:
        """Compute 2D distance between two vectors."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def length(self) -> float:
        """Compute vector length."""
        return (self.x * self.x + self.y * self.y + self.z * self.z) ** 0.5

    def normalize(self) -> Vector3:
        """Return normalized vector."""
        length = self.length()
        if length == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / length, self.y / length, self.z / length)

    def to_dict(self) -> Vector3Dict:
        """Convert Vector3 to dictionary."""
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: Vector3Dict) -> Vector3:
        """Create a Vector3 instance from a dictionary."""
        return cls(data["x"], data["y"], data["z"])

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert Vector3 to tuple."""
        return (self.x, self.y, self.z)

    def to_tuple_2d(self) -> tuple[float, float]:
        """Convert Vector3 to 2D-tuple."""
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, data: tuple[float, float, float]) -> Self:
        """Create a Vector3 instance from a tuple."""
        return cls(data[0], data[1], data[2])

    def to_point(self) -> Point:
        """Convert Vector3 to 3D-Point."""
        return Point(self.x, self.y, self.z)

    def to_point_2d(self) -> Point:
        """Convert Vector3 to 2D-Point."""
        return Point(self.x, self.y)

    def can_jump_to(self, other: Vector3) -> bool:
        """Check if a jump is possible between two points."""
        h_distance = self.distance_2d(other)
        if h_distance <= 0:
            return True

        # Time to travel the horizontal distance between self and other
        # with running speed
        t = h_distance / RUNNING_SPEED
        # In my jump, at which height am i when i reach the desitantion x-y distance.
        z_at_dest = self.z + JUMP_SPEED * t - 0.5 * GRAVITY * t * t

        # Am i at or above my target height?
        return z_at_dest >= other.z
