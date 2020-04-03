import os
import matplotlib.pyplot as plt

from scipy.misc import imread

map_adjustments = {"de_dust2": [-4, 26]}


def plot_trajectory(df, map):
    """ Plots trajectories given a map
    """
    map_bg = imread("""../data/map_img/{0}.png""".format(map))
    fig = plt.figure(figsize=(8, 6))
    plt.plot(
        df["XViz"] + map_adjustments[map][0],
        df["YViz"] + map_adjustments[map][1],
        color="orange",
        zorder=1,
        linestyle="solid",
    )
    plt.imshow(map_bg, zorder=0)
    plt.show()
    return fig


# def plot_kills(df, map):
#     """ Plots kills given a map
#     """
#     map_bg = imread("""../data/map_img/{0}.png""".format(map))
#     for index, row in df.iterrows():
#         if row["AttackerSide"] == "T":
#             linecol = "red"
#         elif row["AttackerSide"] == "CT":
#             linecol = "blue"
#         else:
#             linecol = "gray"
#         plt.plot(row["AttackerXViz"]+map_adjustments[map][0], row["AttackerYViz"]+map_adjustments[map][1], color = "red", zorder=1)
#         plt.plot(row["VictimXViz"]+map_adjustments[map][0], row["VictimYViz"]+map_adjustments[map][1], color = "blue", zorder=1)
#         connectpoints([row["AttackerXViz"], row["AttackerYViz"]], [row["VictimXViz"], row["VictimYViz"]], color = linecol)
#     plt.imshow(map_bg, zorder=0)
#     return plt.show()


def plot_kills(df, map):
    """ plot kills
    """
    map_bg = imread("""../data/map_img/{0}.png""".format(map))
    for index, row in df.iterrows():
        if row["AttackerSide"] == "T":
            linecol = "red"
        elif row["AttackerSide"] == "CT":
            linecol = "blue"
        else:
            linecol = "gray"
        plt.scatter(
            row["AttackerXViz"] + map_adjustments[map][0],
            row["AttackerYViz"] + map_adjustments[map][1],
            color="red",
            zorder=1,
        )
        plt.scatter(
            row["VictimXViz"] + map_adjustments[map][0],
            row["VictimYViz"] + map_adjustments[map][1],
            color="blue",
            zorder=1,
        )
    plt.imshow(map_bg, zorder=0)
    # return plt.show()
    raise NotImplementedError
