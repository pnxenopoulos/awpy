"""Module for plotting Counter-Strike data."""

import importlib.resources
import math
from typing import Dict, List, Literal, Optional, Tuple, Union

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle
from scipy.stats import gaussian_kde

from awpy.plot.utils import is_position_on_lower_level, position_transform_axis

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
    "kill": {
        "marker": "x",
        "color": "red",
        "markersize": 10,
        "linewidth": 2,
        "alpha": 0.8,
    },
}


def plot(
    map_name: str,
    points: Optional[List[Tuple[float, float, float]]] = None,
    point_settings: Optional[List[Dict]] = None,
) -> Tuple[Figure, Axes]:
    """Plot a Counter-Strike map with optional points.

    Args:
        map_name (str): Name of the map to plot.
        points (List[Tuple[float, float, float]], optional):
            List of points to plot. Each point is (X, Y, Z). Defaults to None.
        point_settings (List[Dict], optional):
            List of dictionaries with settings for each point. Each dictionary should contain:
            - 'marker': str (default 'o')
            - 'color': str (default 'red')
            - 'size': float (default 10)
            - 'hp': int (0-100)
            - 'armor': int (0-100)
            - 'direction': Tuple[float, float] (pitch, yaw in degrees)
            - 'label': str (optional)

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
        # Ensure points and settings have the same length
        if point_settings is None:
            point_settings = [{}] * len(points)
        elif len(points) != len(point_settings):
            raise ValueError("Number of points and point settings must match.")

        # Plot each point
        for (x, y, z), settings in zip(points, point_settings):
            transformed_x = position_transform_axis(map_name, x, "x")
            transformed_y = position_transform_axis(map_name, y, "y")

            # Default settings
            marker = settings.get('marker', 'o')
            color = settings.get('color', 'red')
            size = settings.get('size', 10)
            hp = settings.get('hp', 100)
            armor = settings.get('armor', 0)
            direction = settings.get('direction', (0, 0))
            label = settings.get('label', None)

            alpha = 0.2 if hp == 0 else 1.0
            if is_position_on_lower_level(map_name, (x, y, z)):
                alpha *= 0.4

            # Plot the marker
            axes.plot(transformed_x, transformed_y, marker=marker, color=color, 
                      markersize=size, alpha=alpha, zorder=10)

            if hp > 0:
                # Plot HP bar
                bar_width = size / 1
                bar_length = size * 2
                hp_bar = Rectangle((transformed_x - bar_length/2, transformed_y + size/2 + bar_width), 
                                   bar_length * hp/100, bar_width, 
                                   facecolor='green', edgecolor='none', alpha=alpha, zorder=11)
                axes.add_patch(hp_bar)

                # Plot Armor bar
                armor_bar = Rectangle((transformed_x - bar_length/2, transformed_y + size/2), 
                                      bar_length * armor/100, bar_width, 
                                      facecolor='grey', edgecolor='none', alpha=alpha, zorder=11)
                axes.add_patch(armor_bar)

            # Plot direction
            if direction is not None:
                pitch, yaw = direction
                dx = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
                dy = math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
                line_length = size * 1.5
                axes.plot([transformed_x, transformed_x + dx*line_length], 
                          [transformed_y, transformed_y + dy*line_length], 
                          color="black", alpha=alpha, linewidth=1, zorder=12)

            # Add label if provided
            if label:
                axes.annotate(label, (transformed_x, transformed_y), 
                              xytext=(5, 5), textcoords='offset points', 
                              color='white', fontsize=8, alpha=alpha, zorder=13)

    figure.patch.set_facecolor("black")
    plt.tight_layout()

    return figure, axes

# def plot(
#     map_name: str,
#     points: Optional[
#         Union[Tuple[float, float, float], List[Tuple[float, float, float]]]
#     ] = None,
#     point_settings: Optional[Union[str, Dict, List[Union[str, Dict]]]] = None,
# ) -> Tuple[Figure, Axes]:
#     """Plot a Counter-Strike map with optional points.

#     Args:
#         map_name (str): Name of the map to plot.
#         points (Union[Tuple[float, float, float], List[Tuple[float, float, float]]], optional):
#             Single point or list of points to plot. Each point is (X, Y, Z). Defaults to None.
#         point_settings (Union[str, Dict, List[Union[str, Dict]]], optional):
#             String, dictionary, or list of strings/dictionaries with matplotlib plot settings for each point.
#             Strings should correspond to preset settings. Defaults to None.

#     Raises:
#         FileNotFoundError: Raises a FileNotFoundError if the map image is not found.
#         ValueError: Raises a ValueError if the number of points and point_settings don't match.

#     Returns:
#         Tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
#     """
#     # Check for the main map image
#     with importlib.resources.path("awpy.data.maps", f"{map_name}.png") as map_img_path:
#         if not map_img_path.exists():
#             raise FileNotFoundError(f"Map image not found: {map_img_path}")

#         map_bg = mpimg.imread(map_img_path)
#         figure, axes = plt.subplots()
#         axes.imshow(map_bg, zorder=0)
#         axes.axis("off")

#     # Plot points if provided
#     if points is not None:
#         # Convert single point to list for uniform processing
#         if isinstance(points, tuple):
#             points = [points]

#         # Process point_settings
#         if isinstance(point_settings, (str, dict)):
#             point_settings = [point_settings]

#         # If no settings provided, use default preset for each point
#         if point_settings is None:
#             point_settings = ["default" for _ in points]

#         # Ensure points and settings have the same length
#         if len(points) != len(point_settings):
#             raise ValueError("Number of points and point settings must match.")

#         # Plot each point
#         for (x, y, z), setting in zip(points, point_settings):
#             # Transform the x and y coordinates
#             transformed_x = position_transform_axis(map_name, x, "x")
#             transformed_y = position_transform_axis(map_name, y, "y")

#             # Get the settings (either preset or custom)
#             if isinstance(setting, str):
#                 if setting not in PRESET_MARKERS:
#                     raise ValueError(f"Unknown preset marker: {setting}")
#                 plot_settings = PRESET_MARKERS[setting]
#             else:
#                 plot_settings = setting

#             # Check if the point is on a lower level and adjust visibility
#             if is_position_on_lower_level(map_name, (x, y, z)):
#                 plot_settings["alpha"] = 0.4

#             axes.plot(transformed_x, transformed_y, **plot_settings)

#     figure.patch.set_facecolor("black")
#     plt.tight_layout()

#     return figure, axes


def heatmap(
    map_name: str,
    points: List[Tuple[float, float, float]],
    method: Literal["hex", "hist", "kde"],
    size: int = 10,
    cmap: str = "RdYlGn",
    alpha: float = 0.5,
    vary_alpha: bool = False,
) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots()

    # Load and display the map
    with importlib.resources.path("awpy.data.maps", f"{map_name}.png") as map_img_path:
        map_bg = mpimg.imread(map_img_path)
        ax.imshow(map_bg, zorder=0, alpha=0.5)

    # Transform coordinates
    x = [position_transform_axis(map_name, p[0], "x") for p in points]
    y = [position_transform_axis(map_name, p[1], "y") for p in points]

    if method == "hex":
        # Create heatmap
        heatmap = ax.hexbin(x, y, gridsize=size, cmap=cmap, alpha=alpha)

        if vary_alpha:
            # Get array of counts in each hexbin
            counts = heatmap.get_array()
            # Normalize counts to use as alpha values
            alphas = counts / counts.max()
            alphas = alphas * alpha
            # Update the color alpha values
            heatmap.set_alpha(alphas)
    elif method == "hist":
        if vary_alpha:
            hist, xedges, yedges = np.histogram2d(x, y, bins=size)
            X, Y = np.meshgrid(xedges[:-1], yedges[:-1])
            # Normalize histogram values
            hist_norm = hist.T / hist.max()
            # Create a color array with variable alpha
            colors = plt.cm.get_cmap(cmap)(hist_norm)
            colors[..., -1] = hist_norm * alpha
            # Plot the heatmap
            heatmap = ax.pcolormesh(
                X, Y, hist.T, cmap=cmap, norm=LogNorm(), alpha=colors
            )
        else:
            heatmap = ax.hist2d(x, y, bins=size, cmap=cmap, norm=LogNorm(), alpha=alpha)
    elif method == "kde":
        # Calculate the kernel density estimate
        xy = np.vstack([x, y])
        kde = gaussian_kde(xy)
        # Create a grid and evaluate the KDE on it
        xmin, xmax = min(x), max(x)
        ymin, ymax = min(y), max(y)
        xi, yi = np.mgrid[xmin : xmax : size * 1j, ymin : ymax : size * 1j]
        zi = kde(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)
        if vary_alpha:
            # Normalize KDE values
            zi_norm = zi / zi.max()
            # Create a color array with variable alpha
            colors = plt.cm.get_cmap(cmap)(zi_norm)
            colors[..., -1] = zi_norm * alpha
            heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=colors)
        else:
            heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=alpha)
    else:
        raise ValueError("Invalid method. Choose 'hex', 'hist' or 'prob'.")

    ax.axis("off")
    fig.patch.set_facecolor("black")
    plt.tight_layout()

    return fig, ax
