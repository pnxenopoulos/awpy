"""Functions for plotting player positions and nades.

    Typical usage example:

    from awpy.visualization.plot import plot_round
    plot_round("best_round_ever.gif", d["gameRounds"][7]["frames"], map_name=d["mapName"], map_type="simpleradar", dark=False)

    https://github.com/pnxenopoulos/awpy/blob/main/examples/02_Basic_CSGO_Visualization.ipynb
"""
import os
import shutil
from typing import Optional, Literal, cast
import numpy as np
import imageio
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib as mpl
from awpy.data import MAP_DATA
from awpy.types import GameFrame, GameRound


def plot_map(
    map_name: str = "de_dust2", map_type: str = "original", dark: bool = False
) -> tuple[plt.Figure, plt.Axes]:
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
        map_bg = imageio.imread(base_path + ".png")
        if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
            map_bg_lower = imageio.imread(base_path + "_lower.png")
            map_bg = np.concatenate([map_bg, map_bg_lower])
    else:
        try:
            col = "light"
            if dark:
                col = "dark"
            map_bg = imageio.imread(base_path + f"_{col}.png")
            if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
                map_bg_lower = imageio.imread(base_path + f"_lower_{col}.png")
                map_bg = np.concatenate([map_bg, map_bg_lower])
        except FileNotFoundError:
            map_bg = imageio.imread(base_path + ".png")
            if map_name in MAP_DATA and "z_cutoff" in MAP_DATA[map_name]:
                map_bg_lower = imageio.imread(base_path + "_lower.png")
                map_bg = np.concatenate([map_bg, map_bg_lower])
    fig, ax = plt.subplots()
    ax.imshow(map_bg, zorder=0)
    return fig, ax


# Position function courtesy of PureSkill.gg
def position_transform(
    map_name: str, position: float, axis: Literal["x", "y"]
) -> float:
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
        raise ValueError(f"'axis' has to be 'x' or 'y' not {axis}")
    start = MAP_DATA[map_name]["pos_" + axis]
    scale = MAP_DATA[map_name]["scale"]
    if axis == "x":
        pos = position - start
        pos /= scale
        return pos
    elif axis == "y":
        pos = start - position
        pos /= scale
        return pos
    raise ValueError(f"'axis' has to be 'x' or 'y' not {axis}")


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
    start_x = MAP_DATA[map_name]["pos_x"]
    start_y = MAP_DATA[map_name]["pos_y"]
    scale = MAP_DATA[map_name]["scale"]
    x = position[0] - start_x
    x /= scale
    y = start_y - position[1]
    y /= scale
    z = position[2]
    if "z_cutoff" in MAP_DATA[map_name] and z < MAP_DATA[map_name]["z_cutoff"]:
        y += 1024
    return (x, y, z)


def plot_positions(
    positions: Optional[list[tuple[float, float]]] = None,
    colors: Optional[list[str]] = None,
    markers: Optional[list[str]] = None,
    alphas: Optional[list[float]] = None,
    sizes: Optional[list[float]] = None,
    map_name: str = "de_ancient",
    map_type: str = "original",
    dark: bool = False,
    apply_transformation: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Plots player positions

    Args:
        positions (list, optional): List of lists of length 2 ([[x,y], ...])
            Defaults to []
        colors (list, optional): List of colors for each player
            Defaults to []
        markers (list, optional): List of marker types for each player
            Defaults to []
        alphas (list, optional): List of alpha values for each player
            Defaults to [1.0] * len(positions)
        sizes (list, optional): List of marker sizes for each player
            Defaults to [mpl.rcParams["lines.markersize"] ** 2] * len(positions)
        map_name (string, optional): Map to search. Defaults to "de_ancient"
        map_type (string, optional): "original" or "simpleradar". Defaults to "original"
        dark (bool, optional): Only for use with map_type="simpleradar".
            Indicates if you want to use the SimpleRadar dark map type
            Defaults to False
        apply_transformation (bool, optional): Indicates if you need to also use position_transform() for the X/Y coordinates
            Defaults to False

    Returns:
        matplotlib fig and ax
    """
    if positions is None:
        positions = []
    if colors is None:
        colors = []
    if markers is None:
        markers = []
    if alphas is None:
        alphas = [1.0] * len(positions)
    if sizes is None:
        sizes = [mpl.rcParams["lines.markersize"] ** 2] * len(positions)
    f, a = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for p, c, m, alpha, s in zip(positions, colors, markers, alphas, sizes):
        if apply_transformation:
            a.scatter(
                x=position_transform(map_name, p[0], "x"),
                y=position_transform(map_name, p[1], "y"),
                c=c,
                marker=m,
                alpha=alpha,
                s=s,
            )
        else:
            a.scatter(x=p[0], y=p[1], c=c, marker=m, alpha=alpha, s=s)
    a.get_xaxis().set_visible(False)
    a.get_yaxis().set_visible(False)
    return f, a


def plot_round(
    filename: str,
    frames: list[GameFrame],
    map_name: str = "de_ancient",
    map_type: str = "original",
    dark: bool = False,
    fps: int = 10,
) -> Literal[True]:
    """Plots a round and saves as a .gif. CTs are blue, Ts are orange, and the bomb is an octagon. Only use untransformed coordinates.

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
    image_files = []
    for i, f in tqdm(enumerate(frames)):
        positions = []
        colors = []
        markers = []
        # Plot bomb
        # Thanks to https://github.com/pablonieto0981 for adding this code!
        if f["bomb"]:
            colors.append("orange")
            markers.append("8")
            pos = (
                position_transform(map_name, f["bomb"]["x"], "x"),
                position_transform(map_name, f["bomb"]["y"], "y"),
            )
            positions.append(pos)
        else:
            pass
        # Plot players
        for side in ["ct", "t"]:
            side = cast(Literal["ct", "t"], side)
            for p in f[side]["players"] or []:
                if side == "ct":
                    colors.append("cyan")
                else:
                    colors.append("red")
                if p["hp"] == 0:
                    markers.append("x")
                else:
                    markers.append(".")
                pos = (
                    position_transform(map_name, p["x"], "x"),
                    position_transform(map_name, p["y"], "y"),
                )
                positions.append(pos)
        fig, _ = plot_positions(
            positions=positions,
            colors=colors,
            markers=markers,
            map_name=map_name,
            map_type=map_type,
            dark=dark,
        )
        image_files.append(f"csgo_tmp/{i}.png")
        fig.savefig(image_files[-1], dpi=300, bbox_inches="tight")
        plt.close()
    images = []
    for file in image_files:
        images.append(imageio.imread(file))
    imageio.mimsave(filename, images, fps=fps)
    shutil.rmtree("csgo_tmp/")
    return True


def plot_nades(
    rounds: list[GameRound],
    nades: Optional[list[str]] = None,
    side: str = "CT",
    map_name: str = "de_ancient",
    map_type: str = "original",
    dark: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
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
    f, a = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for r in rounds:
        if r["grenades"]:
            for g in r["grenades"]:
                if g["throwerSide"] == side:
                    start_x = position_transform(map_name, g["throwerX"], "x")
                    start_y = position_transform(map_name, g["throwerY"], "y")
                    end_x = position_transform(map_name, g["grenadeX"], "x")
                    end_y = position_transform(map_name, g["grenadeY"], "y")
                    if g["grenadeType"] in nades:
                        if (
                            g["grenadeType"] == "Incendiary Grenade"
                            or g["grenadeType"] == "Molotov"
                        ):
                            a.plot([start_x, end_x], [start_y, end_y], color="red")
                            a.scatter(end_x, end_y, color="red")
                        if g["grenadeType"] == "Smoke Grenade":
                            a.plot([start_x, end_x], [start_y, end_y], color="gray")
                            a.scatter(end_x, end_y, color="gray")
                        if g["grenadeType"] == "HE Grenade":
                            a.plot([start_x, end_x], [start_y, end_y], color="green")
                            a.scatter(end_x, end_y, color="green")
                        if g["grenadeType"] == "Flashbang":
                            a.plot([start_x, end_x], [start_y, end_y], color="gold")
                            a.scatter(end_x, end_y, color="gold")
    a.get_xaxis().set_visible(False)
    a.get_yaxis().set_visible(False)
    return f, a
