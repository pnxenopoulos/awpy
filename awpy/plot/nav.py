"""Module for plotting navigation mesh tiles on a map."""

from pathlib import Path

import matplotlib.pyplot as plt
from loguru import logger
from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import awpy.data
import awpy.nav
import awpy.plot
import awpy.plot.utils
import awpy.vector


def _tile_polygon(area_corners: list[awpy.vector.Vector3], map_name: str) -> list[tuple[float, float]]:
    """Converts a Nav Area's corner coordinates to pixel coordinates.

    Args:
        area_corners (awpy.vector.Vector3): List of corner positions
            (see NavArea.corners for more info)
        map_name (str): The map name used for coordinate conversion.

    Returns:
        list: List of (x, y) pixel coordinates.
    """
    return [awpy.plot.utils.game_to_pixel(map_name, (c.x, c.y, c.z))[0:2] for c in area_corners]


def _plot_tile(
    axis: Axes, polygon: list[tuple[float, float]], edgecolor: str, facecolor: str, linewidth: int = 1
) -> None:
    """Adds a single tile patch to the given axis.

    Args:
        axis (matplotlib.axes.Axes): The matplotlib axis to add the tile to.
        polygon (list[tuple[float, float]]): List of (x, y) pixel coordinates representing the tile's corners.
        edgecolor (str): Color of the tile's border.
        facecolor (str): Fill color of the tile.
        linewidth (int, optional): Width of the tile's border. Defaults to 1.

    Returns:
        None

    Example:
        >>> _plot_tile(ax, [(0, 0), (1, 0), (1, 1), (0, 1)], edgecolor="blue", facecolor="red")
    """
    patch = patches.Polygon(polygon, linewidth=linewidth, edgecolor=edgecolor, facecolor=facecolor)
    axis.add_patch(patch)


def _plot_all_tiles(map_name: str, axis: Axes, default_fill: str = "None") -> None:
    """Plots all tiles from the map with a yellow outline and optional fill color.

    Args:
        map_name (str): The name of the map for plotting.
        axis (matplotlib.axes.Axes): The matplotlib axis to plot the tiles on.
        default_fill (str, optional): Fill color for the tiles. Defaults to "None".

    Returns:
        None

    Example:
        >>> _plot_all_tiles(map_name, ax, default_fill="gray")
    """
    map_nav = awpy.nav.Nav.from_json(awpy.data.NAVS_DIR / f"{map_name}.json")
    for area in map_nav.areas.values():
        polygon = _tile_polygon(area.corners, map_name)
        _plot_tile(axis, polygon, edgecolor="yellow", facecolor=default_fill)


def _plot_selected_tiles(map_name: str, axis: Axes, selected_tiles: list[int]) -> None:
    """Plots all tiles on the map, highlighting the selected ones.

    - Tiles not in the selected list are drawn with a yellow outline and no fill.
    - Tiles in the selected list are filled with red and have black outlines.
    - If multiple tiles are selected (representing a path), the first and last tiles are
      filled in green with black outlines.

    Args:
        map_name (str): The name of the map for plotting.
        axis (matplotlib.axes.Axes): The matplotlib axis to plot the tiles on.
        selected_tiles (list[int]): List of tile IDs to highlight. Can represent a path if multiple
        tiles are included.

    Returns:
        None

    Example:
        >>> selected = [101, 102, 103]
        >>> _plot_selected_tiles(map_name, ax, selected)
    """
    # Using a set for quick membership tests.
    selected_set = set(selected_tiles)

    map_nav = awpy.nav.Nav.from_json(awpy.data.NAVS_DIR / f"{map_name}.json")
    for tile_id, area in map_nav.areas.items():
        polygon = _tile_polygon(area.corners, map_name)
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
            edgecolor = "yellow"
            facecolor = "None"
        _plot_tile(axis, polygon, edgecolor=edgecolor, facecolor=facecolor)


def plot_map_tiles(
    map_name: str,
    outpath: str | Path | None = None,
    dpi: int = 300,
    fill: str | None = None,
    figure_size: tuple[float, float] = (19, 21),
) -> tuple[Figure, Axes]:
    """Plots all navigation mesh tiles for a given map.

    This function overlays navigation mesh tiles onto a specified map and highlights them.
    Non-selected tiles are drawn with a yellow outline. The resulting plot can either be
    displayed or saved to a file.

    Args:
        map_name (str): The name of the map to plot.
        outpath (str | pathlib.Path | None, optional): The file path to save the plotted image.
            Accepts both string and Path objects. If None, the figure will be displayed instead
            of saved. Defaults to None.
        dpi (int, optional): Dots per inch for the saved figure. Higher values result in
            better image quality. Defaults to 300.
        fill (str, optional): The fill color for the tiles. Use "None" for no fill or specify
            a valid color. Defaults to "None".
        figure_size (tuple[float, float], optional): Tuple representing the figure size in inches
            (width, height). Defaults to `(19, 21)`.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects.

    Example:
        >>> plot_map_tiles(
        ...     map_name="de_dust2",
        ...     outpath="./maps/tiles_de_dust2.png",
        ...     dpi=800,
        ...     fill="blue",
        ...     figure_size=(15, 20)
        ... )
        # Saves the plot to './maps/tiles_de_dust2.png'

        >>> plot_map_tiles(
        ...     map_name="de_dust2",
        ...     fill="green"
        ... )
        # Displays the plot with the default figure size
    """
    fig, axis = awpy.plot.plot(map_name=map_name)
    fig.set_size_inches(*figure_size)
    _plot_all_tiles(map_name, axis, default_fill=fill)

    # Handle outpath for both str and Path inputs
    if outpath is not None:
        outpath = Path(outpath)
        outpath.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directory exists
        plt.savefig(outpath, bbox_inches="tight", dpi=dpi)
        logger.debug(f"The visualization has been saved at {outpath.resolve()}")

    return fig, axis


def plot_map_tiles_selected(
    map_name: str,
    selected_tiles: list,
    outpath: str | Path | None = None,
    dpi: int = 300,
    figure_size: tuple[float, float] = (19, 21),
) -> tuple[Figure, Axes]:
    """Plots navigation mesh tiles for a given map with selected tiles highlighted.

    This function overlays navigation mesh tiles onto the specified map and highlights the
    selected tiles. Non-selected tiles are drawn with a yellow outline, while selected tiles
    are filled with a default color (red) and outlined in black. If multiple tiles are selected
    (e.g., representing a path), the first and last tiles are filled with green and outlined
    in black to denote the source and destination.

    Args:
        map_name (str): The name of the map to plot.
        selected_tiles (list): List of tile IDs to be highlighted on the map.
        outpath (str | pathlib.Path | None, optional): The file path to save the plotted image.
            Accepts both string and Path objects. If None, the figure will be displayed
            instead of saved. Defaults to None.
        dpi (int, optional): Dots per inch for the saved figure. Higher values result in
            better image quality. Defaults to 300.
        figure_size (tuple[float, float], optional): Tuple representing the figure size in inches
            (width, height). Defaults to `(19, 21)`.

    Returns:
        tuple[Figure, Axes]: Matplotlib Figure and Axes objects.

    Behavior:
        - Non-selected tiles are drawn with a yellow outline.
        - Selected tiles are filled with red and outlined in black.
        - If multiple tiles are selected (e.g., a path), the first and last tiles are filled
          with green and outlined in black.

    Example:
        >>> plot_map_tiles_selected(
        ...     map_name="de_dust2",
        ...     selected_tiles=[5, 12, 18],
        ...     outpath="./maps/selected_tiles_de_dust2.png",
        ...     dpi=800,
        ...     figure_size=(15, 20)
        ... )
        # Saves the plot to './maps/selected_tiles_de_dust2.png'

        >>> plot_map_tiles_selected(
        ...     map_name="de_dust2",
        ...     selected_tiles=[5, 12, 18]
        ... )
        # Displays the plot with the default figure size
    """
    fig, axis = awpy.plot.plot(map_name=map_name)
    fig.set_size_inches(*figure_size)
    _plot_selected_tiles(map_name, axis, selected_tiles)

    # Handle outpath for both str and Path inputs
    if outpath is not None:
        outpath = Path(outpath)
        outpath.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directory exists
        plt.savefig(outpath, bbox_inches="tight", dpi=dpi)
        logger.debug(f"The visualization has been saved at {outpath.resolve()}")

    return fig, axis
