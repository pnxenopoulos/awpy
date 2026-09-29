"""Build small binary files for spatial tests."""

import struct
from pathlib import Path

Point = tuple[float, float, float]
Square = list[Point]


def square(x: float, y: float, z: float = 0.0) -> Square:
    """Return the corners of a unit square at the given position."""
    return [(x, y, z), (x + 1, y, z), (x + 1, y + 1, z), (x, y + 1, z)]


def write_nav(path: Path, areas: list[tuple[int, Square, list[int]]]) -> None:
    """Write a version-35 nav file with all connections on the first edge.

    Each area has an ID, four corners, and a list of neighbor IDs.
    """
    buf = bytearray()
    buf += struct.pack("<I", 0xFEEDFACE)  # magic
    buf += struct.pack("<III", 35, 1, 1)  # version, sub_version, unk1 (analyzed)

    # Shared polygon table: four corners per area.
    buf += struct.pack("<I", len(areas) * 4)
    for _, corners, _ in areas:
        for cx, cy, cz in corners:
            buf += struct.pack("<fff", cx, cy, cz)
    buf += struct.pack("<I", len(areas))  # polygon_count
    for i in range(len(areas)):
        buf += struct.pack("<B", 4)  # corner count
        for k in range(4):
            buf += struct.pack("<I", i * 4 + k)
        buf += struct.pack("<I", 0)  # version>=35 per-polygon field

    buf += struct.pack("<I", 0)  # version>=32 field
    buf += struct.pack("<I", 0)  # version>=35 field

    buf += struct.pack("<I", len(areas))  # area_count
    for i, (area_id, _, conns) in enumerate(areas):
        buf += struct.pack("<I", area_id)
        buf += struct.pack("<q", 0)  # dynamic_attribute_flags
        buf += struct.pack("<B", 0)  # hull_index
        buf += struct.pack("<I", i)  # polygon_index
        buf += struct.pack("<I", 0)  # skip
        buf += struct.pack("<I", len(conns))  # connections on first edge
        for c in conns:
            buf += struct.pack("<II", c, 0)  # neighbor area id, edge id
        for _ in range(3):
            buf += struct.pack("<I", 0)  # no connections on the other edges
        buf += b"\x00" * 5  # legacy hiding/encounter counts
        buf += struct.pack("<I", 0)  # ladders_above count
        buf += struct.pack("<I", 0)  # ladders_below count
    path.write_bytes(buf)


def write_mesh(path: Path, verts: list[Point], tris: list[tuple[int, int, int]]) -> None:
    """Write a mesh file from vertices and triangle indices."""
    buf = bytearray(b"AWMH")
    buf += struct.pack("<III", 1, len(verts), len(tris))
    for v in verts:
        buf += struct.pack("<fff", *v)
    for t in tris:
        buf += struct.pack("<III", *t)
    path.write_bytes(buf)
