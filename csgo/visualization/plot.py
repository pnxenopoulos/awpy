import matplotlib.pyplot as plt

from scipy.misc import imread


def plot_map(map_name="de_dust2", type="original", dark=False):
    """Plots the map"""
    if type == "original":
        map_bg = imread("""../data/map/{0}.png""".format(map_name))
    else:
        col = "light"
        if dark:
            col = "dark"
        map_bg = imread("""../data/map/{0}_col.png""".format(map_name, col))
    fig, ax = plt.subplots()
    ax.imshow(map_bg, zorder=0)
    return fig, ax
