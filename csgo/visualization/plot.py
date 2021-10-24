import os
import shutil
import imageio

from tqdm import tqdm

import matplotlib.pyplot as plt

from csgo import MAP_DATA


def plot_map(map_name="de_dust2", map_type="original", dark=False):
    """Plots the map"""
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
    start = MAP_DATA[map_name][axis]
    scale = MAP_DATA[map_name]["scale"]
    pos = position - start
    pos = pos / scale
    return pos


def plot_positions(
    positions=[],
    colors=[],
    markers=[],
    map_name="de_ancient",
    map_type="original",
    dark=False,
    apply_transformation=False,
):
    """Plots positions"""
    f, a = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for p, c, m in zip(positions, colors, markers):
        if apply_transformation:
            a.scatter(
                x=position_transform(map_name, p[0], "x"),
                y=position_transform(map_name, p[1], "y"),
                c=c,
                marker=m,
            )
        else:
            a.scatter(x=p[0], y=p[1], c=c, marker=m)
    a.get_xaxis().set_visible(False)
    a.get_yaxis().set_visible(False)
    return f, a


def plot_round(
    filename, frames, map_name="de_ancient", map_type="original", dark=False
):
    """Creates gif from frame. Writes to filename"""
    if os.path.isdir("csgo_tmp"):
        shutil.rmtree("csgo_tmp/")
    os.mkdir("csgo_tmp")
    image_files = []
    for i, f in tqdm(enumerate(frames)):
        positions = []
        colors = []
        markers = []
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
    """Plot grenades"""
    f, a = plot_map(map_name=map_name, map_type=map_type, dark=dark)
    for r in rounds:
        if r["grenades"]:
            for g in r["grenades"]:
                if g["throwerSide"] == side:
                    start_x = position_transform(map_name, g["throwerX"], "x")
                    start_y = position_transform(map_name, g["throwerY"], "x")
                    end_x = position_transform(map_name, g["grenadeX"], "y")
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
