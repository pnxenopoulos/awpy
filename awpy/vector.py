"""Simple Vector3 representation."""

from __future__ import annotations  # Enables postponed evaluation of type hints

from dataclasses import dataclass

import numpy.typing as npt


@dataclass
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
        erroneous_input_msg = "Input must be a Vector3, tuple, list of length 3, or a numpy array of shape (3,)"  # noqa: E501
        raise ValueError(erroneous_input_msg)
