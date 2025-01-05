"""Module to parse and represent navigation mesh files."""

import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Optional


class DynamicAttributeFlags(int):
    """A custom integer class for dynamic attribute flags."""

    def __new__(cls, value: Any) -> "DynamicAttributeFlags":  # noqa: ANN401
        """Creates a new DynamicAttributeFlags instance.

        Args:
            value: The integer value for the flags.

        Returns:
            A new DynamicAttributeFlags instance.
        """
        return super().__new__(cls, value)


class NavDirectionType(Enum):
    """Enumeration for navigation directions."""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


@dataclass
class Vector3:
    """A 3D vector representation.

    Attributes:
        x: X coordinate.
        y: Y coordinate.
        z: Z coordinate.
    """

    x: float
    y: float
    z: float


class NavMeshConnection:
    """Represents a connection between navigation mesh areas.

    Attributes:
        area_id: ID of the connected area.
        edge_id: ID of the connecting edge.
    """

    def __init__(self) -> None:
        """Constructs an empty NavMeshConnection."""
        self.area_id: int = 0
        self.edge_id: int = 0

    def read(self, br: BinaryIO) -> None:
        """Reads connection data from a binary stream.

        Args:
            br: Binary reader stream to read from.
        """
        self.area_id = struct.unpack("I", br.read(4))[0]
        self.edge_id = struct.unpack("I", br.read(4))[0]


class NavArea:
    """Represents an area in the navigation mesh.

    Attributes:
        area_id: Unique identifier for the area.
        hull_index: Index of the hull.
        dynamic_attribute_flags: Dynamic attributes of the area.
        corners: List of corner positions.
        connections: List of connections for each corner.
        ladders_above: List of ladder IDs above this area.
        ladders_below: List of ladder IDs below this area.
    """

    def __init__(self) -> None:
        """Constructs an empty NavArea."""
        self.area_id: int = 0
        self.hull_index: int = 0
        self.dynamic_attribute_flags: DynamicAttributeFlags = DynamicAttributeFlags(0)
        self.corners: list[Vector3] = []
        self.connections: list[list[NavMeshConnection]] = []
        self.ladders_above: list[int] = []
        self.ladders_below: list[int] = []

    @staticmethod
    def read_connections(br: BinaryIO) -> list[NavMeshConnection]:
        """Reads a list of connections from a binary stream.

        Args:
            br: Binary reader stream to read from.

        Returns:
            List of NavMeshConnection objects.
        """
        connection_count = struct.unpack("I", br.read(4))[0]
        connections = []
        for _ in range(connection_count):
            connection = NavMeshConnection()
            connection.read(br)
            connections.append(connection)
        return connections

    def read(
        self,
        br: BinaryIO,
        nav_mesh_file: "Nav",
        polygons: Optional[list[list[Vector3]]] = None,
    ) -> None:
        """Reads area data from a binary stream.

        Args:
            br: Binary reader stream to read from.
            nav_mesh_file: Parent Nav object containing this area.
            polygons: Optional list of predefined polygons for version 31+.
        """
        self.area_id = struct.unpack("I", br.read(4))[0]
        self.dynamic_attribute_flags = DynamicAttributeFlags(
            struct.unpack("q", br.read(8))[0]
        )
        self.hull_index = br.read(1)[0]

        if nav_mesh_file.version >= 31 and polygons is not None:
            polygon_index = struct.unpack("I", br.read(4))[0]
            self.corners = polygons[polygon_index]
        else:
            corner_count = struct.unpack("I", br.read(4))[0]
            self.corners = []
            for _ in range(corner_count):
                x, y, z = struct.unpack("fff", br.read(12))
                self.corners.append(Vector3(x, y, z))

        br.read(4)  # Skip almost always 0

        self.connections = []
        for _ in range(len(self.corners)):
            self.connections.append(self.read_connections(br))

        br.read(5)  # Skip LegacyHidingSpotData count and LegacySpotEncounterData count

        ladder_above_count = struct.unpack("I", br.read(4))[0]
        self.ladders_above = []
        for _ in range(ladder_above_count):
            ladder_id = struct.unpack("I", br.read(4))[0]
            self.ladders_above.append(ladder_id)

        ladder_below_count = struct.unpack("I", br.read(4))[0]
        self.ladders_below = []
        for _ in range(ladder_below_count):
            ladder_id = struct.unpack("I", br.read(4))[0]
            self.ladders_below.append(ladder_id)

    def __repr__(self) -> str:
        """Returns string representation of NavArea."""
        connected_ids = sorted({c.area_id for conns in self.connections for c in conns})
        points = [(c.x, c.y, c.z) for c in self.corners]
        return f"NavArea(id={self.area_id}, connected_ids={connected_ids}, points={points})"  # noqa: E501


class Nav:
    """Navigation mesh file parser.

    Attributes:
        MAGIC: Magic number for nav mesh file format.
        version: Version of the nav mesh file.
        sub_version: Sub-version of the nav mesh file.
        areas: Dictionary of navigation areas indexed by area ID.
        is_analyzed: Whether the nav mesh has been analyzed.
    """

    MAGIC: int = 0xFEEDFACE

    def __init__(self, path: str | Path) -> None:
        """Initializes and reads a navigation mesh from a file.

        Args:
            path: Path to the nav mesh file to read.


        Raises:
            FileNotFoundError: If the nav mesh file does not exist.
        """
        self.version: int = 0
        self.sub_version: int = 0
        self.areas: dict[int, NavArea] = {}
        self.is_analyzed: bool = False
        self.read(path)

    def read(self, path: str | Path) -> None:
        """Reads nav mesh data from a file.

        Args:
            path: Path to the nav mesh file to read.

        Raises:
            FileNotFoundError: If the nav mesh file does not exist.
            ValueError: If the file format is invalid or unsupported.
        """
        nav_path = Path(path)
        if not nav_path.exists():
            nav_path_not_found_msg = f"Nav mesh file not found: {nav_path}"
            raise FileNotFoundError(nav_path_not_found_msg)

        with open(nav_path, "rb") as f:
            magic = struct.unpack("I", f.read(4))[0]
            if magic != self.MAGIC:
                unexpected_magic_msg = (
                    f"Unexpected magic: {magic:X}, expected {self.MAGIC:X}"
                )
                raise ValueError(unexpected_magic_msg)

            self.version = struct.unpack("I", f.read(4))[0]
            if self.version < 30 or self.version > 35:
                unsupported_version_msg = f"Unsupported nav version: {self.version}"
                raise ValueError(unsupported_version_msg)

            self.sub_version = struct.unpack("I", f.read(4))[0]

            unk1 = struct.unpack("I", f.read(4))[0]
            self.is_analyzed = (unk1 & 0x00000001) > 0

            polygons = None
            if self.version >= 31:
                polygons = self._read_polygons(f)

            if self.version >= 32:
                f.read(4)  # Skip unk2

            if self.version >= 35:
                f.read(4)  # Skip unk3

            self._read_areas(f, polygons)

    def _read_polygons(self, br: BinaryIO) -> list[list[Vector3]]:
        """Reads polygon data from a binary stream.

        Args:
            br: Binary reader stream to read from.

        Returns:
            List of polygons, where each polygon is a list of Vector3 vertices.
        """
        corner_count = struct.unpack("I", br.read(4))[0]
        corners = []
        for _ in range(corner_count):
            x, y, z = struct.unpack("fff", br.read(12))
            corners.append(Vector3(x, y, z))

        polygon_count = struct.unpack("I", br.read(4))[0]
        polygons = []
        for _ in range(polygon_count):
            polygons.append(self._read_polygon(br, corners))
        return polygons

    def _read_polygon(self, br: BinaryIO, corners: list[Vector3]) -> list[Vector3]:
        """Reads a single polygon from a binary stream.

        Args:
            br: Binary reader stream to read from.
            corners: List of corner vertices to reference.

        Returns:
            List of Vector3 vertices forming the polygon.
        """
        corner_count = br.read(1)[0]
        polygon = []
        for _ in range(corner_count):
            corner_index = struct.unpack("I", br.read(4))[0]
            polygon.append(corners[corner_index])
        if self.version >= 35:
            br.read(4)  # Skip unk
        return polygon

    def _read_areas(
        self, br: BinaryIO, polygons: Optional[list[list[Vector3]]]
    ) -> None:
        """Reads all navigation areas from a binary stream.

        Args:
            br: Binary reader stream to read from.
            polygons: Optional list of predefined polygons for version 31+.
        """
        area_count = struct.unpack("I", br.read(4))[0]
        for _ in range(area_count):
            area = NavArea()
            area.read(br, self, polygons)
            self.areas[area.area_id] = area

    def __repr__(self) -> str:
        """Returns string representation of Nav."""
        return (
            f"Nav(version={self.version}.{self.sub_version}, areas={len(self.areas)})"
        )
