"""
   Utilities for plotting tiles on a map specifically.
   credit: @JanEric
"""

import importlib.resources
import json
import logging
import os
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.axes import Axes

from awpy.data.map_data import MAP_DATA
from awpy.plot.utils import game_to_pixel, position_transform
from awpy import Nav

NAV = {}
MAP_DIR = "../data/nav"
NAV['de_dust2'] = Nav(path="../../awpy/data/de_dust2")

def plot_map(map_name: str):
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
    """Convert an area’s corner coordinates to pixel coordinates."""
    # Note: 'de_dust2' is hard-coded as in your original code.
    return [game_to_pixel('de_dust2', (c["x"], c["y"], c["z"]))[0:2] for c in area_dict["corners"]]

def _plot_tile(axis: Axes, polygon: list, edgecolor: str, facecolor: str, linewidth: int = 1) -> None:
    """Add a single tile patch to the axis."""
    patch = patches.Polygon(polygon, linewidth=linewidth, edgecolor=edgecolor, facecolor=facecolor)
    axis.add_patch(patch)

def _plot_all_tiles(map_dict: 'Nav', axis: Axes, default_fill: str = "None") -> None:
    """Plot every tile with a yellow outline and optional fill color."""
    for area in map_dict.areas.values():
        area_dict = area.to_dict()
        polygon = _tile_polygon(area_dict)
        _plot_tile(axis, polygon, edgecolor="yellow", facecolor=default_fill)

def _plot_selected_tiles(map_dict: 'Nav', axis: Axes, selected_tiles: list, fill: str) -> None:
    """
    Plot all tiles, highlighting the selected ones.
    
    - Tiles not in the selected list are drawn with a yellow outline and no fill.
    - Tiles in the selected list are filled with the specified color.
    - If multiple tiles are selected (a path), the first and last tiles are outlined in black.
    """
    # Using a set for quick membership tests.
    selected_set = set(selected_tiles)
    
    for tile_id, area in map_dict.areas.items():
        area_dict = area.to_dict()
        polygon = _tile_polygon(area_dict)
        if tile_id in selected_set:
            '''
            If just one tile is passed in to visualize, it is filled in red with white edges.
            If a list of lenth > 1 is passdd in (a path), then the first and last tiles are filled in green with white edges. All other tiles are filled in red with white edges.
            All tiles not in the passed in list are colored with no fill and yellow edges.
            '''
            if len(selected_tiles) > 1 and (tile_id == selected_tiles[0] or tile_id == selected_tiles[-1]):
                edgecolor = "black"
                facecolor = 'green'
            else:
                edgecolor = "black"
                facecolor = 'red'
        else:
            facecolor = "None"
            edgecolor = "yellow"
        _plot_tile(axis, polygon, edgecolor=edgecolor, facecolor=facecolor)

def plot_map_tiles(output_path: str, map_name: str = "de_ancient", map_type: str = "original",
                   *, dark: bool = False, dpi: int = 1000, fill: str = "None") -> None:
    """
    Plot all navigation mesh tiles in a given map.
    
    Non-selected tiles are drawn with a yellow outline.
    """
    fig, axis = plot_map(map_name=map_name)
    fig.set_size_inches(19.2, 21.6)
    _plot_all_tiles(NAV[map_name], axis, default_fill=fill)
    plt.show()
    # Optionally save the figure:
    # plt.savefig(os.path.join(output_path, f"tiles_{map_name}.png"), bbox_inches="tight", dpi=dpi)
    fig.clear()
    plt.close()

def plot_map_tiles_selected(output_path: str, map_name: str, selected_tiles: list, *,
                            fill: str = "red", dpi: int = 1000) -> None:
    """
    Plot navigation mesh tiles with selected tiles highlighted.
    
    Args:
        output_path (str): Path to the output folder.
        map_name (str): Name of the map.
        selected_tiles (list): List of tile IDs to be highlighted.
        fill (str, optional): Fill color for selected tiles (default is "red").
        dpi (int, optional): DPI for the output image.
    
    Behavior:
        - Tiles not in the list are drawn with a yellow outline.
        - Tiles in the list are filled with the specified fill color.
        - If more than one tile is selected (a path), the first and last
          (source and destination) tiles have an edge color of black.
    """
    fig, axis = plot_map(map_name=map_name)
    fig.set_size_inches(19.2, 21.6)
    _plot_selected_tiles(NAV[map_name], axis, selected_tiles, fill)
    plt.show()
    # Optionally save the figure:
    # plt.savefig(os.path.join(output_path, f"selected_tiles_{map_name}.png"), bbox_inches="tight", dpi=dpi)
    fig.clear()
    plt.close()
