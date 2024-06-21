"""Module for plotting Counter-Strike data."""

import importlib.resources
from typing import Optional

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure


def plot_map(map_name: str, *, lower: Optional[bool] = None) -> tuple[Figure, Axes]:
    """Plot a Counter-Strike map.

    Args:
        map_name (str): Name of the map to plot.
        lower (Optional[bool], optional): True if you want to plot the lower, False for
            upper. Defaults to None.

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if the map image is not found.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
    """
    if lower is None:
        figure, axes = plot_upper_and_lower(map_name)
    else:
        if lower is True:
            map_name += "_lower"

        with importlib.resources.path(
            "awpy.data.maps", f"{map_name}.png"
        ) as map_img_path:
            if not map_img_path.exists():
                map_img_not_found_msg = f"Map image not found: {map_img_path}"
                raise FileNotFoundError(map_img_not_found_msg)

            map_bg = mpimg.imread(map_img_path)

            figure, axes = plt.subplots()
            axes.imshow(map_bg, zorder=0)

    return figure, axes


def plot_upper_and_lower(map_name: str) -> tuple[Figure, list[Axes]]:
    """Plot a Counter-Strike map side-by-side.

    Args:
        map_name (str): Name of the map to plot.
        lower (bool, optional): Allows plotting the lower layer. Defaults to False.

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if a map image is not found.

    Returns:
        Tuple[Figure, List[Axes]]: Matplotlib Figure and list of Axes objects.
    """
    map_names = [map_name, f"{map_name}_lower"]
    figure, axes = plt.subplots(1, 2)  # , figsize=(2 * 5, 5)

    for ax, map_layer_name in zip(axes, map_names, strict=True):
        with importlib.resources.path(
            "awpy.data.maps", f"{map_layer_name}.png"
        ) as map_img_path:
            if not map_img_path.exists():
                map_img_not_found_msg = f"Map image not found: {map_img_path}"
                raise FileNotFoundError(map_img_not_found_msg)

            map_bg = mpimg.imread(map_img_path)
            ax.imshow(map_bg, zorder=0)
            ax.set_facecolor("black")
            ax.axis("off")  # Hide axes

    # Set figure background color to black, lower doesn't have a facecolor
    figure.patch.set_facecolor("black")
    plt.tight_layout()
    return figure, axes
