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
import logging
import os
import shutil
from typing import Literal

import cv2
import imageio.v3 as imageio
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from tqdm import tqdm

from awpy.analytics.map_control import (
    calc_frame_map_control_metric,
    calc_parsed_frame_map_control_values,
    extract_teams_metadata,
)
from awpy.data import MAP_DATA, NAV
from awpy.types import (
    BombInfo,
    FrameMapControlValues,
    FrameTeamMetadataDict,
    FrameTeamMetadataObject,
    GameFrame,
    GameRound,
    PlayerInfo,
    PlotPosition,
    TeamMapControlValuesDict,
    lower_side,
)
from awpy.visualization import (
    SIDE_COLORS,
)


def plot_map(
    map_name: str = "de_dust2", map_type: str = "original", *, dark: bool = False
) -> tuple[Figure, Axes]:
    """Plots a blank map.

    Args:
        map_name (str, optional): Map to search. Defaults to "de_dust2"
        map_type (str, optional): "original" or "simpleradar". Defaults to "original"
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
        map_name (str): Map to search
        position (float): X or Y coordinate
        axis (str): Either "x" or "y" (lowercase)

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
        map_name (str): Map to search
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
        map_name (str, optional): Map to search. Defaults to "de_ancient"
        map_type (str, optional): "original" or "simpleradar". Defaults to "original"
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
        filename (str): Filename to save the gif
        frames (list): List of frames from a parsed demo
        map_name (str, optional): Map to search. Defaults to "de_ancient"
        map_type (str, optional): "original" or "simpleradar". Defaults to "original
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
        side (str, optional): Specify side to plot grenades. Either "CT" or "T".
            Defaults to "CT"
        map_name (str, optional): Map to search. Defaults to "de_ancient"
        map_type (str, optional): "original" or "simpleradar". Defaults to "original"
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


def _plot_frame_team_player_positions(
    map_name: str,
    side: Literal["CT", "T"],
    player_data: FrameTeamMetadataDict,
    axes: plt.Axes,
) -> None:
    transformed_x = [
        position_transform(map_name, loc[0], "x")
        for loc in player_data["alive_player_locations"]
    ]
    transformed_y = [
        position_transform(map_name, loc[1], "y")
        for loc in player_data["alive_player_locations"]
    ]
    side_color = SIDE_COLORS[lower_side(side)]
    color_arr = [side_color] * len(player_data["alive_player_locations"])
    axes.scatter(transformed_x, transformed_y, c=color_arr)


def _plot_map_control_snapshot_helper(
    map_name: str,
    ct_tiles: TeamMapControlValuesDict,
    t_tiles: TeamMapControlValuesDict,
    axes: plt.Axes,
    player_data: FrameTeamMetadataObject | None = None,
) -> None:
    """Helper function to plot map control nav tile plot.

    Args:
        map_name (str): Map used position_transform call
        ct_tiles (dict): CT map control values dictionary
        t_tiles (dict): T map control values dictionary
        axes (plt.axes): axes object for plotting
        player_data (FrameTeamMetadataObject): Dictionary of player positions
            for each team. Expected format same as output of extract_player_positions

    Returns: Nothing, all plotting is done on ax object
    """
    ct_tile_set, t_tile_set = set(ct_tiles.keys()), set(t_tiles.keys())
    all_tiles = ct_tile_set.union(t_tile_set)

    # Iterate through the tiles that have a value
    for tile in all_tiles:
        if tile in NAV[map_name]:
            area = NAV[map_name][tile]

            width = position_transform(
                map_name, area["southEastX"], "x"
            ) - position_transform(map_name, area["northWestX"], "x")
            height = position_transform(
                map_name, area["northWestY"], "y"
            ) - position_transform(map_name, area["southEastY"], "y")

            # Use max value (default value 0 if no values exist)
            # for each side for the current tile
            ct_val = max(ct_tiles[tile], default=0)
            t_val = max(t_tiles[tile], default=0)

            """
            Map T/CT Val to RGB Color.
            If CT Val is non-zero and T Val is 0, color will be Green
            If T Val is non-zero and CT Val is 0, color will be Red
            If T and CT Val are non-zero, color is weighted average
            between Green and Red.
            """
            cur_color = min(ct_val / (ct_val + t_val), ct_val) * np.array(
                [0, 1, 0]
            ) + min(t_val / (ct_val + t_val), t_val) * np.array([1, 0, 0])

            cur_color = (ct_val / (ct_val + t_val)) / 5 * np.array([0, 1, 0]) + (
                t_val / (ct_val + t_val) / 5
            ) * np.array([1, 0, 0])

            cur_color = ct_val * np.array([0, 1, 0]) + t_val * np.array([1, 0, 0])

            rect = patches.Rectangle(
                (
                    position_transform(map_name, area["northWestX"], "x"),
                    position_transform(map_name, area["southEastY"], "y"),
                ),
                width,
                height,
                linewidth=1,
                edgecolor=cur_color,
                facecolor=cur_color,
                alpha=1.0,
            )
            axes.add_patch(rect)
        else:
            log_message = "Tile not found in map:" + tile
            logging.info(log_message)

    # Plot player positions if given
    if player_data is not None:
        _plot_frame_team_player_positions(map_name, "CT", player_data["ct"], axes)
        _plot_frame_team_player_positions(map_name, "T", player_data["t"], axes)

    axes.axis("off")


def plot_map_control_snapshot(
    map_name: str,
    tile_values: FrameMapControlValues,
    player_pos: FrameTeamMetadataObject | None = None,
    given_fig_ax: tuple[plt.Figure, plt.Axes] | tuple[None, None] = (None, None),
    save_filepath: str = "",
) -> None:
    """Visualize map control for given ct/t map control value dictionaries.

    Args:
        map_name (str): Map used position_transform call
        tile_values (dict): List with map control values dictionary for both sides
            Expected format = [CT Dict, T Dict]
        player_pos (dict): Dictionary of player positions for each team.
            Expected format same as output of extract_player_positions
        given_fig_ax: Optional tuple containing figure and ax objects for plotting
        save_filepath (str) : Filepath to save the figure to file if required

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    ct_tiles, t_tiles = tile_values["ct"], tile_values["t"]
    figure, base_ax = given_fig_ax
    if figure is None:
        figure, base_ax = plot_map(map_name=map_name, map_type="simpleradar", dark=True)
    _plot_map_control_snapshot_helper(
        map_name, ct_tiles, t_tiles, base_ax, player_data=player_pos
    )
    if save_filepath:
        figure.savefig(fname=save_filepath, bbox_inches="tight", dpi=400)
        plt.close(figure)
    elif not given_fig_ax[0]:
        plt.show(figure)


def plot_frame_map_control(
    map_name: str,
    frame: GameFrame,
    plot_type: str = "",
    given_fig_ax: tuple[plt.Figure, plt.Axes] | tuple[None, None] = (None, None),
    save_filepath: str = "",
) -> None:
    """Visualize map control for awpy frame.

    Args:
        map_name (str): Map used position_transform call
        frame (GameFrame): awpy frame to calculate map control for
        plot_type (str): Determines which type of plot is created
            (either with or without players)
        given_fig_ax: Optional tuple containing figure and ax objects for plotting
        save_filepath (str): Filepath to save the figure to file if required

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    player_positions = extract_teams_metadata(frame)
    map_control_dict = calc_parsed_frame_map_control_values(map_name, player_positions)
    if plot_type == "players":
        plot_map_control_snapshot(
            map_name,
            map_control_dict,
            player_pos=player_positions,
            given_fig_ax=given_fig_ax,
            save_filepath=save_filepath,
        )
    else:
        plot_map_control_snapshot(
            map_name,
            map_control_dict,
            given_fig_ax=given_fig_ax,
            save_filepath=save_filepath,
        )


def create_round_map_control_gif(
    map_name: str,
    round_data: GameRound,
    plot_type: str = "",
    gif_filepath: str = "./results/round_mc.gif",
) -> None:
    """Create gif summarizing map control for round.

    Args:
        map_name (str): Map used in plot_frame_map_control call
        round_data (GameRound): Round whose map control will be animated.
            Expected format that of awpy round
        plot_type (str): Determines which type of plot is created
            (either with or without players)
        gif_filepath (str): Filepath to save the gif to file

    Returns: Nothing, all plotting is done on ax object

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
                    If roundData not of expected
                    awpy frame format
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)
    if "tmp" not in os.listdir():
        error_string = (
            "Frame visualizations cannot be saved to the"
            "./tmp folder - it does not exist"
        )
        raise ValueError(error_string)

    images: list[np.ndarray] = []
    print("Saving/loading frames")
    frames = round_data["frames"]
    i = 0
    for frame in frames or []:
        filename = f"./tmp/tmp{i}.png"

        # Save current frame map control viz to file
        # All frames are saved to './tmp/ folder '
        plot_frame_map_control(
            map_name,
            frame,
            plot_type=plot_type,
            save_filepath=filename,
        )

        # Load image back as frame of gif that will
        # be created at the end of this function
        cur_img = imageio.imread(filename)
        images.append(cur_img)

        i += 1

    print("Creating gif!")
    imageio.imwrite(gif_filepath, images)


def _plot_map_control_metrics_helper(
    metrics: list[float],
    axes: plt.Axes,
) -> None:
    """Helper function to plot map control metrics.

    Args:
        metrics (list): List containing map control values to plot
        axes (axes): axes object for plotting

    Returns: Nothing, all plotting is done on ax_object
    """
    x = list(range(1, len(metrics) + 1))
    axes.plot(x, metrics)
    axes.set_ylim(0, 1)
    axes.axhline(y=0.5, linestyle="--", c="k")
    axes.set_ylabel("Map Control Metric Value")
    axes.set_xlabel("Frame Number")
    axes.set_title("Map Control Metric Progress")
    x_tick_threshold = 10
    if len(metrics) > x_tick_threshold:
        step_size = int(len(metrics) // x_tick_threshold)
        axes.set_xticks(list(range(1, len(metrics) + 1, step_size)))


def plot_map_control_metrics(
    metric_arr: list[float],
    given_fig_ax: tuple[plt.Figure, plt.Axes] | tuple[None, None] = (None, None),
) -> None:
    """Function to plot given map control metrics.

    Args:
        metric_arr (list): List containing map control values to plot
        given_fig_ax (tuple): Fig and ax objects if given

    Returns: Plot given map control metric values onto axes object

    Raises:
        ValueError: If metrics is empty
    """
    if not metric_arr:
        msg = "Metrics is empty."
        raise ValueError(msg)

    if given_fig_ax[0] is not None:
        _plot_map_control_metrics_helper(metric_arr, given_fig_ax[1])
    else:
        _, curr_ax = plt.subplots()
        _plot_map_control_metrics_helper(metric_arr, curr_ax)
        plt.show()


def _save_map_control_graphic_helper(
    map_name: str,
    frame: GameFrame,
    metrics: list[float],
    save_path: str = "",
) -> None:
    """Helper function to generate map control graphic for awpy round.

    Args:
        map_name (str): Map used in frame_map_control_metric call
        frame (GameFrame): awpy frame to create map control graphic
        metrics  (list): List containing map control values to plot
        save_path (str): Location where graphic should be saved on file
    """
    fig, axs = plt.subplots(1, 2, figsize=(12, 12))
    map_bg = plt.imread(f"../awpy/data/map/{map_name}_dark.png")
    axs[0].imshow(map_bg, zorder=0)
    plot_frame_map_control(
        map_name, frame, plot_type="players", given_fig_ax=(fig, axs[0])
    )
    _plot_map_control_metrics_helper(metrics, axs[1])
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
) -> None:
    """Function to generate map control gif for awpy round.

    Gif including minimap visualization
    and map control metric plot for each frame in the round.

    Args:
        map_name (str): Map used inframe_map_control_metric call
        frames (list): List of GameFrame for map control graphic
        save_path (str): Location where graphic should be saved on file

    Raises:
        ValueError: If map_name is not in awpy.data.NAV
    """
    if map_name not in NAV:
        msg = "Map not found."
        raise ValueError(msg)

    metrics: list[float] = []
    images: list[np.ndarray] = []

    print("Saving/loading frames!")
    for i, frame in enumerate(frames):
        metrics.append(calc_frame_map_control_metric(map_name, frame))
        temp_filename = f"./tmp/tmp{i!s}.png"
        _save_map_control_graphic_helper(
            map_name, frame, metrics, save_path=temp_filename
        )
        if save_path:
            # sometime second dimension has an extra entry
            # so resize to expected size
            cur_img = cv2.resize(imageio.imread(temp_filename), (4760, 4760))
            images.append(cur_img)
    if save_path:
        print("Saving map control graphic gif")
        imageio.imwrite(save_path, images)
