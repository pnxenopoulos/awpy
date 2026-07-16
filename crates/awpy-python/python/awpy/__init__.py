"""Awpy — a Counter-Strike 2 demo parser with a Rust backend."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("awpy")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"

from awpy import data
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
]
