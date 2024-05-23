"""Module for plotting Counter-Strike data."""

import importlib.resources

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure


def plot_map(map_name: str, *, lower: bool = False) -> tuple[Figure, Axes]:
    """Plot a Counter-Strike map.

    Args:
        map_name (str): Name of the map to plot.
        lower (bool, optional): Allows plotting the lower layer. Defaults to False.

    Raises:
        FileNotFoundError: Raises a FileNotFoundError if the map image is not found.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects.
    """
    if lower is True:
        map_name += "_lower"

    with importlib.resources.path("awpy.data.maps", f"{map_name}.png") as map_img_path:
        if not map_img_path.exists():
            map_img_not_found_msg = f"Map image not found: {map_img_path}"
            raise FileNotFoundError(map_img_not_found_msg)

        map_bg = mpimg.imread(map_img_path)

        figure, axes = plt.subplots()
        axes.imshow(map_bg, zorder=0)
        return figure, axes
