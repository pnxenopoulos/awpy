"""Module for plotting Counter-Strike data."""

import importlib.resources
import io
import math
from collections.abc import Sequence
from typing import Literal, TypedDict

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

from awpy.plot.utils import is_position_on_lower_level, position_transform_axis


class PointSetting(TypedDict, total=False):
    """Setting for a point."""

    marker: str
    color: str
    size: float
    hp: int
    armor: int
    direction: tuple[float, float]
    label: str


def plot(  # noqa: PLR0915
    map_name: str,
    points: Sequence[tuple[float, float, float]] | None = None,
    point_settings: Sequence[PointSetting] | None = None,
) -> tuple[Figure, Axes]:
    # pylint: disable=too-many-locals, too-many-statements
    """Plot a Counter-Strike map with optional points.

    Args:
        map_name (str): Name of the map to plot.
        points (List[Tuple[float, float, float]], optional):
            List of points to plot. Each point is (X, Y, Z). Defaults to None.
        point_settings (List[Dict], optional):
            List of dictionaries with settings for each point. Each dictionary
            should contain:
            - 'marker': str (default 'o')
            - 'color': str (default 'red')
            - 'size': float (default 10)
            - 'hp': int (0-100)
            - 'armor': int (0-100)
            - 'direction': Tuple[float, float] (pitch, yaw in degrees)
            - 'label': str (optional)

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if the map image is not found.
        ValueError: Raises a ValueError if the number of points and
            point_settings don't match.

    Returns:
        Tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
    """
    # Check for the main map image
    with importlib.resources.path("awpy.data.maps", f"{map_name}.png") as map_img_path:
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
            point_settings = [{} for _ in range(len(points))]
        elif len(points) != len(point_settings):
            settings_mismatch_err = "Number of points and point_settings do not match."
            raise ValueError(settings_mismatch_err)

        # Plot each point
        for (x, y, z), settings in zip(points, point_settings, strict=False):
            transformed_x = position_transform_axis(map_name, x, "x")
            transformed_y = position_transform_axis(map_name, y, "y")

            # Default settings
            marker = settings.get("marker", "o")
            color = settings.get("color", "red")
            size = settings.get("size", 10)
            hp = settings.get("hp")
            armor = settings.get("armor")
            direction = settings.get("direction")
            label = settings.get("label")

            alpha = 0.15 if hp == 0 else 1.0
            if is_position_on_lower_level(map_name, (x, y, z)):
                alpha *= 0.4

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
                if armor:
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
            if direction and hp and hp > 0:
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


def _generate_frame_plot(map_name: str, frames_data: list[dict]) -> list[Image.Image]:
    """Generate frames for the animation.

    Args:
        map_name (str): Name of the map to plot.
        frames_data (List[Dict]): List of dictionaries, each containing 'points'
            and 'point_settings' for a frame.

    Returns:
        List[Image.Image]: List of PIL Image objects representing each frame.
    """
    frames = []
    for frame_data in tqdm(frames_data):
        fig, _ax = plot(map_name, frame_data["points"], frame_data["point_settings"])

        # Convert the matplotlib figure to a PIL Image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor="black")
        buf.seek(0)
        img = Image.open(buf)
        frames.append(img)

        plt.close(fig)  # Close the figure to free up memory

    return frames


def gif(
    map_name: str, frames_data: list[dict], output_filename: str, duration: int = 500
) -> None:
    """Create an animated gif from a list of frames.

    Args:
        map_name (str): Name of the map to plot.
        frames_data (List[Dict]): List of dictionaries, each containing 'points'
            and 'point_settings' for a frame.
        frames (List[Image.Image]): List of PIL Image objects.
        output_filename (str): Name of the output GIF file.
        duration (int): Duration of each frame in milliseconds.
    """
    frames = _generate_frame_plot(map_name, frames_data)
    frames[0].save(
        output_filename,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
    )


def heatmap(
    map_name: str,
    points: list[tuple[float, float, float]],
    method: Literal["hex", "hist", "kde"],
    size: int = 10,
    cmap: str = "RdYlGn",
    alpha: float = 0.5,
    *,
    vary_alpha: bool = False,
    kde_lower_bound: float = 0.1,
) -> tuple[Figure, Axes]:
    # pylint: disable=too-many-locals, redefined-outer-name
    """Create a heatmap of points on a Counter-Strike map.

    Args:
        map_name (str): Name of the map to plot.
        points (List[Tuple[float, float, float]]): List of points to plot.
        method (Literal["hex", "hist", "kde"]): Method to use for the heatmap.
        size (int, optional): Size of the heatmap grid. Defaults to 10.
        cmap (str, optional): Colormap to use. Defaults to 'RdYlGn'.
        alpha (float, optional): Transparency of the heatmap. Defaults to 0.5.
        vary_alpha (bool, optional): Vary the alpha based on the density. Defaults
            to False.
        kde_lower_bound (float, optional): Lower bound for KDE density values. Defaults
            to 0.1.

    Raises:
        ValueError: Raises a ValueError if an invalid method is provided.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects
    """
    fig, ax = plt.subplots(figsize=(1024 / 300, 1024 / 300), dpi=300)

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

        # Get array of counts in each hexbin
        counts = heatmap.get_array()
        # Set counts of 0 to NaN to make them transparent
        counts[counts == 0] = np.nan
        heatmap.set_array(counts)

        if vary_alpha:
            # Normalize counts to use as alpha values
            alphas = counts / counts.max()
            alphas = alphas * alpha
            # Update the color alpha values
            heatmap.set_alpha(alphas)

    elif method == "hist":
        hist, xedges, yedges = np.histogram2d(x, y, bins=size)
        x, y = np.meshgrid(xedges[:-1], yedges[:-1])

        # Set counts of 0 to NaN to make them transparent
        hist[hist == 0] = np.nan

        if vary_alpha:
            # Normalize histogram values
            hist_norm = hist.T / hist.max()
            # Create a color array with variable alpha
            colors = plt.get_cmap(cmap)(hist_norm)
            colors[..., -1] = np.where(np.isnan(hist_norm), 0, hist_norm * alpha)
            # Plot the heatmap
            heatmap = ax.pcolormesh(
                x, y, hist.T, cmap=cmap, norm=LogNorm(), alpha=colors
            )
        else:
            heatmap = ax.pcolormesh(
                x, y, hist.T, cmap=cmap, norm=LogNorm(), alpha=alpha
            )

    elif method == "kde":
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

        if vary_alpha:
            # Normalize KDE values
            zi_norm = zi / zi.max()
            # Create a color array with variable alpha
            colors = plt.get_cmap(cmap)(zi_norm)
            colors[..., -1] = np.where(np.isnan(zi_norm), 0, zi_norm * alpha)
            heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=colors)
        else:
            heatmap = ax.pcolormesh(xi, yi, zi, cmap=cmap, alpha=alpha)
    else:
        invalid_method_msg = "Invalid method. Choose 'hex', 'hist' or 'kde'."
        raise ValueError(invalid_method_msg)

    ax.axis("off")
    fig.patch.set_facecolor("black")
    plt.tight_layout()

    return fig, ax
