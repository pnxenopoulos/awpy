"""Parse Counter-Strike 2 demos with Rust and query typed Polars DataFrames.

Use Polars for filters, joins, and Apache Parquet output.
Use the optional ``awpy.plot`` module for matplotlib radar plots and GIFs.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("awpy")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"

from awpy import data, map_control
from awpy._awpy import Demo, InvalidDemoError, NavMesh, VisibilityChecker
from awpy.schema import GAME_EVENTS, SNAPSHOT_PROPERTIES

__all__ = [
    "GAME_EVENTS",
    "SNAPSHOT_PROPERTIES",
    "Demo",
    "InvalidDemoError",
    "NavMesh",
    "VisibilityChecker",
    "data",
    "map_control",
]
