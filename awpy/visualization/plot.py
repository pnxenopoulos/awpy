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

from matplotlib import patches, axes
from awpy.analytics.map_control import (
    parseRoundFrame,
    calcMapControlHelper,
    frame_map_control_metric,
)


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

def plot_map_control_snapshot_helper(
    map_name: str,
    ct_tiles: dict,
    t_tiles: dict,
    ax: axes,
    player_data: dict = {},
):
    """Helper function to plot map control nav tile plot on given
        matplotlib.axes object
    Args:
        map_name (string)       : Map used position_transform call
        ct_tiles (dict)         : CT map control values dictionary
        t_tiles (dict)          : T map control values dictionary
        ax (matplotlib.axes)    : axes object for plotting
        player_dict (dict)      : Dictionary of player positions
                                  for each team. Expected format
                                  same as output of parseRoundFrame

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If player_dict not of expected
                    parseRoundFrame output format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if player_data and ("t" not in player_data or "ct" not in player_data):
        raise ValueError("player_dict not of expected parseRoundFrame output format.")

    ctTileLocs, tTileLocs = set(ct_tiles.keys()), set(t_tiles.keys())
    allRelevantTiles = ctTileLocs.union(tTileLocs)

    # Iterate through the tiles that have a value
    for curTile in allRelevantTiles:
        if curTile in NAV[map_name]:
            area = NAV[map_name][curTile]
            tmpSE_X = position_transform(map_name, area["southEastX"], "x")
            tmpNW_X = position_transform(map_name, area["northWestX"], "x")
            tmpSE_Y = position_transform(map_name, area["southEastY"], "y")
            tmpNW_Y = position_transform(map_name, area["northWestY"], "y")
            width = tmpSE_X - tmpNW_X
            height = tmpNW_Y - tmpSE_Y
            southwest_x = tmpNW_X
            southwest_y = tmpSE_Y

            # Use max value (if exists) for each side for the current tile
            tileCTValue, tileTValue = max(ct_tiles[curTile] + [0]), max(
                t_tiles[curTile] + [0]
            )

            # Use each side's value above as weights for weighted average
            # to find correct color
            curColor = min(
                tileCTValue / (tileCTValue + tileTValue), tileCTValue
            ) * np.array([0, 1, 0]) + min(
                tileTValue / (tileCTValue + tileTValue), tileTValue
            ) * np.array(
                [1, 0, 0]
            )

            rect = patches.Rectangle(
                (southwest_x, southwest_y),
                width,
                height,
                linewidth=1,
                edgecolor=curColor,
                facecolor=curColor,
                alpha=1.0,
            )
            ax.add_patch(rect)
        else:
            print("Tile not found in map:", curTile)

    # Plot player positions if given
    if len(player_data) > 0:
        tPlayerPositions, ctPlayerPositions = (
            player_data["t"]["player-locations"],
            player_data["ct"]["player-locations"],
        )
        if len(tPlayerPositions) > 0:
            transformedX = [
                position_transform(map_name, loc[0], "x") for loc in tPlayerPositions
            ]
            transformedY = [
                position_transform(map_name, loc[1], "y") for loc in tPlayerPositions
            ]
            colorArr = ["#5d79ae"] * len(tPlayerPositions)
            ax.scatter(transformedX, transformedY, c=colorArr)
        if len(ctPlayerPositions) > 0:
            colorArr = ["#de9b35"] * len(ctPlayerPositions)
            transformedX = [
                position_transform(map_name, loc[0], "x") for loc in ctPlayerPositions
            ]
            transformedY = [
                position_transform(map_name, loc[1], "y") for loc in ctPlayerPositions
            ]
            ax.scatter(transformedX, transformedY, c=colorArr)
    ax.axis("off")


def plot_map_control_snapshot(
    map_name: str,
    ct_tiles: dict,
    t_tiles: dict,
    player_pos: dict = {},
    given_fig_ax: tuple[plt.Figure, axes] = (None, None),
    save_filepath: str = "",
):
    """Visualize map control for given ct/t map control value
        dictionaries. Tile values are mapped to RGB colors and then
        plotted. Plot player positions also if given.
    Args:
        map_name (string)       : Map used position_transform call
        ct_tiles (dict)         : CT map control values dictionary
        t_tiles (dict)          : T map control values dictionary
        player_pos (dict)       : Dictionary of player positions
                                  for each team. Expected format
                                  same as output of parseRoundFrame
        save_filepath (str)     : Filepath to save the figure to file
                                  if required

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

        # if not useAx[0]:
    if not given_fig_ax[0]:
        f, baseAx = plot_map(map_name=map_name, map_type="simpleradar", dark=True)
    else:
        f, baseAx = given_fig_ax
    plot_map_control_snapshot_helper(
        map_name, ct_tiles, t_tiles, ax=baseAx, player_data=player_pos
    )

    if len(save_filepath) > 0:
        f.savefig(fname=save_filepath, bbox_inches="tight", dpi=400)
        plt.close(f)
    elif not given_fig_ax[0]:
        plt.show(f)


def plot_frame_map_control(
    map_name: str,
    frame: dict,
    players_plotted: bool = False,
    given_fig_ax: tuple[plt.Figure, axes] = (None, None),
    save_filepath: str = "",
):
    # returnWanted=False, save = (False, ), axWanted=(False, )):
    """Visualize map control given awpy frame data structure.
        Plot player positions also if necessary.
    Args:
        map_name (string)       : Map used position_transform call
        frame (dict)            : awpy frame to calculate map
                                  control for
        players_plotted (bool)  : Boolean for whether alive players
                                  should be plotted
        save_filepath (str)     : Filepath to save the figure to file
                                  if required

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

    parsedData = parseRoundFrame(frame)
    mapControlDict = calcMapControlHelper(map_name, parsedData, True)
    if players_plotted:
        plot_map_control_snapshot(
            map_name,
            mapControlDict["ct"],
            mapControlDict["t"],
            player_pos=parsedData,
            given_fig_ax=given_fig_ax,
            save_filepath=save_filepath,
        )
    else:
        plot_map_control_snapshot(
            map_name,
            mapControlDict["ct"],
            mapControlDict["t"],
            given_fig_ax=given_fig_ax,
            save_filepath=save_filepath,
        )


def create_round_map_control_gif(
    map_name: str,
    round_data: dict,
    players_plotted: bool = False,
    gif_filepath: str = "./results/round_mc.gif",
):
    """Create gif summarizing map control for round by
        animating frame visualizations. Plot player
        positions also if necessary.
    Args:
        map_name (string)       : Map used in plot_frame_map_control
                                  call
        round_data (dict)       : Round whose map control will be
                                  animated. Expected format that
                                  of awpy round
                                      ex: demo['gameRounds'][i]
        players_plotted (bool)  : Boolean for whether alive players
                                  should be plotted
        gif_filepath (str)      : Filepath to save the gif to file

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If roundData not of expected
                    awpy frame format
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if "frames" not in round_data:
        raise ValueError("round_data argument not of expected awpy round format.")
    if "tmp" not in os.listdir():
        raise ValueError(
            "Frame visualizations cannot be saved to the ./tmp folder - it does not exist"
        )

    images = []
    print("Saving/loading frames")
    for i in range(len(round_data["frames"])):
        frame = round_data["frames"][i]
        currentFilename = "./tmp/tmp" + str(i) + ".png"

        # Save current frame map control viz to file
        # All frames are saved to './tmp/ folder '
        plot_frame_map_control(
            map_name,
            frame,
            players_plotted=players_plotted,
            save_filepath=currentFilename,
        )

        # Load image back as frame of gif that will
        # be created at the end of this function
        images.append(imageio.imread(currentFilename))

    print("Creating gif!")
    imageio.mimsave(gif_filepath, images)


def plot_map_control_metrics_helper(
    metrics: list[float],
    axObject: axes,
):
    """Helper function to plot map control metric plot
        onto given axes object
    Args:
        metrics (list)       : List containing map control values
                               to plot
        ax_object (axes)     : axes object for plotting

    Returns: Nothing, all plotting is done on ax_object

    Raises:
        ValueError: If metrics is empty
    """
    if not metrics:
        raise ValueError("Metrics is empty.")

    xArr = list(range(1, len(metrics) + 1))
    axObject.plot(xArr, metrics)  # , x=
    axObject.set_ylim(0, 1)
    axObject.axhline(0.5, linestyle="--", c="k")
    axObject.set_ylabel("Map Control Metric Value")
    axObject.set_xlabel("Frame Number")
    axObject.set_title("Map Control Metric Progress")
    if len(metrics) > 10:
        axObject.set_xticks(list(range(1, len(metrics) + 1, int(len(metrics) // 10))))


def plot_map_control_metrics(
    metric_arr=list[float],
    given_fig_ax: tuple[plt.Figure, axes] = (None, None),
    plotFig=False,
):
    """Function to plot given map control metrics
    Args:
        metric_arr (list)     : List containing map control values
                               to plot

    Returns: Plot given map control metric values onto axes
             object

    Raises:
        ValueError: If metrics is empty
    """

    if not metric_arr:
        raise ValueError("Metrics is empty.")

    if given_fig_ax[0]:
        plot_map_control_metrics_helper(metric_arr, given_fig_ax[1])
    else:
        f, curAx = plt.subplots()
        plot_map_control_metrics_helper(metric_arr, curAx)
        plt.show()


def map_control_graphic_helper(
    map_name: str,
    frame: GameFrame,
    metrics: list[float],
    save_path: str = "",
):
    """Helper function to generate map control graphic for given awpy
    round.
    Args:
        map_name (string)       : Map used in
                                  frame_map_control_metric call
        frame (GameFrame)       : awpy frame to create map
                                  control graphic
        save_path (string)      : Location where graphic should
                                  be saved on file

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

    fig, axs = plt.subplots(1, 2, figsize=(12, 12))
    map_bg = plt.imread("../awpy/data/map/" + map_name + "_dark.png")
    axs[0].imshow(map_bg, zorder=0)
    plot_frame_map_control(
        map_name, frame, players_plotted=True, given_fig_ax=(fig, axs[0])
    )
    plot_map_control_metrics_helper(metrics, axs[1])
    plt.tight_layout()
    if save_path:
        fig.savefig(fname=save_path, bbox_inches="tight", dpi=400)
    else:
        plt.show(fig)
    plt.close(fig)


def save_map_control_graphic(
    map_name: str,
    frames: list[GameFrame],
    save_path: str = "",
):
    """Function to generate map control graphic for given awpy
    round. Graphic is a gif including minimap visualization
    and map control metric plot for each frame in the round
    Args:
        map_name (string)       : Map used in
                                  frame_map_control_metric call
        frames (list)           : List of GameFrame for map
                                  control graphic
        save_path (string)      : Location where graphic should
                                  be saved on file

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")

    metricValues = []
    images = []

    print("Saving/loading frames!")
    for i in range(len(frames)):
        frame = frames[i]
        metricValues.append(frame_map_control_metric(map_name, frame))
        currentFilename = "./tmp/tmp" + str(i) + ".png"
        map_control_graphic_helper(
            map_name, frame, metricValues, save_path=currentFilename
        )
        if save_path:
            images.append(imageio.imread(currentFilename))
    if save_path:
        print("Saving map control graphic gif")
        imageio.mimsave(save_path, images)
