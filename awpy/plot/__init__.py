"""Awpy plotting module."""

PLOT_SETTINGS = {
    "ct": {
        "marker": "o",
        "color": "tab:cyan",
        "size": 8,
    },
    "t": {
        "marker": "o",
        "color": "tab:olive",
        "size": 8,
    },
    "bomb": {
        "marker": "x",
        "color": "tab:orange",
        "size": 8,
    },
    "smoke": {
        "marker": "o",
        "color": "tab:gray",
        "size": 12,
    },
    "fire": {
        "marker": "o",
        "color": "tab:red",
        "size": 12,
    },
}

from awpy.plot.plot import gif, heatmap, plot

__all__ = ["gif", "heatmap", "plot"]
