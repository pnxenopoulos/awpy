import os
import shutil
import imageio

import collections
from tqdm import tqdm
import logging
import matplotlib.pyplot as plt
import matplotlib as mpl

from awpy.data import MAP_DATA


def plot_map(map_name="de_dust2", map_type="original", dark=False):
    """Plots a blank map.

    Args:
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type

    Returns:
        matplotlib fig and ax
    """
    if map_type == "original":
        map_bg = imageio.imread(
            os.path.join(os.path.dirname(__file__), "")
            + """../data/map/{0}.png""".format(map_name)
        )
    else:
        col = "light"
        if dark:
            col = "dark"
        map_bg = imageio.imread(
            os.path.join(os.path.dirname(__file__), "")
            + """../data/map/{0}_{1}.png""".format(map_name, col)
        )
    fig, ax = plt.subplots()
    ax.imshow(map_bg, zorder=0)
    return fig, ax


# Position function courtesy of PureSkill.gg
def position_transform(map_name, position, axis):
    """Transforms an X or Y coordinate.

    Args:
        map_name (string): Map to search
        position (float): X or Y coordinate
        axis (string): Either "x" or "y" (lowercase)

    Returns:
        float
    """
    start = MAP_DATA[map_name][axis]
    scale = MAP_DATA[map_name]["scale"]
    if axis == "x":
        pos = position - start
        pos /= scale
        return pos
    elif axis == "y":
        pos = start - position
        pos /= scale
        return pos
    else:
        return None


def plot_positions(
    positions=[],
    colors=[],
    markers=[],
    alphas=[],
    sizes=[],
    map_name="de_ancient",
    map_type="original",
    dark=False,
    apply_transformation=False,
):
    """Plots player positions

    Args:
        positions (list): List of lists of length 2 ([[x,y], ...])
        colors (list): List of colors for each player
        markers (list): List of marker types for each player
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type
        apply_transformation (boolean): Indicates if you need to also use position_transform() for the X/Y coordinates

    Returns:
        matplotlib fig and ax
    """
    logging.info(alphas)
    logging.info(positions)
    logging.info(markers)
    logging.info(sizes)
    f, a = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for p, c, m, al, s in zip(positions, colors, markers, alphas, sizes):
        if apply_transformation:
            a.scatter(
                x=position_transform(map_name, p[0], "x"),
                y=position_transform(map_name, p[1], "y"),
                c=c,
                marker=m,
                alpha=al,
                s=s,
            )
        else:
            a.scatter(x=p[0], y=p[1], c=c, marker=m, alpha=al, s=s)
    a.get_xaxis().set_visible(False)
    a.get_yaxis().set_visible(False)
    return f, a


def plot_round(
    filename, frames, map_name="de_ancient", map_type="original", dark=False
):
    """Plots a round and saves as a .gif. CTs are blue, Ts are orange, and the bomb is an octagon. Only use untransformed coordinates.

    Args:
        filename (string): Filename to save the gif
        frames (list): List of frames from a parsed demo
        markers (list): List of marker types for each player
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type

    Returns:
        matplotlib fig and ax, saves .gif
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
            for p in f[side]["players"]:
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
        f, a = plot_positions(
            positions=positions,
            colors=colors,
            markers=markers,
            map_name=map_name,
            map_type=map_type,
            dark=dark,
        )
        image_files.append("csgo_tmp/{}.png".format(i))
        f.savefig(image_files[-1], dpi=300, bbox_inches="tight")
        plt.close()
    images = []
    for file in image_files:
        images.append(imageio.imread(file))
    imageio.mimsave(filename, images)
    shutil.rmtree("csgo_tmp/")
    return True


def get_player_id(player):
    """Extracts a players steamID from their player dictionary in a given frame.

    Each player has a unique steamID by which they can be identified.
    Bots, however, do not naturally have a steamID and are instead all assigned 0.
    To avoid overlap bots are instead identified by their name which is unique in any given game.

    Args:
        player: Dictionary about a players position and status in a given frame

    Returns:
        An integer corresponding to their steamID if they are a player or a string corresponding to the bots name if not.
    """
    if player["steamID"] == 0:
        return player["name"]
    else:
        return player["steamID"]


def plot_rounds(
    filename, frames_list, map_name="de_ancient", map_type="original", dark=False
):
    """Plots a round and saves as a .gif. CTs are blue, Ts are orange, and the bomb is an octagon. Only use untransformed coordinates.

    Args:
        filename (string): Filename to save the gif
        frames_list (list): List of frames lists from parsed demos
        markers (list): List of marker types for each player
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type

    Returns:
        matplotlib fig and ax, saves .gif
    """
    if os.path.isdir("csgo_tmp"):
        shutil.rmtree("csgo_tmp/")
    os.mkdir("csgo_tmp")
    image_files = []
    dict_initialized = {"t": False, "ct": False}
    id_number_dict = {"t": {}, "ct": {}}
    frame_positions = collections.defaultdict(list)
    frame_colors = collections.defaultdict(list)
    frame_markers = collections.defaultdict(list)
    frame_alphas = collections.defaultdict(list)
    frame_sizes = collections.defaultdict(list)
    colors_list = ["cyan", "red", "green", "blue", "orange"]
    # logging.info(type(frames_list))
    # logging.info([frames[0]["tick"] for frames in frames_list])
    max_frames = max(len(frames) for frames in frames_list)
    # logging.info(max_frames)
    for i in tqdm(range(max_frames)):
        # for i in range(max_frames):
        positions = []
        colors = []
        markers = []
        alphas = []
        sizes = []
        first_alive = [-1] * 5
        for frame_index, frames in enumerate(frames_list):
            # logging.info(type(frames))
            # logging.info(frame_index, frames[0])
            frame_positions[frame_index] = []
            frame_colors[frame_index] = []
            frame_markers[frame_index] = []
            frame_alphas[frame_index] = []
            frame_sizes[frame_index] = []
            if i in range(len(frames)):
                # Plot players
                for side in ["ct"]:
                    for player_index, p in enumerate(frames[i][side]["players"]):
                        player_id = get_player_id(p)
                        if dict_initialized[side] is False:
                            id_number_dict[side][player_id] = player_index
                        if player_id not in id_number_dict[side]:
                            continue
                        frame_colors[frame_index].append(
                            colors_list[id_number_dict[side][player_id]]
                        )
                        if p["hp"] == 0:
                            frame_markers[frame_index].append("x")
                        else:
                            frame_markers[frame_index].append(
                                r"$ {} $".format(frame_index)
                            )
                            if first_alive[id_number_dict[side][player_id]] == -1:
                                first_alive[
                                    id_number_dict[side][player_id]
                                ] = frame_index
                            # frame_markers[frame_index].append(".")
                        pos = (
                            position_transform(map_name, p["x"], "x"),
                            position_transform(map_name, p["y"], "y"),
                        )
                        frame_positions[frame_index].append(pos)
                        frame_alphas[frame_index].append(
                            1
                            if frame_index
                            == first_alive[id_number_dict[side][player_id]]
                            else 0.2
                        )
                        frame_sizes[frame_index].append(
                            mpl.rcParams["lines.markersize"] ** 2
                            if frame_index
                            == first_alive[id_number_dict[side][player_id]]
                            else 0.25 * mpl.rcParams["lines.markersize"] ** 2
                        )
                    dict_initialized[side] = True
            positions.extend(frame_positions[frame_index])
            colors.extend(frame_colors[frame_index])
            markers.extend(frame_markers[frame_index])
            alphas.extend(frame_alphas[frame_index])
            sizes.extend(frame_sizes[frame_index])
        # logging.info(alpha)
        # logging.info(positions)
        # logging.info(markers)
        f, a = plot_positions(
            positions=positions,
            colors=colors,
            markers=markers,
            alphas=alphas,
            sizes=sizes,
            map_name=map_name,
            map_type=map_type,
            dark=dark,
        )
        image_files.append("csgo_tmp/{}.png".format(i))
        f.savefig(image_files[-1], dpi=300, bbox_inches="tight")
        plt.close()
    images = []
    for file in image_files:
        images.append(imageio.imread(file))
    imageio.mimsave(filename, images)
    # shutil.rmtree("csgo_tmp/")
    return True


def plot_nades(
    rounds, nades=[], side="CT", map_name="de_ancient", map_type="original", dark=False
):
    """Plots grenade trajectories.

    Args:
        rounds (list): List of round objects from a parsed demo
        nades (list): List of grenade types to plot
        side (string): Specify side to plot grenades. Either "CT" or "T".
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type

    Returns:
        matplotlib fig and ax
    """
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
