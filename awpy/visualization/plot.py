import os
import shutil
import itertools
import collections

import imageio
from tqdm import tqdm
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
        try:
            col = "light"
            if dark:
                col = "dark"
            map_bg = imageio.imread(
                os.path.join(os.path.dirname(__file__), "")
                + """../data/map/{0}_{1}.png""".format(map_name, col)
            )
        except FileNotFoundError:
            map_bg = imageio.imread(
                os.path.join(os.path.dirname(__file__), "")
                + """../data/map/{0}.png""".format(map_name)
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
    alphas=None,
    sizes=None,
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
        alphas (list): List of alpha values for each player
        sizes (list): List of marker sizes for each player
        map_name (string): Map to search
        map_type (string): "original" or "simpleradar"
        dark (boolean): Only for use with map_type="simpleradar". Indicates if you want to use the SimpleRadar dark map type
        apply_transformation (boolean): Indicates if you need to also use position_transform() for the X/Y coordinates

    Returns:
        matplotlib fig and ax
    """
    if alphas is None:
        alphas = [1] * len(positions)
    if sizes is None:
        sizes = [mpl.rcParams["lines.markersize"] ** 2] * len(positions)
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


def get_player_id(player):
    """Extracts a players steamID from their player dictionary in a given frame.

    Each player has a unique steamID by which they can be identified.
    Bots, however, do not naturally have a steamID and are instead all assigned 0.
    To avoid overlap bots are instead identified by their name which is unique in any given game.

    Args:
        player (dictionary): Dictionary about a players position and status in a given frame

    Returns:
        string
    """
    if player["steamID"] == 0:
        return player["name"]
    else:
        return str(player["steamID"])


def get_shortest_distances_mapping(leaders, current_positions):
    """Gets the mapping between players in the current round and lead players that has the shortest total distance between mapped players.

    Args:
        leaders (dictionary): Dictionary of leaders position, alive status and color index in the current frame
        current_positions (list): List of tuples of players x, y coordinates in the current round and frame

    Returns:
        A list mapping the the player at index i in the current round to the leader at position list[i] in the leaders dictionary.
        (Requires python 3.6 because it relies on the order of elements in the dict)"""
    smallest_distance = float("inf")
    best_mapping = [0, 1, 2, 3, 4]
    for mapping in itertools.permutations(range(len(leaders)), len(current_positions)):
        dist = 0
        for current_pos, leader_pos in enumerate(mapping):
            # Remove dead players from consideration
            if current_positions[current_pos] is None:
                continue
            dist += (
                current_positions[current_pos][0]
                - leaders[list(leaders)[leader_pos]]["pos"][0]
            ) ** 2 + (
                current_positions[current_pos][1]
                - leaders[list(leaders)[leader_pos]]["pos"][1]
            ) ** 2
        if dist < smallest_distance:
            smallest_distance = dist
            best_mapping = mapping
    best_mapping = list(best_mapping)
    for i, leader_pos in enumerate(best_mapping):
        best_mapping[i] = list(leaders)[leader_pos]
    return best_mapping


def tree():
    """Builds tree data structure from nested defaultdicts

    Args:
        None

    Returns:
        An empty tree"""

    def the_tree():
        return collections.defaultdict(the_tree)

    return the_tree()


def plot_rounds_different_players(
    filename,
    frames_list,
    map_name="de_ancient",
    map_type="original",
    dark=False,
    sides=None,
):
    """Plots a list of rounds and saves as a .gif. Each player in the first round is assigned a separate color. Players in the other rounds are matched by proximity.
     Only use untransformed coordinates.

    Args:
        filename (string): Filename to save the gif
        frames_list (list): List of frames lists from parsed demos
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
    # Needed to check if leaders have been fully initialized
    dict_initialized = {"t": False, "ct": False}
    # Used to store values for each round separately. Needed when a round ends.
    frame_positions = collections.defaultdict(list)
    frame_colors = collections.defaultdict(list)
    frame_markers = collections.defaultdict(list)
    frame_alphas = collections.defaultdict(list)
    frame_sizes = collections.defaultdict(list)
    colors_list = {
        "t": ["cyan", "yellow", "fuchsia", "lime", "orange"],
        "ct": ["red", "green", "black", "white", "gold"],
    }
    # Dict to store the colors (via index) of players that have died so that they dont switch color posthumously
    dead_colors = {}
    # Determine how many frames are there in total
    max_frames = max(len(frames) for frames in frames_list)
    # Build tree data structure for leaders
    # Currently leaders={"t":{},"ct":{}} would probably do as well
    # For each side the keys are a players steamd id + "_" + frame_number in case the same steamid occurs in multiple rounds
    leaders = tree()
    # Want to avoid unsafe defaults
    if sides is None:
        sides = ["ct"]
    for i in tqdm(range(max_frames)):
        # Initialize lists used to store things from all rounds to plot for each frame
        positions = []
        colors = []
        markers = []
        alphas = []
        sizes = []
        # Is used to determine if a specific leader has already been seen. Needed when a leader drops out because their round has already ended
        checked_in = set()
        # Loop over all the rounds and update the position and status of all leaders
        for frame_index, frames in enumerate(frames_list):
            # Check if the current frame has already ended
            if i in range(len(frames)):
                for side in sides:
                    # Do not do this if leaders has not been fully initialized
                    if dict_initialized[side] is True:
                        for player_index, p in enumerate(frames[i][side]["players"]):
                            player_id = get_player_id(p) + "_" + str(frame_index)
                            if (
                                player_id not in leaders[side]
                                or player_id in checked_in
                            ):
                                continue
                            pos = (
                                position_transform(map_name, p["x"], "x"),
                                position_transform(map_name, p["y"], "y"),
                            )
                            if p["hp"] == 0:
                                leaders[side][player_id]["is_dead"] = True
                            leaders[side][player_id]["pos"] = pos
        # Now do another loop to add all players in all frames with their appropriate colors.
        for frame_index, frames in enumerate(frames_list):
            # Initialize lists used to store values for this round for this frame
            frame_positions[frame_index] = []
            frame_colors[frame_index] = []
            frame_markers[frame_index] = []
            frame_alphas[frame_index] = []
            frame_sizes[frame_index] = []
            if i in range(len(frames)):
                for side in sides:
                    # If we have already initialized leaders
                    if dict_initialized[side] is True:
                        # Get the positions of all players in the current frame and round
                        current_positions = []
                        for player_index, p in enumerate(frames[i][side]["players"]):
                            pos = (
                                position_transform(map_name, p["x"], "x"),
                                position_transform(map_name, p["y"], "y"),
                            )
                            # Remove dead players from consideration
                            if p["hp"] == 0:
                                current_positions.append(None)
                            else:
                                current_positions.append(pos)
                        # Find the best mapping between current players and leaders
                        mapping = get_shortest_distances_mapping(
                            leaders[side], current_positions
                        )
                    # Now do the actual plotting
                    for player_index, p in enumerate(frames[i][side]["players"]):
                        player_id = get_player_id(p) + "_" + str(frame_index)
                        pos = (
                            position_transform(map_name, p["x"], "x"),
                            position_transform(map_name, p["y"], "y"),
                        )

                        is_dead = False
                        if p["hp"] == 0:
                            is_dead = True
                            frame_markers[frame_index].append("x")
                        else:
                            frame_markers[frame_index].append(".")

                        # If the leaders have not been initialized yet, do so
                        if dict_initialized[side] is False:
                            leaders[side][player_id]["index"] = player_index
                            leaders[side][player_id]["pos"] = pos
                            leaders[side][player_id]["is_dead"] = is_dead

                        # This is relevant for all subsequent frames
                        # If we are a leader we update our values
                        # Should be able to be dropped as we already updated leaders in the earlier loop
                        if player_id in leaders[side]:
                            # Update the is_dead status
                            if is_dead:
                                leaders[side][player_id]["is_dead"] = True
                            # Grabour current player_index from what it was the previous round to achieve color consistency
                            player_index = leaders[side][player_id]["index"]
                            # Update our position
                            leaders[side][player_id]["pos"] = pos
                        # If not a leader
                        else:
                            # Grab the id of the leader assigned to this player
                            assigned_leader = mapping[player_index]
                            # If the assigned leader is now dead or has not been assigned (happens when his round is already over)
                            # Then we take over that position if we are not also dead
                            if (
                                leaders[side][assigned_leader]["is_dead"]
                                or assigned_leader not in checked_in
                            ) and not is_dead:
                                # Remove the previous leaders entry from the dict
                                old_index = leaders[side][assigned_leader]["index"]
                                del leaders[side][assigned_leader]
                                # Fill with our own values but use their prior index to keep color consistency when switching leaders
                                leaders[side][player_id]["index"] = old_index
                                leaders[side][player_id]["pos"] = pos
                                leaders[side][player_id]["is_dead"] = False
                                player_index = leaders[side][player_id]["index"]
                            # If the leader is alive and present or if we are also dead
                            else:
                                # We just grab our color
                                player_index = leaders[side][assigned_leader]["index"]
                        # If we just died this frame store our current color in a dict for later reuse
                        if is_dead and player_id not in dead_colors:
                            dead_colors[player_id] = colors_list[side][player_index]
                        # If we are dead use our stored color instead of the one we were assigned
                        if is_dead:
                            frame_colors[frame_index].append(dead_colors[player_id])
                        # Otherwise use the assigned color
                        else:
                            frame_colors[frame_index].append(
                                colors_list[side][player_index]
                            )
                        frame_positions[frame_index].append(pos)
                        # If we are an alive leader we get opaque and big markers
                        if (
                            player_id in leaders[side]
                            and not leaders[side][player_id]["is_dead"]
                            and not player_id in checked_in
                        ):
                            frame_alphas[frame_index].append(1)
                            frame_sizes[frame_index].append(
                                mpl.rcParams["lines.markersize"] ** 2
                            )
                        # If not we get partially transparent and small ones
                        else:
                            frame_alphas[frame_index].append(0.5)
                            frame_sizes[frame_index].append(
                                0.3 * mpl.rcParams["lines.markersize"] ** 2
                            )
                        # If we are a leader we are now checked in so everyone knows our round has not ended yet
                        if player_id in leaders[side]:
                            checked_in.add(player_id)
                    # Once we have done our first loop over a side we are initialized
                    dict_initialized[side] = True
            # Ádd the values for the current round to the lists for the whole frame
            positions.extend(frame_positions[frame_index])
            colors.extend(frame_colors[frame_index])
            markers.extend(frame_markers[frame_index])
            alphas.extend(frame_alphas[frame_index])
            sizes.extend(frame_sizes[frame_index])
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


def plot_rounds_same_players(
    filename,
    frames_list,
    map_name="de_ancient",
    map_type="original",
    dark=False,
    sides=None,
):
    """Plots a list of rounds and saves as a .gif. Each player in the first round is assigned a separate color. Players in the other rounds are matched by steam id.
     Only use untransformed coordinates.

    Args:
        filename (string): Filename to save the gif
        frames_list (list): List of frames lists from parsed demos
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
    # Needed to check if leaders have been fully initialized
    dict_initialized = {"t": False, "ct": False}
    # Dictionary used to map each players steam id to a given index (color)
    id_number_dict = {"t": {}, "ct": {}}
    # Used to store values for each round separately. Needed when a round ends.
    frame_positions = collections.defaultdict(list)
    frame_colors = collections.defaultdict(list)
    frame_markers = collections.defaultdict(list)
    frame_alphas = collections.defaultdict(list)
    frame_sizes = collections.defaultdict(list)
    colors_list = {
        "t": ["cyan", "yellow", "fuchsia", "lime", "orange"],
        "ct": ["red", "green", "black", "white", "gold"],
    }
    # Determine how many frames are there in total
    max_frames = max(len(frames) for frames in frames_list)
    # Want to avoid unsafe defaults
    if sides is None:
        sides = ["ct"]
    for i in tqdm(range(max_frames)):
        # Initialize lists used to store things from all rounds to plot for each frame
        positions = []
        colors = []
        markers = []
        alphas = []
        sizes = []
        # The first instance of a given player being alive is taken note if so that they can be marked bigger
        first_alive = [-1] * 5
        for frame_index, frames in enumerate(frames_list):
            # Initialize lists used to store values for this round for this frame
            frame_positions[frame_index] = []
            frame_colors[frame_index] = []
            frame_markers[frame_index] = []
            frame_alphas[frame_index] = []
            frame_sizes[frame_index] = []
            if i in range(len(frames)):
                for side in sides:
                    for player_index, p in enumerate(frames[i][side]["players"]):
                        player_id = get_player_id(p)

                        # Assign steam ids to their index only the first time
                        if dict_initialized[side] is False:
                            id_number_dict[side][player_id] = player_index
                        player_index = id_number_dict[side][player_id]

                        # If a player hasnt been assigned they are not plotted this round (player joins or leaves mid round)
                        if player_id not in id_number_dict[side]:
                            continue
                        # Color gets assigned according to matched steam id index
                        frame_colors[frame_index].append(
                            colors_list[side][player_index]
                        )
                        if p["hp"] == 0:
                            frame_markers[frame_index].append("x")
                        else:
                            frame_markers[frame_index].append(
                                r"$ {} $".format(frame_index)
                            )
                            if first_alive[player_index] == -1:
                                first_alive[player_index] = frame_index
                        pos = (
                            position_transform(map_name, p["x"], "x"),
                            position_transform(map_name, p["y"], "y"),
                        )
                        frame_positions[frame_index].append(pos)
                        # First alive player gets plotted big and opaque
                        frame_alphas[frame_index].append(
                            1 if frame_index == first_alive[player_index] else 0.5
                        )
                        # All others small and partially transparent
                        frame_sizes[frame_index].append(
                            mpl.rcParams["lines.markersize"] ** 2
                            if frame_index == first_alive[player_index]
                            else 0.3 * mpl.rcParams["lines.markersize"] ** 2
                        )
                    dict_initialized[side] = True
            positions.extend(frame_positions[frame_index])
            colors.extend(frame_colors[frame_index])
            markers.extend(frame_markers[frame_index])
            alphas.extend(frame_alphas[frame_index])
            sizes.extend(frame_sizes[frame_index])
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
    shutil.rmtree("csgo_tmp/")
    return True
