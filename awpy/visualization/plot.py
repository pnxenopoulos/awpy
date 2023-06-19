"""Functions for plotting player positions and nades.

Example::

    from awpy.visualization.plot import plot_round

    plot_round(
        "best_round_ever.gif",
        d["gameRounds"][7]["frames"],
        map_name=d["mapName"],
        map_type="simpleradar",
        dark=False,
    )

https://github.com/pnxenopoulos/awpy/blob/main/examples/02_Basic_CSGO_Visualization.ipynb
"""
import os
import shutil
from typing import Literal

import imageio.v3 as imageio
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from tqdm import tqdm

from awpy.data import MAP_DATA
from awpy.types import BombInfo, GameFrame, GameRound, PlayerInfo, PlotPosition


def plot_map(
    map_name: str = "de_dust2", map_type: str = "original", *, dark: bool = False
) -> tuple[Figure, Axes]:
    """Plots a blank map.

    Args:
        map_name (string, optional): Map to search. Defaults to "de_dust2"
        map_type (string, optional): "original" or "simpleradar". Defaults to "original"
        dark (bool, optional): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type
            Defaults to False

    Returns:
        matplotlib fig and ax
    """
    base_path = os.path.join(os.path.dirname(__file__), f"""../data/map/{map_name}""")
    if map_type == "original":
        map_bg = imageio.imread(f"{base_path}.png")
        if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
            map_bg_lower = imageio.imread(f"{base_path}_lower.png")
            map_bg = np.concatenate([map_bg, map_bg_lower])
    else:
        try:
            col = "dark" if dark else "light"
            map_bg = imageio.imread(f"{base_path}_{col}.png")
            if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
                map_bg_lower = imageio.imread(f"{base_path}_lower_{col}.png")
                map_bg = np.concatenate([map_bg, map_bg_lower])
        except FileNotFoundError:
            map_bg = imageio.imread(f"{base_path}.png")
            if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
                map_bg_lower = imageio.imread(f"{base_path}_lower.png")
                map_bg = np.concatenate([map_bg, map_bg_lower])
    figure, axes = plt.subplots()
    axes.imshow(map_bg, zorder=0)
    return figure, axes


# Position function courtesy of PureSkill.gg
def position_transform(
    map_name: str, position: float, axis: Literal["x", "y"]
) -> float:  # sourcery skip: use-fstring-for-concatenation
    """Transforms an X or Y coordinate.

    Args:
        map_name (string): Map to search
        position (float): X or Y coordinate
        axis (string): Either "x" or "y" (lowercase)

    Returns:
        float

    Raises:
        ValueError: Raises a ValueError if axis not 'x' or 'y'
    """
    if axis not in ["x", "y"]:
        msg = f"'axis' has to be 'x' or 'y' not {axis}"
        raise ValueError(msg)
    # Have to skip f-string for pyright to handle literal math
    start = MAP_DATA[map_name]["pos_" + axis]
    scale = MAP_DATA[map_name]["scale"]
    if axis == "x":
        pos = position - start
        pos /= scale
        return pos
    # axis: "y":
    pos = start - position
    pos /= scale
    return pos


def position_transform_all(
    map_name: str, position: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Transforms an X or Y coordinate.

    Args:
        map_name (string): Map to search
        position (tuple): (X,Y,Z) coordinates

    Returns:
        tuple
    """
    current_map_data = MAP_DATA[map_name]
    start_x = current_map_data["pos_x"]
    start_y = current_map_data["pos_y"]
    scale = current_map_data["scale"]
    x = position[0] - start_x
    x /= scale
    y = start_y - position[1]
    y /= scale
    z = position[2]
    if "z_cutoff" in current_map_data and z < current_map_data["z_cutoff"]:
        y += 1024
    return (x, y, z)


def plot_positions(
    positions: list[PlotPosition],
    map_name: str = "de_ancient",
    map_type: str = "original",
    *,
    dark: bool = False,
    apply_transformation: bool = False,
) -> tuple[Figure, Axes]:
    """Plots player positions.

    Args:
        positions (list[PlotPosition]): List of lists of plot positions containing:
            position (tuple[float, float]): Tuple of length 2 ([[x,y], ...])
            color (str): Color for the position
            marker (str): Marker for the position
            alpha (float): Alpha value for the position
            sizes (float): Size for the position
        map_name (string, optional): Map to search. Defaults to "de_ancient"
        map_type (string, optional): "original" or "simpleradar". Defaults to "original"
        dark (bool, optional): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type
            Defaults to False
        apply_transformation (bool, optional): Indicates if you need to also use
            position_transform() for the X/Y coordinates,
            Defaults to False

    Returns:
        matplotlib fig and ax
    """
    figure, axes = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for position in positions:
        if apply_transformation:
            x = position_transform(map_name, position.position[0], "x")
            y = position_transform(map_name, position.position[1], "y")

        else:
            x = position.position[0]
            y = position.position[1]
        axes.scatter(
            x=x,
            y=y,
            c=position.color,
            marker=position.marker,
            alpha=position.alpha,
            s=position.size,
        )
    axes.get_xaxis().set_visible(b=False)
    axes.get_yaxis().set_visible(b=False)
    return figure, axes


def _get_plot_position_for_player(
    player: PlayerInfo, side: Literal["ct", "t"], map_name: str
) -> PlotPosition:
    """Build a PlotPosition class for the given player.

    Args:
        player (PlayerInfo): Information about a player at a point in time.
        side (Literal["ct", "t"]): Side that the player is playing on.
        map_name (str): Map that the player is playing on.

    Returns:
        PlotPosition: Information needed to plot the player.
    """
    pos = (
        position_transform(map_name, player["x"], "x"),
        position_transform(map_name, player["y"], "y"),
    )
    color = "cyan" if side == "ct" else "red"
    marker = "x" if player["hp"] == 0 else "."
    return PlotPosition(position=pos, color=color, marker=marker)


def _get_plot_position_for_bomb(bomb: BombInfo, map_name: str) -> PlotPosition:
    """Build a PlotPosition class for the given player.

    Args:
        bomb (BombInfo): Information about a bomb at a point in time.
        map_name (str): Map that the bomb is playing on.

    Returns:
        PlotPosition: Information needed to plot the bomb.
    """
    pos = (
        position_transform(map_name, bomb["x"], "x"),
        position_transform(map_name, bomb["y"], "y"),
    )
    color = "orange"
    marker = "8"
    return PlotPosition(position=pos, color=color, marker=marker)


def plot_round(
    filename: str,
    frames: list[GameFrame],
    map_name: str = "de_ancient",
    map_type: str = "original",
    *,
    dark: bool = False,
    fps: int = 10,
) -> Literal[True]:
    """Plots a round and saves as a .gif.

    CTs are blue, Ts are orange, and the bomb is an octagon.
    Only use untransformed coordinates.

    Args:
        filename (string): Filename to save the gif
        frames (list): List of frames from a parsed demo
        map_name (string, optional): Map to search. Defaults to "de_ancient"
        map_type (string, optional): "original" or "simpleradar". Defaults to "original
        dark (bool, optional): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type
            Defaults to False
        fps (int, optional): Number of frames per second in the gif
            Defaults to 10

    Returns:
        True, saves .gif
    """
    if os.path.isdir("csgo_tmp"):
        shutil.rmtree("csgo_tmp/")
    os.mkdir("csgo_tmp")
    image_files: list[str] = []
    for i, game_frame in tqdm(enumerate(frames)):
        positions = [_get_plot_position_for_bomb(game_frame["bomb"], map_name)]
        # Plot players
        for side in ("ct", "t"):
            positions.extend(
                _get_plot_position_for_player(player, side, map_name)
                for player in game_frame[side]["players"] or []
            )
        figure, _ = plot_positions(
            positions=positions,
            map_name=map_name,
            map_type=map_type,
            dark=dark,
        )
        image_files.append(f"csgo_tmp/{i}.png")
        figure.savefig(image_files[-1], dpi=300, bbox_inches="tight")
        plt.close()
    images = [imageio.imread(file) for file in image_files]
    imageio.imwrite(filename, images, duration=1000 / fps)
    shutil.rmtree("csgo_tmp/")
    return True


def plot_nades(
    rounds: list[GameRound],
    nades: list[str] | None = None,
    side: str = "CT",
    map_name: str = "de_ancient",
    map_type: str = "original",
    *,
    dark: bool = False,
) -> tuple[Figure, Axes]:
    """Plots grenade trajectories.

    Args:
        rounds (list): List of round objects from a parsed demo
        nades (list, optional): List of grenade types to plot
            Defaults to []
        side (string, optional): Specify side to plot grenades. Either "CT" or "T".
            Defaults to "CT"
        map_name (string, optional): Map to search. Defaults to "de_ancient"
        map_type (string, optional): "original" or "simpleradar". Defaults to "original"
        dark (bool, optional): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type.
            Defaults to False

    Returns:
        matplotlib fig and ax
    """
    if nades is None:
        nades = []
    figure, axes = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for game_round in rounds:
        if game_round["grenades"] is None:
            continue
        for grenade_action in game_round["grenades"]:
            if (
                grenade_action["throwerSide"] == side
                and grenade_action["grenadeType"] in nades
            ):
                start_x = position_transform(map_name, grenade_action["throwerX"], "x")
                start_y = position_transform(map_name, grenade_action["throwerY"], "y")
                end_x = position_transform(map_name, grenade_action["grenadeX"], "x")
                end_y = position_transform(map_name, grenade_action["grenadeY"], "y")
                g_color = {
                    "Incendiary Grenade": "red",
                    "Molotov": "red",
                    "Smoke Grenade": "gray",
                    "HE Grenade": "green",
                    "Flashbang": "gold",
                }[grenade_action["grenadeType"]]
                axes.plot([start_x, end_x], [start_y, end_y], color=g_color)
                axes.scatter(end_x, end_y, color=g_color)
    axes.get_xaxis().set_visible(b=False)
    axes.get_yaxis().set_visible(b=False)
    return figure, axes
