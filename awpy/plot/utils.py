"""Utilities for plotting and visualization."""

import warnings
from typing import Literal

import awpy.data.map_data


# Position function courtesy of PureSkill.gg
def game_to_pixel_axis(map_name: str, position: float, axis: Literal["x", "y"]) -> float:
    """Transforms a CS2-coord value to a pixel-coord in the X or Y-axis.

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
    start = awpy.data.map_data.MAP_DATA[map_name]["pos_" + axis]
    scale = awpy.data.map_data.MAP_DATA[map_name]["scale"]

    if axis == "x":
        return (position - start) / scale
    return (start - position) / scale


def pixel_to_game_axis(map_name: str, position: float, axis: Literal["x", "y"]) -> float:
    """Transforms a pixel-coord value to a CS2-coord in the X or Y-axis.

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
    start = awpy.data.map_data.MAP_DATA[map_name]["pos_" + axis]
    scale = awpy.data.map_data.MAP_DATA[map_name]["scale"]

    if axis == "x":
        return position * scale + start
    return start - position * scale


def game_to_pixel(map_name: str, position: tuple[float, float, float]) -> tuple[float, float, float]:
    """Transforms a `(X, Y, Z)` CS2-coord to pixel coord.

    Args:
        map_name (str): Map to transform coordinates.
        position (tuple): (X,Y,Z) coordinates.

    Returns:
        Tuple[float, float, float]: Transformed coordinates (X,Y,Z).
    """
    return (
        game_to_pixel_axis(map_name, position[0], "x"),
        game_to_pixel_axis(map_name, position[1], "y"),
        position[2],
    )


def pixel_to_game(map_name: str, position: tuple[float, float, float]) -> tuple[float, float, float]:
    """Transforms a `(X, Y, Z)` pixel coord to CS2-coord.

    Args:
        map_name (str): Map to transform coordinates.
        position (tuple): (X,Y,Z) coordinates.

    Returns:
        Tuple[float, float, float]: Transformed coordinates (X,Y,Z).
    """
    return (
        pixel_to_game_axis(map_name, position[0], "x"),
        pixel_to_game_axis(map_name, position[1], "y"),
        position[2],
    )


def is_position_on_lower_level(map_name: str, position: tuple[float, float, float]) -> bool:
    """Check if a position is on a lower level of a map.

    Args:
        map_name (str): Map to check the position level.
        position (Tuple[float, float, float]): (X,Y,Z) coordinates.

    Returns:
        bool: True if the position on the lower level, False otherwise.
    """
    metadata = awpy.data.map_data.MAP_DATA[map_name]
    return position[2] <= metadata["lower_level_max_units"]


def position_transform_axis(map_name: str, position: float, axis: Literal["x", "y"]) -> float:
    """Calls `game_to_pixel_axis` and sends warning.

    This is the old name of function `game_to_pixel_axis`. Please update
    your code to avoid future deprecation.
    """
    warnings.warn(
        (
            "Deprecation warning: Function position_transform_axis() has been "
            "renamed to game_to_pixel_axis(). Please update your code to avoid "
            "future deprecation."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return game_to_pixel_axis(map_name, position, axis)


def position_revert_axis(map_name: str, position: float, axis: Literal["x", "y"]) -> float:
    """Calls `pixel_to_game_axis` and sends warning.

    This is the old name of function `pixel_to_game_axis`. Please update
    your code to avoid future deprecation.
    """
    warnings.warn(
        (
            "Deprecation warning: Function position_revert_axis() has been "
            "renamed to pixel_to_game_axis(). Please update your code to avoid "
            "future deprecation."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return pixel_to_game_axis(map_name, position, axis)


def position_transform(map_name: str, position: tuple[float, float, float]) -> tuple[float, float, float]:
    """Calls `game_to_pixel` and sends warning.

    This is the old name of function `game_to_pixel`. Please update
    your code to avoid future deprecation.
    """
    warnings.warn(
        (
            "Deprecation warning: Function position_transform() has been renamed "
            "to game_to_pixel(). Please update your code to avoid future "
            "deprecation."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return game_to_pixel(map_name, position)


def position_revert(map_name: str, position: tuple[float, float, float]) -> tuple[float, float, float]:
    """Calls `pixel_to_game` and sends warning.

    This is the old name of function `pixel_to_game`. Please update
    your code to avoid future deprecation.
    """
    warnings.warn(
        (
            "Deprecation warning: Function position_revert() has been renamed to "
            "pixel_to_game(). Please update your code to avoid future "
            "deprecation."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return pixel_to_game(map_name, position)
