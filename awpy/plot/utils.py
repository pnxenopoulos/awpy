"""Utilities for plotting and visualization."""

from typing import Literal

from awpy.data.map_data import MAP_DATA


# Position function courtesy of PureSkill.gg
def position_transform_axis(
    map_name: str, position: float, axis: Literal["x", "y"]
) -> float:
    """Transforms an X or Y-axis value. CS2 coordinate -> Minimap image pixel value.

    Args:
        map_name (str): Map to search
        position (float): X or Y coordinate
        axis (str): Either "x" or "y"

    Returns:
        float: Transformed position

    Raises:
        ValueError: Raises a ValueError if axis not 'x' or 'y'
    """
    axis = axis.lower()
    if axis not in ["x", "y"]:
        msg = f"'axis' has to be 'x' or 'y', not {axis}"
        raise ValueError(msg)
    start = MAP_DATA[map_name]["pos_" + axis]
    scale = MAP_DATA[map_name]["scale"]

    if axis == "x":
        return (position - start) / scale
    return (start - position) / scale


def position_revert_axis(
    map_name: str, position: float, axis: Literal["x", "y"]
) -> float:
    """Reverts an X or Y-axis value. Minimap image pixel value -> CS2 coordinate.

    Args:
        map_name (str): Map to search
        position (float): X or Y coordinate
        axis (str): Either "x" or "y"

    Returns:
        float: Transformed position

    Raises:
        ValueError: Raises a ValueError if axis not 'x' or 'y'
    """
    axis = axis.lower()
    if axis not in ["x", "y"]:
        msg = f"'axis' has to be 'x' or 'y', not {axis}"
        raise ValueError(msg)
    start = MAP_DATA[map_name]["pos_" + axis]
    scale = MAP_DATA[map_name]["scale"]

    if axis == "x":
        # return (position - start) / scale
        return position * scale + start
    # return (start - position) / scale
    return start - position * scale


def position_transform(
    map_name: str, position: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Transforms an single coordinate (X,Y,Z). CS2 coordinates -> Minimap image pixel values.

    Args:
        map_name (str): Map to transform coordinates.
        position (tuple): (X,Y,Z) coordinates.

    Returns:
        Tuple[float, float, float]: Transformed coordinates (X,Y,Z).
    """
    return (
        position_transform_axis(map_name, position[0], "x"),
        position_transform_axis(map_name, position[1], "y"),
        position[2],
    )


def position_revert(
    map_name: str, position: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Transforms an single coordinate (X,Y,Z). Minimap image pixel values -> CS2 coordinates.

    Args:
        map_name (str): Map to transform coordinates.
        position (tuple): (X,Y,Z) coordinates.

    Returns:
        Tuple[float, float, float]: Transformed coordinates (X,Y,Z).
    """
    return (
        position_revert_axis(map_name, position[0], "x"),
        position_revert_axis(map_name, position[1], "y"),
        position[2],
    )


def is_position_on_lower_level(
    map_name: str, position: tuple[float, float, float]
) -> bool:
    """Check if a position is on a lower level of a map.

    Args:
        map_name (str): Map to check the position level.
        position (Tuple[float, float, float]): (X,Y,Z) coordinates.

    Returns:
        bool: True if the position on the lower level, False otherwise.
    """
    metadata = MAP_DATA[map_name]
    if position[2] <= metadata["lower_level_max"]:
        return True
    return False
