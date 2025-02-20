"""Utilities for plotting tiles on a map specifically.

credit: @JanEricNitschke.
"""

import importlib.resources
import os

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.axes import Axes

import awpy.nav
import awpy.plot.utils

NAV = {}
MAP_DIR = "../data/nav"
# TODO: Change hardcoded de_dust2
NAV["de_dust2"] = awpy.nav.Nav(path="../../awpy/data/de_dust2")


def plot_map(map_name: str) -> tuple:
    """Plots a map background based on the provided map name and returns the figure and axes objects.

    This function loads a PNG image corresponding to the given map name and displays it using matplotlib.
    If the map name ends with "_lower", that suffix is removed before loading the image.

    Parameters:
    -----------
    map_name : str
        The name of the map (without the .png extension). If the map name ends with "_lower",
        the suffix will be removed before loading the image.

    Returns:
    --------
    tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]
        A tuple containing:
        - `fig`: The matplotlib Figure object containing the plot.
        - `ax`: The matplotlib Axes object where the map is displayed.

    Example:
    --------
    >>> fig, ax = plot_map("de_dust2")
    >>> plt.show()
    """
    fig, ax = plt.subplots(figsize=(1024 / 300, 1024 / 300), dpi=300)
    image = f"{map_name}.png"
    if map_name.endswith("_lower"):
        map_name = map_name.removesuffix("_lower")
    # Load and display the map background
    with importlib.resources.path("awpy.data.maps", image) as map_img_path:
        map_bg = mpimg.imread(map_img_path)
        ax.imshow(map_bg, zorder=0, alpha=0.5)
    return fig, ax


def _tile_polygon(area_dict: dict) -> list:
    """Convert an area's corner coordinates to pixel coordinates."""
    # TODO: Change hardcoded de_dust2
    return [awpy.plot.utils.game_to_pixel("de_dust2", (c["x"], c["y"], c["z"]))[0:2] for c in area_dict["corners"]]


def _plot_tile(axis: Axes, polygon: list, edgecolor: str, facecolor: str, linewidth: int = 1) -> None:
    """Add a single tile patch to the axis."""
    patch = patches.Polygon(polygon, linewidth=linewidth, edgecolor=edgecolor, facecolor=facecolor)
    axis.add_patch(patch)


def _plot_all_tiles(map_dict: "awpy.nav.Nav", axis: Axes, default_fill: str = "None") -> None:
    """Plot every tile with a yellow outline and optional fill color."""
    for area in map_dict.areas.values():
        area_dict = area.to_dict()
        polygon = _tile_polygon(area_dict)
        _plot_tile(axis, polygon, edgecolor="yellow", facecolor=default_fill)


def _plot_selected_tiles(map_dict: "awpy.nav.Nav", axis: Axes, selected_tiles: list) -> None:
    """Plot all tiles, highlighting the selected ones.

    - Tiles not in the selected list are drawn with a yellow outline and no fill.
    - Tiles in the selected list are filled with red and black outlines.
    - If multiple tiles are selected (a path), the first and last tiles are filled in green and
      outlined in black.
    """
    # Using a set for quick membership tests.
    selected_set = set(selected_tiles)

    for tile_id, area in map_dict.areas.items():
        area_dict = area.to_dict()
        polygon = _tile_polygon(area_dict)
        if tile_id in selected_set:
            """
            - If just one tile is passed in to visualize, it is filled in red with black edges.
            - If a list of lenth > 1 is passed in (a path), then the first and last tiles are
              filled in green with white edges. All other tiles are filled in red with white edges.
            - All tiles not in the passed in list are colored with no fill and yellow edges.
            """
            if len(selected_tiles) > 1 and (tile_id == selected_tiles[0] or tile_id == selected_tiles[-1]):
                edgecolor = "black"
                facecolor = "green"
            else:
                edgecolor = "black"
                facecolor = "red"
        else:
            facecolor = "None"
            edgecolor = "yellow"
        _plot_tile(axis, polygon, edgecolor=edgecolor, facecolor=facecolor)


def plot_map_tiles(map_name: str = "de_ancient", output_path: str = "", dpi: int = 1000, fill: str = "None") -> None:
    """Plot all navigation mesh tiles for a given map.

    This function overlays navigation mesh tiles onto a specified map and highlights them.
    Non-selected tiles are drawn with a yellow outline. The resulting plot can be displayed
    and optionally saved to a file.

    Parameters:
    -----------
    map_name : str, optional
        The name of the map to plot (default is "de_ancient").
    output_path : str, optional
        Path to save the plotted image. If left as an empty string (""), the figure won't be saved (default is "").
    dpi : int, optional
        Dots per inch for the saved figure. Higher values result in better image quality (default is 1000).
    fill : str, optional
        The fill color for the tiles. Use "None" for no fill or specify a valid color (default is "None").

    Returns:
    --------
    None
        This function displays the plot and optionally saves it if `output_path` is provided.

    Example:
    --------
    >>> plot_map_tiles(map_name="de_dust2", output_path="./maps", dpi=800, fill="blue")
    # Displays the plot and saves it as './maps/tiles_de_dust2.png'
    """
    fig, axis = plot_map(map_name=map_name)
    fig.set_size_inches(19.2, 21.6)
    _plot_all_tiles(NAV[map_name], axis, default_fill=fill)
    plt.show()
    # Optionally save the figure:
    if output_path != "":
        plt.savefig(os.path.join(output_path, f"tiles_{map_name}.png"), bbox_inches="tight", dpi=dpi)
    fig.clear()
    plt.close()


def plot_map_tiles_selected(map_name: str, selected_tiles: list, output_path: str = "", dpi: int = 1000) -> None:
    """Plot navigation mesh tiles for a given map with selected tiles highlighted.

    This function overlays navigation mesh tiles onto the specified map and highlights the
    selected tiles. Non-selected tiles are drawn with a yellow outline, while selected tiles
    are filled with a default color (green) and outlined in black. If a path is selected (more
    than one tile), the first and last tiles (source and destination) are filled with red
    and outlined in black.

    Parameters:
    -----------
    map_name : str
        The name of the map to plot.
    selected_tiles : list
        A list of tile IDs to be highlighted on the map.
    output_path : str, optional
        Path to save the plotted image. If left as an empty string (""), the figure won't be saved (default is "").
    dpi : int, optional
        Dots per inch for the saved figure. Higher values result in better image quality (default is 1000).

    Returns:
    --------
    None
        This function displays the plot and optionally saves it if `output_path` is provided.

    Behavior:
    ---------
    - Non-selected tiles are drawn with a yellow outline.
    - Selected tiles are filled with a default color (usually red).
    - If multiple tiles are selected (e.g., a path), the first and last tiles (source and destination)
      are outlined in black.

    Example:
    --------
    >>> plot_map_tiles_selected(
    ...     map_name="de_dust2",
    ...     selected_tiles=[5, 12, 18],
    ...     output_path="./maps",
    ...     dpi=800
    ... )
    # Displays the plot and saves it as './maps/selected_tiles_de_dust2.png'
    """
    fig, axis = plot_map(map_name=map_name)
    fig.set_size_inches(19.2, 21.6)
    _plot_selected_tiles(NAV[map_name], axis, selected_tiles)
    plt.show()
    # Optionally save the figure:
    if output_path != "":
        plt.savefig(os.path.join(output_path, f"selected_tiles_{map_name}.png"), bbox_inches="tight", dpi=dpi)
    fig.clear()
    plt.close()
