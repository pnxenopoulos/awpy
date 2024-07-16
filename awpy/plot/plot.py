"""Module for plotting Counter-Strike data."""

import importlib.resources
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from awpy.plot.utils import position_transform_axis

# Define preset settings
PRESET_MARKERS = {
    "default": {
        "marker": "o",
        "color": "cyan",
        "markersize": 7,
        "linewidth": 2,
        "alpha": 0.8,
    },
    "player_ct": {
        "marker": "o",
        "color": "#5d79ae",
        "markersize": 10,
        "linewidth": 2,
        "alpha": 0.8,
    },
    "player_t": {
        "marker": "o",
        "color": "#de9b35",
        "markersize": 10,
        "linewidth": 2,
        "alpha": 0.8,
    },
    "bomb": {
        "marker": "x",
        "color": "brown",
        "markersize": 7,
        "linewidth": 2,
        "alpha": 0.8,
    },
    "smoke": {
        "marker": "o",
        "color": "gray",
        "markersize": 16,
        "linewidth": 2,
        "alpha": 0.8,
    },
    "fire": {
        "marker": "o",
        "color": "red",
        "markersize": 14,
        "linewidth": 2,
        "alpha": 0.8,
    },
}


def plot(
    map_name: str,
    points: Optional[
        Union[Tuple[float, float, float], List[Tuple[float, float, float]]]
    ] = None,
    point_settings: Optional[Union[str, Dict, List[Union[str, Dict]]]] = None,
) -> Tuple[Figure, Axes]:
    """Plot a Counter-Strike map with optional points.

    Args:
        map_name (str): Name of the map to plot.
        points (Union[Tuple[float, float, float], List[Tuple[float, float, float]]], optional):
            Single point or list of points to plot. Each point is (X, Y, Z). Defaults to None.
        point_settings (Union[str, Dict, List[Union[str, Dict]]], optional):
            String, dictionary, or list of strings/dictionaries with matplotlib plot settings for each point.
            Strings should correspond to preset settings. Defaults to None.

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if the map image is not found.
        ValueError: Raises a ValueError if the number of points and point_settings don't match.

    Returns:
        Tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
    """
    # Check for the main map image
    with importlib.resources.path("awpy.data.maps", f"{map_name}.png") as map_img_path:
        if not map_img_path.exists():
            raise FileNotFoundError(f"Map image not found: {map_img_path}")

        map_bg = mpimg.imread(map_img_path)
        figure, axes = plt.subplots()
        axes.imshow(map_bg, zorder=0)
        axes.axis("off")

    # Plot points if provided
    if points is not None:
        # Convert single point to list for uniform processing
        if isinstance(points, tuple):
            points = [points]

        # Process point_settings
        if isinstance(point_settings, (str, dict)):
            point_settings = [point_settings]

        # If no settings provided, use default preset for each point
        if point_settings is None:
            point_settings = ["default" for _ in points]

        # Ensure points and settings have the same length
        if len(points) != len(point_settings):
            raise ValueError("Number of points and point settings must match.")

        # Plot each point
        for (x, y, _), setting in zip(points, point_settings):
            # Transform the x and y coordinates
            transformed_x = position_transform_axis(map_name, x, "x")
            transformed_y = position_transform_axis(map_name, y, "y")

            # Get the settings (either preset or custom)
            if isinstance(setting, str):
                if setting not in PRESET_MARKERS:
                    raise ValueError(f"Unknown preset marker: {setting}")
                plot_settings = PRESET_MARKERS[setting]
            else:
                plot_settings = setting

            axes.plot(transformed_x, transformed_y, **plot_settings)

    figure.patch.set_facecolor("black")
    plt.tight_layout()

    return figure, axes
