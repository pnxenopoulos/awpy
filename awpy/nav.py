"""Module to parse and represent navigation mesh files.

Reference: https://github.com/ValveResourceFormat/ValveResourceFormat/tree/master/ValveResourceFormat/NavMesh
"""

import json
import math
import struct
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Literal, Self, TypedDict

import networkx as nx

from awpy.vector import Vector3, Vector3Dict


def _read_u32(f: BinaryIO) -> int:
    return struct.unpack("I", f.read(4))[0]


def _read_u16(f: BinaryIO) -> int:
    return struct.unpack("H", f.read(2))[0]


def _read_i32(f: BinaryIO) -> int:
    return struct.unpack("i", f.read(4))[0]


class DynamicAttributeFlags(int):
    """A custom integer class for dynamic attribute flags."""

    def __new__(cls, value: int) -> Self:
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


class NavMeshConnection:
    """Represents a connection between navigation mesh areas.

    Attributes:
        area_id: ID of the connected area.
        edge_id: ID of the connecting edge.
    """

    def __init__(self, area_id: int = 0, edge_id: int = 0) -> None:
        """Constructs an empty NavMeshConnection."""
        self.area_id = area_id
        self.edge_id = edge_id

    @classmethod
    def from_binary(cls, br: BinaryIO) -> Self:
        """Creates a NavMeshConnection from a binary stream.

        Args:
            br: Binary reader stream to read from.

        Returns:
            A new NavMeshConnection object.
        """
        area_id = _read_u32(br)
        edge_id = _read_u32(br)
        return cls(area_id, edge_id)


class NavAreaDict(TypedDict):
    """Typed dict representation of a NavArea."""

    area_id: int
    hull_index: int
    dynamic_attribute_flags: int
    corners: list[Vector3Dict]
    connections: list[int]
    ladders_above: list[int]
    ladders_below: list[int]


class CompressionMethod(Enum):
    """Compression method for KV3 binary data."""

    RAW = 0
    LZ4 = 1
    ZSTD = 2


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

    def __init__(
        self,
        area_id: int = 0,
        hull_index: int = 0,
        dynamic_attribute_flags: DynamicAttributeFlags = DynamicAttributeFlags(  # noqa: B008
            0
        ),
        corners: list[Vector3] | None = None,
        connections: list[int] | None = None,
        ladders_above: list[int] | None = None,
        ladders_below: list[int] | None = None,
    ) -> None:
        """Constructs an empty NavArea."""
        self.area_id = area_id
        self.hull_index = hull_index
        self.dynamic_attribute_flags = dynamic_attribute_flags
        self.corners: list[Vector3] = corners or []
        self.connections: list[int] = connections or []
        self.ladders_above: list[int] = ladders_above or []
        self.ladders_below: list[int] = ladders_below or []

    @property
    def connected_areas(self) -> set[int]:
        """Returns a set of connected area IDs."""
        return set(self.connections)

    @property
    def size(self) -> float:
        """Calculates the area of the polygon defined by the corners.

        Returns:
            The area of the polygon in 2D (ignoring the z-coordinate).
        """
        if len(self.corners) < 3:
            return 0.0  # A polygon must have at least 3 corners to form an area

        x_coords = [corner.x for corner in self.corners]
        y_coords = [corner.y for corner in self.corners]

        # Close the polygon loop
        x_coords.append(x_coords[0])
        y_coords.append(y_coords[0])

        # Shoelace formula
        area = 0.0
        for i in range(len(self.corners)):
            area += x_coords[i] * y_coords[i + 1] - y_coords[i] * x_coords[i + 1]

        return abs(area) / 2.0

    @property
    def centroid(self) -> Vector3:
        """Calculates the centroid of the polygon defined by the corners.

        Returns:
            A Vector3 representing the centroid (geometric center) of the polygon.
        """
        if not self.corners:
            return Vector3(0, 0, 0)  # Return origin if no corners exist

        x_coords = [corner.x for corner in self.corners]
        y_coords = [corner.y for corner in self.corners]

        centroid_x = sum(x_coords) / len(self.corners)
        centroid_y = sum(y_coords) / len(self.corners)

        # Assume z is averaged as well for completeness
        z_coords = [corner.z for corner in self.corners]
        centroid_z = sum(z_coords) / len(self.corners)

        return Vector3(centroid_x, centroid_y, centroid_z)

    def __repr__(self) -> str:
        """Returns string representation of NavArea."""
        connected_ids = sorted(set(self.connections))
        points = [c.to_tuple() for c in self.corners]
        return f"NavArea(id={self.area_id}, connected_ids={connected_ids}, points={points}, size={self.size})"

    @staticmethod
    def read_connections(br: BinaryIO) -> list[NavMeshConnection]:
        """Reads a list of connections from a binary stream.

        Args:
            br: Binary reader stream to read from.

        Returns:
            List of NavMeshConnection objects.
        """
        connection_count = _read_u32(br)
        return [NavMeshConnection.from_binary(br) for _ in range(connection_count)]

    @classmethod
    def from_data(
        cls,
        br: BinaryIO,
        nav_mesh_version: int,
        polygons: list[list[Vector3]] | None = None,
    ) -> Self:
        """Reads area data from a binary stream.

        Args:
            br: Binary reader stream to read from.
            nav_mesh_version: Version of the nav mesh file.
            polygons: Optional list of predefined polygons for version 31+.
        """
        area_id = _read_u32(br)
        dynamic_attribute_flags = DynamicAttributeFlags(struct.unpack("q", br.read(8))[0])
        hull_index = br.read(1)[0]

        corners: list[Vector3] = []
        if nav_mesh_version >= 31 and polygons is not None:
            polygon_index: int = _read_u32(br)
            corners = polygons[polygon_index]
        else:
            corner_count = _read_u32(br)
            for _ in range(corner_count):
                x, y, z = struct.unpack("fff", br.read(12))
                corners.append(Vector3(x, y, z))

        br.read(4)  # Skip almost always 0

        connections = [conn.area_id for _ in range(len(corners)) for conn in cls.read_connections(br)]

        br.read(5)  # Skip LegacyHidingSpotData count and LegacySpotEncounterData count

        ladder_above_count = _read_u32(br)
        ladders_above: list[int] = []
        for _ in range(ladder_above_count):
            ladder_id = _read_u32(br)
            ladders_above.append(ladder_id)

        ladder_below_count = _read_u32(br)
        ladders_below: list[int] = []
        for _ in range(ladder_below_count):
            ladder_id = _read_u32(br)
            ladders_below.append(ladder_id)
        return cls(
            area_id=area_id,
            hull_index=hull_index,
            dynamic_attribute_flags=dynamic_attribute_flags,
            corners=corners,
            connections=connections,
            ladders_above=ladders_above,
            ladders_below=ladders_below,
        )

    def to_dict(self) -> NavAreaDict:
        """Converts the navigation area to a dictionary."""
        return {
            "area_id": self.area_id,
            "hull_index": self.hull_index,
            "dynamic_attribute_flags": int(self.dynamic_attribute_flags),
            "corners": [c.to_dict() for c in self.corners],
            "connections": self.connections,
            "ladders_above": self.ladders_above,
            "ladders_below": self.ladders_below,
        }

    @classmethod
    def from_dict(cls, data: NavAreaDict) -> Self:
        """Load a NavArea from a dictionary."""
        return cls(
            area_id=data["area_id"],
            hull_index=data["hull_index"],
            dynamic_attribute_flags=DynamicAttributeFlags(data["dynamic_attribute_flags"]),
            corners=[Vector3.from_dict(c) for c in data["corners"]],
            connections=data["connections"],
            ladders_above=data["ladders_above"],
            ladders_below=data["ladders_below"],
        )


class NavDict(TypedDict):
    """Typed dict representation of a Nav."""

    version: int
    sub_version: int
    is_analyzed: bool
    areas: dict[int, NavAreaDict]


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

    def __init__(
        self,
        *,
        version: int = 0,
        sub_version: int = 0,
        areas: dict[int, NavArea] | None = None,
        is_analyzed: bool = False,
    ) -> None:
        """Initialize a Nav object from existing areas."""
        self.version = version
        self.sub_version = sub_version
        self.areas = areas or {}
        self.is_analyzed = is_analyzed

        self.graph = nx.DiGraph()

        # Add nodes
        for area_id, area in self.areas.items():
            self.graph.add_node(area_id, node=area)  # Add node with area_id and size as attributes

        # Add edges
        for area_id, area in self.areas.items():
            for connected_area_id in area.connected_areas:
                size_weight = area.size + self.areas[connected_area_id].size
                dist_weight = math.sqrt(
                    (area.centroid.x - self.areas[connected_area_id].centroid.x) ** 2
                    + (area.centroid.y - self.areas[connected_area_id].centroid.y) ** 2
                )
                self.graph.add_edge(
                    area_id,
                    connected_area_id,
                    size=size_weight,
                    dist=dist_weight,
                )  # Add an edge between connected areas

    @classmethod
    def from_path(cls, path: str | Path) -> Self:
        """Initializes and reads a navigation mesh from a file.

        Args:
            path: Path to the nav mesh file to read.

        From: https://github.com/ValveResourceFormat/ValveResourceFormat/blob/6c90d5e46afd8dc4ff326417518769f4fe2c2540/ValveResourceFormat/Resource/ResourceTypes/BinaryKV3.cs

        Raises:
            FileNotFoundError: If the nav mesh file does not exist.
        """
        nav_path = Path(path)
        if not nav_path.exists():
            nav_path_not_found_msg = f"Nav mesh file not found: {nav_path}"
            raise FileNotFoundError(nav_path_not_found_msg)

        with open(nav_path, "rb") as f:
            magic = _read_u32(f)
            if magic != cls.MAGIC:
                unexpected_magic_msg = f"Unexpected magic: {magic:X}, expected {cls.MAGIC:X}"
                raise ValueError(unexpected_magic_msg)

            version = _read_u32(f)
            if version < 30 or version > 36:
                unsupported_version_msg = f"Unsupported nav version: {version}"
                raise ValueError(unsupported_version_msg)

            sub_version = _read_u32(f)

            unk1 = _read_u32(f)
            is_analyzed = (unk1 & 0x00000001) > 0

            if version >= 36:
                cls._skip_kv3(f)  # Skip kv3unk1

            polygons = None
            if version >= 31:
                polygons = cls._read_polygons(f, version)

            if version >= 32:
                f.read(4)  # Skip unk2

            if version >= 35:
                unk_count = _read_u32(f)
                for _ in range(unk_count):
                    while f.read(1) != b"\x00":
                        pass
                    f.read(48)

            if version >= 36:
                cls._skip_kv3(f)  # skip kv3unk2

            areas = cls._read_areas(f, polygons, version)

            # Dont read ladders
            # Dont read Generation Params
            # Dont read custom data
            return cls(
                version=version,
                sub_version=sub_version,
                areas=areas,
                is_analyzed=is_analyzed,
            )

    def __repr__(self) -> str:
        """Returns string representation of Nav."""
        return f"Nav(version={self.version}.{self.sub_version}, areas={len(self.areas)})"

    @classmethod
    def _skip_kv3(cls, f: BinaryIO) -> None:
        """Skip a KV3 blob embedded in a .nav file."""
        while f.read(1) == b"\x00":
            pass
        f.seek(-1, 1)

        cls._skip_binary_kv3(f)

    @classmethod
    def _read_kv3_version(cls, f: BinaryIO) -> int:
        magic_0 = 0x03564B56  # VKV3 - version 0 (not used in navmesh)

        magic = _read_u32(f)

        if magic == magic_0:
            # Version 0 uses a different path (ReadVersion0).
            # Not observed in .nav files; implement if needed.
            msg = "Skipping VKV3 (version 0) is not implemented"
            raise NotImplementedError(msg)

        version = magic & 0xFF
        base_magic = magic & 0xFFFFFF00

        if base_magic != 0x4B563300:
            msg = f"Unsupported KV3 signature: 0x{magic:08X}"
            raise ValueError(msg)
        if version < 2 or version > 5:
            msg = f"Skipping KV3 version {version} not implemented"
            raise NotImplementedError(msg)
        return version

    @classmethod
    def _skip_kv3_buffer(cls, f: BinaryIO, version: int) -> None:  # noqa: PLR0912, PLR0915
        f.read(16)  # Format GUID

        compression_method = CompressionMethod(_read_u32(f))  # 0 = raw, 1 = LZ4, 2 = ZSTD
        _compression_dictionary_id = 0
        _compression_frame_size = 0
        _count_bytes_1 = 0
        _count_bytes_4 = 0
        _count_bytes_8 = 0
        _count_types = 0
        _count_objects = 0
        _count_arrays = 0
        size_uncompressed_total = 0
        size_compressed_total = 0
        count_blocks = 0
        size_binary_blobs_bytes = 0

        if version == 1:
            _count_bytes_1 = _read_i32(f)
            _count_bytes_4 = _read_i32(f)
            _count_bytes_8 = _read_i32(f)
            size_uncompressed_total = _read_i32(f)

            size_compressed_total = 0  # (int)(Size - (reader.BaseStream.Position - Offset));
        else:
            _compression_dictionary_id = _read_u16(f)
            _compression_frame_size = _read_u16(f)
            _count_bytes1 = _read_i32(f)
            _count_bytes4 = _read_i32(f)
            _count_bytes8 = _read_i32(f)
            _count_types = _read_i32(f)
            _count_objects = _read_u16(f)
            _count_arrays = _read_u16(f)
            size_uncompressed_total = _read_i32(f)
            size_compressed_total = _read_i32(f)
            count_blocks = _read_i32(f)
            size_binary_blobs_bytes = _read_i32(f)

        _count_bytes_2 = 0
        _size_block_compressed_sizes_bytes = 0

        if version >= 4:
            _count_bytes_2 = _read_i32(f)
            _size_block_compressed_sizes_bytes = _read_i32(f)

        # Buffer 1 / 2 sizes
        size_uncompressed_buffer_1 = 0
        size_compressed_buffer_1 = 0
        size_uncompressed_buffer_2 = 0
        size_compressed_buffer_2 = 0

        # Buffer2 layout (v5 only)
        _count_bytes1_buffer_2 = 0
        _count_bytes2_buffer_2 = 0
        _count_bytes4_buffer_2 = 0
        _count_bytes8_buffer_2 = 0
        _count_objects_buffer_2 = 0
        _count_arrays_buffer_2 = 0

        if version >= 5:
            size_uncompressed_buffer_1 = _read_i32(f)
            size_compressed_buffer_1 = _read_i32(f)
            size_uncompressed_buffer_2 = _read_i32(f)
            size_compressed_buffer_2 = _read_i32(f)
            _count_bytes1_buffer_2 = _read_i32(f)
            _count_bytes2_buffer_2 = _read_i32(f)
            _count_bytes4_buffer_2 = _read_i32(f)
            _count_bytes8_buffer_2 = _read_i32(f)
            _read_i32(f)  # unk13
            _count_objects_buffer_2 = _read_i32(f)
            _count_arrays_buffer_2 = _read_i32(f)
            _read_i32(f)  # unk16
        else:
            size_compressed_buffer_1 = size_compressed_total
            size_uncompressed_buffer_1 = size_uncompressed_total

        # Buffer 1
        match compression_method:
            case CompressionMethod.RAW:
                f.read(size_uncompressed_buffer_1)
            case CompressionMethod.LZ4:
                f.read(size_compressed_buffer_1)
            case CompressionMethod.ZSTD:
                f.read(size_compressed_buffer_1)

        # Buffer 2
        if version >= 5:
            match compression_method:
                case CompressionMethod.RAW:
                    f.read(size_uncompressed_buffer_2)
                case CompressionMethod.LZ4:
                    f.read(size_compressed_buffer_2)
                case CompressionMethod.ZSTD:
                    f.read(size_compressed_buffer_2)

        # Skip binary blobs section if present
        if count_blocks > 0:
            match compression_method:
                case CompressionMethod.RAW:
                    f.read(size_binary_blobs_bytes)
                case CompressionMethod.LZ4:
                    msg = "LZ4 compression method with blocks not supported yet."
                    raise NotImplementedError(msg)
                case CompressionMethod.ZSTD:
                    if version >= 5:
                        size_compressed_binary_blobs = (
                            size_compressed_total - size_compressed_buffer_1 - size_compressed_buffer_2
                        )
                        f.read(size_compressed_binary_blobs)
                    else:
                        # ZSTD v2-4: blobs already in buffer1; nothing to read from stream
                        pass

            # trailer after blobs
            trailer = _read_u32(f)
            if trailer != 0xFFEEDD00:
                unexpected_magic_msg = f"Unexpected trailed: {trailer:X}"
                raise ValueError(unexpected_magic_msg)

    @classmethod
    def _skip_binary_kv3(cls, f: BinaryIO) -> None:
        """Skip a BinaryKV3 blob, consuming the same bytes from the stream."""
        version = cls._read_kv3_version(f)
        cls._skip_kv3_buffer(f, version)

    @classmethod
    def _read_polygons(cls, br: BinaryIO, version: int) -> list[list[Vector3]]:
        """Reads polygon data from a binary stream.

        Args:
            br: Binary reader stream to read from.
            version: Version of the nav mesh file.

        Returns:
            List of polygons, where each polygon is a list of Vector3 vertices.
        """
        corner_count = _read_u32(br)
        corners: list[Vector3] = []
        for _ in range(corner_count):
            x, y, z = struct.unpack("fff", br.read(12))
            corners.append(Vector3(x, y, z))

        polygon_count = _read_u32(br)
        polygons: list[list[Vector3]] = []
        for _ in range(polygon_count):
            polygons.append(cls._read_polygon(br, corners, version))
        return polygons

    @classmethod
    def _read_polygon(cls, br: BinaryIO, corners: list[Vector3], version: int) -> list[Vector3]:
        """Reads a single polygon from a binary stream.

        Args:
            br: Binary reader stream to read from.
            corners: List of corner vertices to reference.
            version: Version of the nav mesh file.

        Returns:
            List of Vector3 vertices forming the polygon.
        """
        corner_count = br.read(1)[0]
        polygon: list[Vector3] = []
        for _ in range(corner_count):
            corner_index: int = _read_u32(br)
            polygon.append(corners[corner_index])
        if version >= 35:
            br.read(4)  # Skip unk
        return polygon

    @classmethod
    def _read_areas(cls, br: BinaryIO, polygons: list[list[Vector3]] | None, version: int) -> dict[int, NavArea]:
        """Reads all navigation areas from a binary stream.

        Args:
            br: Binary reader stream to read from.
            polygons: Optional list of predefined polygons for version 31+.
            version: Version of the nav mesh file.
        """
        areas: dict[int, NavArea] = {}
        area_count = _read_u32(br)
        for _ in range(area_count):
            area = NavArea.from_data(br, version, polygons)
            areas[area.area_id] = area
        return areas

    def find_path(
        self,
        start_id: int,
        end_id: int,
        weight: Literal["size", "dist"] | None = None,
    ) -> list[NavArea]:
        """Finds the path between two areas in the graph.

        Args:
            start_id: The area ID of the starting NavArea.
            end_id: The area ID of the ending NavArea.
            weight: The edge attribute to use as weight (optional).
                    If None, treats edges as unweighted.
                    Size treats edges as the sum of the areas' sizes.
                    Dist treats edges as the Euclidean distance between centroids.

        Returns:
            A list of NavArea objects representing the path from start to end.
            Returns an empty list if no path exists.
        """
        try:
            # Get the shortest path as a list of area IDs
            path_ids = nx.shortest_path(self.graph, source=start_id, target=end_id, weight=weight)
            # Convert area IDs to NavArea objects
            return [self.graph.nodes[area_id]["node"] for area_id in path_ids]
        except nx.NetworkXNoPath:
            return []  # No path exists

    def to_dict(self) -> NavDict:
        """Converts the entire navigation mesh to a dictionary."""
        return {
            "version": self.version,
            "sub_version": self.sub_version,
            "is_analyzed": self.is_analyzed,
            "areas": {area_id: area.to_dict() for area_id, area in self.areas.items()},
        }

    def to_json(self, path: str | Path) -> None:
        """Writes the navigation mesh data to a JSON file.

        Args:
            path: Path to the JSON file to write.
        """
        nav_dict = self.to_dict()
        with open(path, "w", encoding="utf-8") as json_file:
            json.dump(nav_dict, json_file)
            json_file.write("\n")

    @classmethod
    def from_json(cls, path: str | Path) -> "Nav":
        """Reads the navigation mesh data from a JSON file.

        Args:
            path: Path to the JSON file to read from.
        """
        nav_dict: NavDict = json.loads(Path(path).read_text())
        return cls(
            version=nav_dict["version"],
            sub_version=nav_dict["sub_version"],
            areas={int(area_id): NavArea.from_dict(area_dict) for area_id, area_dict in nav_dict["areas"].items()},
            is_analyzed=nav_dict["is_analyzed"],
        )
