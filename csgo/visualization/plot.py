from csgo import MAP_DATA

import matplotlib.pyplot as plt
import matplotlib.image as mpimg


def plot_map(map_name="de_dust2", type="original", dark=False):
    """Plots the map"""
    if type == "original":
        map_bg = mpimg.imread("""../data/map/{0}.png""".format(map_name))
    else:
        col = "light"
        if dark:
            col = "dark"
        map_bg = mpimg.imread("""../data/map/{0}_{1}.png""".format(map_name, col))
    fig, ax = plt.subplots()
    ax.imshow(map_bg, zorder=0)
    return fig, ax


# Position functions courtesy of PureSkill.gg
def position_transform_x(map_name, position_x):
    start_x = MAP_DATA[map_name]["x"]
    scale = MAP_DATA[map_name]["scale"]
    x_pos = position_x
    x_pos = x_pos - start_x
    x_pos = x_pos / scale
    return x_pos


# Position functions courtesy of PureSkill.gg
def position_transform_y(map_name, position_y):
    start_y = MAP_DATA[map_name]["y"]
    scale = MAP_DATA[map_name]["scale"]
    y_pos = position_y
    y_pos = start_y - y_pos
    y_pos = y_pos / scale
    return y_pos


def plot_positions(
    positions=[],
    colors=[],
    markers=[],
    map_name="de_ancient",
    type="original",
    dark=False,
    apply_transformation=False,
):
    """Plots positions"""
    f, a = plot_map(map_name=map_name, type=type, dark=dark)
    for p, c, m in zip(positions, colors, markers):
        if apply_transformation:
            a.scatter(x=position_transform_x(map_name=map_name, p[0]), y=position_transform_y(map_name=map_name, p[1]), c=c, marker=m)
        else:
            a.scatter(x=p[0], y=p[1], c=c, marker=m)
    a.get_xaxis().set_visible(False)
    a.get_yaxis().set_visible(False)
    return f, a
