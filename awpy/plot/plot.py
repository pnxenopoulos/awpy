"""Module for plotting Counter-Strike data."""

import importlib.resources
import io
import math
import warnings
from typing import Literal, Optional

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PIL import Image
from scipy.stats import gaussian_kde
from tqdm import tqdm

from awpy.plot.utils import game_to_pixel_axis, is_position_on_lower_level


def plot(  # noqa: PLR0915
    map_name: str,
    points: Optional[list[tuple[float, float, float]]] = None,
    lower_points_frac: Optional[float] = 0.4,
    point_settings: Optional[list[dict]] = None,
) -> tuple[Figure, Axes]:
    """Plot a Counter-Strike map with optional points.

    Args:
        map_name (str): Name of the map to plot. E.g. "de_dust2"
            ("dust2" or "de_dust2.png" will not work).
        points (list[tuple[float, float, float]], optional):
            list of points to plot. Each point is (X, Y, Z). Defaults to None.
        lower_points_frac (optional, float): The factor by which to multiply
            the opacity of a given point if it is on the lower level of the
            map and `map_name` is NOT referencing the lower level (i.e.
            `map_name` does not end in "_lower"). Defaults to 0.4.

            If `map_name` is referencing the lower level of a map (i.e.
            ends in "_lower") then this argument is ignored and lower points'
            alpha is set to 1 and upper points' alpha is set to 0.
        point_settings (list[dict], optional):
            list of dictionaries with settings for each point. Each dictionary
            should contain:
            - 'marker': str (default 'o')
            - 'color': str (default 'red')
            - 'size': float (default 10)
            - 'hp': int (0-100)
            - 'armor': int (0-100)
            - 'direction': tuple[float, float] (pitch, yaw in degrees)
            - 'label': str (optional)

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if the map image is not
            found.
        ValueError: Raises a ValueError if the number of points and
            point_settings don't match.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
    """
    image = f"{map_name}.png"
    map_name = map_name.removesuffix("_lower")

    # Check for the main map image
    with importlib.resources.path("awpy.data.maps", image) as map_img_path:
        if not map_img_path.exists():
            map_img_path_err = f"Map image not found: {map_img_path}"
            raise FileNotFoundError(map_img_path_err)

        map_bg = mpimg.imread(map_img_path)
        figure, axes = plt.subplots(figsize=(1024 / 300, 1024 / 300), dpi=300)
        axes.imshow(map_bg, zorder=0)
        axes.axis("off")

    # Plot points if provided
    if points is not None:
        # Ensure points and settings have the same length
        if point_settings is None:
            point_settings = [{}] * len(points)
        elif len(points) != len(point_settings):
            settings_mismatch_err = "Number of points and point_settings do not match."
            raise ValueError(settings_mismatch_err)

        # Plot each point
        for (x, y, z), settings in zip(points, point_settings, strict=False):
            transformed_x = game_to_pixel_axis(map_name, x, "x")
            transformed_y = game_to_pixel_axis(map_name, y, "y")

            # Check if the point is within bounds of the map image
            if (
                transformed_x < 0
                or transformed_x > 1024
                or transformed_y < 0
                or transformed_y > 1024
            ):
                continue

            # Default settings
            marker = settings.get("marker", "o")
            color = settings.get("color", "red")
            size = settings.get("size", 10)
            hp = settings.get("hp")
            armor = settings.get("armor")
            direction = settings.get("direction")
            label = settings.get("label")

            alpha = 0.15 if hp == 0 else 1.0

            map_is_lower = map_name.endswith("_lower")
            point_is_lower = is_position_on_lower_level(map_name, (x, y, z))

            if not map_is_lower and point_is_lower:
                if lower_points_frac == 0:
                    continue
                alpha *= lower_points_frac
            elif map_is_lower and not point_is_lower:
                continue

            transformed_x = game_to_pixel_axis(map_name, x, "x")
            transformed_y = game_to_pixel_axis(map_name, y, "y")

            # Plot the marker
            axes.plot(
                transformed_x,
                transformed_y,
                marker=marker,
                color="black",
                markersize=size,
                alpha=alpha,
                zorder=10,
            )  # Black outline
            axes.plot(
                transformed_x,
                transformed_y,
                marker=marker,
                color=color,
                markersize=size * 0.9,
                alpha=alpha,
                zorder=11,
            )  # Inner color

            # Set bar sizes and offsets
            bar_width = size * 2
            bar_length = size * 6
            vertical_offset = size * 3.5

            if hp and hp > 0:
                # Plot HP bar (red background)
                hp_bar_full = Rectangle(
                    (transformed_x - bar_length / 2, transformed_y + vertical_offset),
                    bar_length,
                    bar_width,
                    facecolor="red",
                    edgecolor="black",
                    alpha=alpha,
                    zorder=11,
                )
                axes.add_patch(hp_bar_full)

                # Plot HP bar (actual health)
                hp_bar = Rectangle(
                    (transformed_x - bar_length / 2, transformed_y + vertical_offset),
                    bar_length * hp / 100,
                    bar_width,
                    facecolor="green",
                    edgecolor="black",
                    alpha=alpha,
                    zorder=11,
                )
                axes.add_patch(hp_bar)

                # Plot Armor bar (lightgrey background)
                armor_bar = Rectangle(
                    (
                        transformed_x - bar_length / 2,
                        transformed_y + vertical_offset + bar_width,
                    ),
                    bar_length,
                    bar_width,
                    facecolor="lightgrey",
                    edgecolor="black",
                    alpha=alpha,
                    zorder=11,
                )
                axes.add_patch(armor_bar)

                # Plot Armor bar (actual armor)
                armor_bar = Rectangle(
                    (
                        transformed_x - bar_length / 2,
                        transformed_y + vertical_offset + bar_width,
                    ),
                    bar_length * armor / 100,
                    bar_width,
                    facecolor="grey",
                    edgecolor="black",
                    alpha=alpha,
                    zorder=11,
                )
                axes.add_patch(armor_bar)

            # Plot direction
            if direction and hp > 0:
                pitch, yaw = direction
                dx = math.cos(math.radians(yaw)) * math.cos(math.radians(pitch))
                dy = math.sin(math.radians(yaw)) * math.cos(math.radians(pitch))
                line_length = size * 2
                axes.plot(
                    [transformed_x, transformed_x + dx * line_length],
                    [transformed_y, transformed_y + dy * line_length],
                    color="black",
                    alpha=alpha,
                    linewidth=1,
                    zorder=12,
                )

            # Add label
            if label:
                label_offset = vertical_offset + 1.25 * bar_width
                axes.annotate(
                    label,
                    (transformed_x, transformed_y - label_offset),
                    xytext=(0, 0),
                    textcoords="offset points",
                    color="white",
                    fontsize=6,
                    alpha=alpha,
                    zorder=13,
                    ha="center",
                    va="top",
                )  # Center the text horizontally

    figure.patch.set_facecolor("black")
    plt.tight_layout()

    return figure, axes


def _generate_frame_plot(
    map_name: str,
    frames_data: list[dict],
    lower_points_frac: Optional[float] = 0.4,
) -> list[Image.Image]:
    """Generate frames for the animation.

    Args:
        map_name (str): Name of the map to plot. E.g. "de_dust2"
            ("dust2" or "de_dust2.png" will not work).
        frames_data (list[dict]): list of dictionaries, each containing
            'points' and 'point_settings' for a frame.
        lower_points_frac (optional, float): The factor by which to multiply
            the opacity of a given point if it is on the lower level of the
            map and `map_name` is NOT referencing the lower level (i.e.
            `map_name` does not end in "_lower"). Defaults to 0.4.

            If `map_name` is referencing the lower level of a map (i.e.
            ends in "_lower") then this argument is ignored and lower points'
            alpha is set to 1 and upper points' alpha is set to 0.

    Returns:
        list[Image.Image]: list of PIL Image objects representing each frame.
    """
    frames = []
    for frame_data in tqdm(frames_data):
        fig, _ax = plot(
            map_name,
            frame_data["points"],
            lower_points_frac,
            frame_data["point_settings"],
        )

        # Convert the matplotlib figure to a PIL Image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor="black")
        buf.seek(0)
        img = Image.open(buf)
        frames.append(img)

        plt.close(fig)  # Close the figure to free up memory

    return frames


def gif(
    map_name: str,
    frames_data: list[dict],
    output_filename: str,
    duration: int = 500,
    lower_points_frac: Optional[float] = 0.4,
) -> None:
    """Create an animated gif from a list of frames.

    Args:
        map_name (str): Name of the map to plot. E.g. "de_dust2"
            ("dust2" or "de_dust2.png" will not work).
        frames_data (list[dict]): list of dictionaries, each containing
            'points' and 'point_settings' for a frame.
        frames (list[Image.Image]): list of PIL Image objects.
        output_filename (str): Name of the output GIF file.
        duration (int): Duration of each frame in milliseconds.
        lower_points_frac (optional, float): The factor by which to multiply
            the opacity of a given point if it is on the lower level of the
            map and `map_name` is NOT referencing the lower level (i.e.
            `map_name` does not end in "_lower"). Defaults to 0.4.

            If `map_name` is referencing the lower level of a map (i.e.
            ends in "_lower") then this argument is ignored and lower points'
            alpha is set to 1 and upper points' alpha is set to 0.
    """
    frames = _generate_frame_plot(
        map_name,
        frames_data,
        lower_points_frac,
    )
    frames[0].save(
        output_filename,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
    )


def _hex_plot(
    ax: Axes,
    x: list[float],
    y: list[float],
    size: int,
    cmap: str,
    alpha: float,
    alpha_range: Optional[list[float]],
    min_alpha: float,
    max_alpha: float,
) -> Axes:
    """Returns an `ax` with a hex plot."""
    # Create heatmap
    heatmap = ax.hexbin(x, y, gridsize=size, cmap=cmap, alpha=alpha)

    # Get array of counts in each hexbin
    counts = heatmap.get_array()

    if alpha_range is not None:
        # Normalize counts to use as alpha values
        alphas = counts / counts.max()
        alphas = alphas * (max_alpha - min_alpha) + min_alpha
        # Update the color alpha values
        heatmap.set_alpha(alphas)

    # Set counts of 0 to NaN to make them transparent
    counts[counts == 0] = np.nan
    heatmap.set_array(counts)

    return ax


def _hist_plot(
    ax: Axes,
    x: list[float],
    y: list[float],
    size: int,
    cmap: str,
    alpha: float,
    alpha_range: Optional[list[float]],
    min_alpha: float,
    max_alpha: float,
) -> Axes:
    """Returns an `ax` with a hist plot."""
    hist, xedges, yedges = np.histogram2d(x, y, bins=size)
    x, y = np.meshgrid(xedges[:-1], yedges[:-1])

    # Set counts of 0 to NaN to make them transparent
    hist[hist == 0] = np.nan

    if alpha_range is not None:
        # Normalize histogram values
        hist_norm = hist.T / hist.max()
        # Create a color array with variable alpha
        colors = plt.cm.get_cmap(cmap)(hist_norm)
        colors[..., -1] = np.where(
            np.isnan(hist_norm),
            0,
            hist_norm * (max_alpha - min_alpha) + min_alpha,
        )
        # Plot the heatmap
        _heatmap = ax.pcolormesh(x, y, hist.T, cmap=cmap, norm=LogNorm(), alpha=colors)
    else:
        _heatmap = ax.pcolormesh(x, y, hist.T, cmap=cmap, norm=LogNorm(), alpha=alpha)

    return ax


def _kde_plot(
    ax: Axes,
    x: list[float],
    y: list[float],
    size: int,
    cmap: str,
    alpha: float,
    alpha_range: Optional[list[float]],
    min_alpha: float,
    max_alpha: float,
    kde_lower_bound: float = 0.1,
) -> Axes:
    """Returns an `ax` with a kde plot."""
    # Calculate the kernel density estimate
    xy = np.vstack([x, y])
    kde = gaussian_kde(xy)
    # Create a grid and evaluate the KDE on it
    xmin, xmax = min(x), max(x)
    ymin, ymax = min(y), max(y)
    xi, yi = np.mgrid[xmin : xmax : size * 1j, ymin : ymax : size * 1j]
    zi = kde(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    # Set very low density values to NaN to make them transparent
    threshold = zi.max() * kde_lower_bound  # You can adjust this threshold
    zi[zi < threshold] = np.nan

    if alpha_range is not None:
        # Normalize KDE values
        zi_norm = zi / zi.max()
        # Create a color array with variable alpha
        colors = plt.cm.get_cmap(cmap)(zi_norm)
        colors[..., -1] = np.where(
            np.isnan(zi_norm),
            0,
            zi_norm * (max_alpha - min_alpha) + min_alpha,
        )
        _heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=colors)
    else:
        _heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=alpha)

    return ax


def verify_alpha_range(alpha_range: list[float]) -> list:
    """Verify that `alpha_range` is valid."""
    if len(alpha_range) != 2:
        msg = "alpha_range must have exactly 2 elements."
        raise ValueError(msg)
    min_val, max_val = alpha_range[0], alpha_range[1]
    if not (min_val >= 0 and min_val <= 1) or not (max_val >= 0 and max_val <= 1):
        msg = "alpha_range must have both values as floats between \
            0 and 1."
        raise ValueError(msg)
    if min_val > max_val:
        msg = "alpha_range[0] (min alpha) cannot be greater than \
            alpha[1] (max alpha)."
        raise ValueError(msg)
    return [min_val, max_val]


def heatmap(
    map_name: str,
    points: list[tuple[float, float, float]],
    method: Literal["hex", "hist", "kde"],
    size: int = 10,
    cmap: str = "RdYlGn",
    alpha: float = 0.5,
    *,
    alpha_range: Optional[list[float]] = None,
    kde_lower_bound: float = 0.1,
) -> tuple[Figure, Axes]:
    """Create a heatmap of points on a Counter-Strike map.

    Args:
        map_name (str): Name of the map to plot. E.g. "de_dust2"
            ("dust2" or "de_dust2.png" will not work).
        points (list[tuple[float, float, float]]): list of points to plot.
        method (Literal["hex", "hist", "kde"]): Method to use for the heatmap.
        size (int, optional): Size of the heatmap grid. Defaults to 10.
        cmap (str, optional): Colormap to use. Defaults to 'RdYlGn'.
        alpha (float, optional): Transparency of the heatmap. Defaults to 0.5.
        alpha_range (list[float, float], optional): When value is provided
            here,  points' transparency will vary based on the density, with
            min transparency of `alpha_range[0]` and max of `alpha_range[1]`.
            Defaults to `None`, meaning no variance of transparency.
        kde_lower_bound (float, optional): Lower bound for KDE density
            values. Defaults to 0.1.

    Raises:
        ValueError: Raises a ValueError if an invalid method is provided.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects
    """
    fig, ax = plt.subplots(figsize=(1024 / 300, 1024 / 300), dpi=300)

    image = f"{map_name}.png"

    map_is_lower = map_name.endswith("_lower")
    if map_is_lower:
        map_name = map_name.removesuffix("_lower")

    # Load and display the map
    with importlib.resources.path("awpy.data.maps", image) as map_img_path:
        map_bg = mpimg.imread(map_img_path)
        ax.imshow(map_bg, zorder=0, alpha=0.5)

    temp_points = points
    points = []
    warning = ""
    for point in temp_points:
        point_is_lower = is_position_on_lower_level(map_name, point)
        # If point is on same level as map, then keep, else ignore & warn.
        if point_is_lower == map_is_lower:
            points.append(point)
        else:
            warning = f"You are drawing on the {'lower' if map_is_lower else 'upper'} level of the map, but provided some points on the {'lower' if point_is_lower else 'upper'} level, which were ignored."  # noqa: E501
    if warning:
        warnings.warn(warning, UserWarning, stacklevel=2)

    x, y = [], []
    for point in points:
        x_point = game_to_pixel_axis(map_name, point[0], "x")
        y_point = game_to_pixel_axis(map_name, point[1], "y")

        # Check if the point is within bounds of the map image
        if x_point < 0 or x_point > 1024 or y_point < 0 or y_point > 1024:
            continue

        x.append(x_point)
        y.append(y_point)

    # Check and/or set alpha_range
    min_alpha, max_alpha = 0, 1
    if alpha_range is not None:
        min_alpha, max_alpha = verify_alpha_range(alpha_range)

    if method == "hex":
        ax = _hex_plot(
            ax,
            x,
            y,
            size,
            cmap,
            alpha,
            alpha_range,
            min_alpha,
            max_alpha,
        )

    elif method == "hist":
        ax = _hist_plot(
            ax,
            x,
            y,
            size,
            cmap,
            alpha,
            alpha_range,
            min_alpha,
            max_alpha,
        )

    elif method == "kde":
        ax = _kde_plot(
            ax,
            x,
            y,
            size,
            cmap,
            alpha,
            alpha_range,
            min_alpha,
            max_alpha,
            kde_lower_bound,
        )

    ax.axis("off")
    fig.patch.set_facecolor("black")
    plt.tight_layout()

    return fig, ax
