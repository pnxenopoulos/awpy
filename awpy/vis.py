"""Module for calculating visibility.

Reference: https://github.com/AtomicBool/cs2-map-parser
"""

import pathlib
import struct
from collections import deque
from dataclasses import dataclass

import numpy.typing as npt
from loguru import logger

from awpy.vector import Vector3


@dataclass
class Triangle:
    """A triangle in 3D space defined by three vertices.

    Attributes:
        p1: First vertex of the triangle.
        p2: Second vertex of the triangle.
        p3: Third vertex of the triangle.
    """

    p1: Vector3
    p2: Vector3
    p3: Vector3


@dataclass
class Edge:
    """An edge in a triangulated mesh.

    Attributes:
        next: Index of the next edge in the face.
        twin: Index of the twin edge in the adjacent face.
        origin: Index of the vertex where this edge starts.
        face: Index of the face this edge belongs to.
    """

    next: int
    twin: int
    origin: int
    face: int


class KV3Parser:
    """Parser for KV3 format files used in Source 2 engine.

    This class provides functionality to parse KV3 files, which are used to store
    various game data including physics collision meshes.

    Attributes:
        content: Raw content of the KV3 file.
        index: Current parsing position in the content.
        parsed_data: Resulting parsed data structure.
    """

    def __init__(self) -> None:
        """Initialize a new KV3Parser instance."""
        self.content = ""
        self.index = 0
        self.parsed_data = None

    def parse(self, content: str) -> None:
        """Parse the given KV3 content string.

        Args:
            content: String containing KV3 formatted data.
        """
        self.content = content
        self.index = 0
        self._skip_until_first_bracket()
        self.parsed_data = self._parse_value()

    def get_value(self, path: str) -> str:
        """Get a value from the parsed data using a dot-separated path.

        Args:
            path: Dot-separated path to the desired value, e.g.,
                "section.subsection[0].value"

        Returns:
            String value at the specified path, or empty string
                if not found.
        """
        if not self.parsed_data:
            return ""

        current = self.parsed_data
        for segment in path.split("."):
            key = segment
            array_index = None

            if "[" in segment:
                key = segment[: segment.find("[")]
                array_index = int(segment[segment.find("[") + 1 : segment.find("]")])

            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return ""

            if array_index is not None:
                if isinstance(current, list) and array_index < len(current):
                    current = current[array_index]
                else:
                    return ""

        return current if isinstance(current, str) else ""

    def _skip_until_first_bracket(self) -> None:
        """Skip content until the first opening bracket is found."""
        while self.index < len(self.content) and self.content[self.index] != "{":
            self.index = self.content.find("\n", self.index) + 1

    def _skip_whitespace(self) -> None:
        """Skip all whitespace characters at the current position."""
        while self.index < len(self.content) and self.content[self.index].isspace():
            self.index += 1

    def _parse_value(self) -> dict | list | str | None:
        """Parse a value from the current position.

        Returns:
            Parsed value which can be a dictionary, list, or string,
                or None if parsing fails.
        """
        self._skip_whitespace()
        if self.index >= len(self.content):
            return None

        char = self.content[self.index]
        if char == "{":
            return self._parse_object()
        if char == "[":
            return self._parse_array()
        if (
            char == "#"
            and self.index + 1 < len(self.content)
            and self.content[self.index + 1] == "["
        ):
            self.index += 1
            return self._parse_byte_array()
        return self._parse_string()

    def _parse_object(self) -> dict:
        """Parse a KV3 object starting at the current position.

        Returns:
            Dictionary containing the parsed key-value pairs.
        """
        self.index += 1  # Skip {
        obj = {}
        while self.index < len(self.content):
            self._skip_whitespace()
            if self.content[self.index] == "}":
                self.index += 1
                return obj

            key = self._parse_string()
            self._skip_whitespace()
            if self.content[self.index] == "=":
                self.index += 1

            value = self._parse_value()
            if key and value is not None:
                obj[key] = value

            self._skip_whitespace()
            if self.content[self.index] == ",":
                self.index += 1

        return obj

    def _parse_array(self) -> list:
        """Parse a KV3 array starting at the current position.

        Returns:
            List containing the parsed values.
        """
        self.index += 1  # Skip [
        arr = []
        while self.index < len(self.content):
            self._skip_whitespace()
            if self.content[self.index] == "]":
                self.index += 1
                return arr

            value = self._parse_value()
            if value is not None:
                arr.append(value)

            self._skip_whitespace()
            if self.content[self.index] == ",":
                self.index += 1
        return arr

    def _parse_byte_array(self) -> str:
        """Parse a KV3 byte array starting at the current position.

        Returns:
            Space-separated string of byte values.
        """
        self.index += 1  # Skip [
        start = self.index
        while self.index < len(self.content) and self.content[self.index] != "]":
            self.index += 1
        byte_str = self.content[start : self.index].strip()
        self.index += 1  # Skip ]
        return " ".join(byte_str.split())

    def _parse_string(self) -> str:
        """Parse a string value at the current position.

        Returns:
            Parsed string value.
        """
        start = self.index
        while self.index < len(self.content):
            char = self.content[self.index]
            if char in "={}[], \n":
                break
            self.index += 1
        return self.content[start : self.index].strip()


class VphysParser:
    """Parser for VPhys collision files.

    This class extracts and processes collision geometry data
        from VPhys files, converting it into a set of triangles.

    Attributes:
        vphys_file (Path): Path to the VPhys file.
        triangles (list[Triangle]): List of parsed triangles from the VPhys file.
        kv3_parser (KV3Parser): Helper parser for extracting key-value data from
            the .vphys file.
    """

    def __init__(self, vphys_file: str | pathlib.Path) -> None:
        """Initializes the parser with the path to a VPhys file.

        Args:
            vphys_file (str | pathlib.Path): Path to the VPhys file
                to parse.
        """
        self.vphys_file = pathlib.Path(vphys_file)
        self.triangles = []
        self.kv3_parser = KV3Parser()
        self.parse()

    @staticmethod
    def bytes_to_vec(byte_str: str, element_size: int) -> list[int | float]:
        """Converts a space-separated string of byte values into a list of numbers.

        Args:
            byte_str (str): Space-separated string of hexadecimal byte values.
            element_size (int): Number of bytes per element (1 for
                uint8, 4 for float/int32).

        Returns:
            list[int | float]: List of converted values (integers for
                uint8, floats for size 4).
        """
        bytes_list = [int(b, 16) for b in byte_str.split()]
        result = []

        if element_size == 1:  # uint8
            return bytes_list

        # Convert bytes to appropriate type based on size
        for i in range(0, len(bytes_list), element_size):
            chunk = bytes(bytes_list[i : i + element_size])
            if element_size == 4:  # float or int32
                val = struct.unpack("f", chunk)[0]  # Assume float for size 4
                result.append(val)

        return result

    def parse(self) -> None:
        """Parses the VPhys file and extracts collision geometry.

        Processes hulls and meshes in the VPhys file to generate a list of triangles.
        """
        if len(self.triangles) > 0:
            logger.debug(
                f"VPhys data already parsed, got {len(self.triangles)} triangles."
            )
            return

        logger.debug(f"Parsing vphys file: {self.vphys_file}")

        # Read file
        with open(self.vphys_file) as f:
            data = f.read()

        # Parse VPhys data
        self.kv3_parser.parse(data)

        # Process hulls
        hull_idx = 0
        hull_count = 0
        while True:
            if hull_idx % 1000 == 0:
                logger.debug(f"Processing hull {hull_idx}...")

            collision_idx = self.kv3_parser.get_value(
                f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_nCollisionAttributeIndex"
            )
            if not collision_idx:
                break

            if collision_idx == "0":
                # Get vertices
                vertex_str = self.kv3_parser.get_value(
                    f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_VertexPositions"
                )
                if not vertex_str:
                    vertex_str = self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Vertices"
                    )

                vertex_data = self.bytes_to_vec(vertex_str, 4)
                vertices = [
                    Vector3(vertex_data[i], vertex_data[i + 1], vertex_data[i + 2])
                    for i in range(0, len(vertex_data), 3)
                ]

                # Get faces and edges
                faces = self.bytes_to_vec(
                    self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Faces"
                    ),
                    1,
                )
                edge_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Edges"
                    ),
                    1,
                )

                edges = [
                    Edge(
                        edge_data[i],
                        edge_data[i + 1],
                        edge_data[i + 2],
                        edge_data[i + 3],
                    )
                    for i in range(0, len(edge_data), 4)
                ]

                # Process triangles
                for start_edge in faces:
                    edge = edges[start_edge].next
                    while edge != start_edge:
                        next_edge = edges[edge].next
                        self.triangles.append(
                            Triangle(
                                vertices[edges[start_edge].origin],
                                vertices[edges[edge].origin],
                                vertices[edges[next_edge].origin],
                            )
                        )
                        edge = next_edge

                hull_count += 1
            hull_idx += 1

        # Process meshes
        mesh_idx = 0
        mesh_count = 0
        while True:
            collision_idx = self.kv3_parser.get_value(
                f"m_parts[0].m_rnShape.m_meshes[{mesh_idx}].m_nCollisionAttributeIndex"
            )
            if not collision_idx:
                break

            if collision_idx == "0":
                # Get triangles and vertices
                tri_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_meshes.[{mesh_idx}].m_Mesh.m_Triangles"
                    ),
                    4,
                )
                vertex_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_meshes.[{mesh_idx}].m_Mesh.m_Vertices"
                    ),
                    4,
                )

                vertices = [
                    Vector3(vertex_data[i], vertex_data[i + 1], vertex_data[i + 2])
                    for i in range(0, len(vertex_data), 3)
                ]

                for i in range(0, len(tri_data), 3):
                    self.triangles.append(
                        Triangle(
                            vertices[int(tri_data[i])],
                            vertices[int(tri_data[i + 1])],
                            vertices[int(tri_data[i + 2])],
                        )
                    )

                mesh_count += 1
            mesh_idx += 1

    def to_tri(self, path: str | pathlib.Path | None) -> None:
        """Export parsed triangles to a .tri file.

        Args:
            path: Path to the output .tri file.
        """
        if not path:
            path = self.vphys_file.with_suffix(".tri")
        outpath = pathlib.Path(path)

        logger.debug(f"Exporting {len(self.triangles)} triangles to {outpath}")
        with open(outpath, "wb") as f:
            for triangle in self.triangles:
                # Write all Vector3 components as float32
                f.write(struct.pack("f", triangle.p1.x))
                f.write(struct.pack("f", triangle.p1.y))
                f.write(struct.pack("f", triangle.p1.z))
                f.write(struct.pack("f", triangle.p2.x))
                f.write(struct.pack("f", triangle.p2.y))
                f.write(struct.pack("f", triangle.p2.z))
                f.write(struct.pack("f", triangle.p3.x))
                f.write(struct.pack("f", triangle.p3.y))
                f.write(struct.pack("f", triangle.p3.z))

        logger.success(
            f"Processed {len(self.triangles)} triangles from {self.vphys_file} -> {outpath}"  # noqa: E501
        )


@dataclass
class AABB:
    """Represents an axis-aligned bounding box (AABB).

    An AABB is defined by its minimum and maximum points in 3D space.

    Attributes:
        min_point (Vector3): The minimum corner of the bounding box.
        max_point (Vector3): The maximum corner of the bounding box.
    """

    min_point: Vector3
    max_point: Vector3

    def triangle_intersects(self, triangle: "Triangle") -> bool:
        """Tests whether a triangle intersects with the AABB.

        Uses a fast, conservative triangle-AABB intersection test.

        Args:
            triangle (Triangle): The triangle to test for intersection.

        Returns:
            bool: True if the triangle intersects with the AABB, False otherwise.
        """
        # Compute the center of the triangle
        center = Vector3(
            (triangle.p1.x + triangle.p2.x + triangle.p3.x) / 3,
            (triangle.p1.y + triangle.p2.y + triangle.p3.y) / 3,
            (triangle.p1.z + triangle.p2.z + triangle.p3.z) / 3,
        )

        # Simple AABB test for the triangle's center
        if not self.contains_point(center):
            max_x = max(triangle.p1.x, triangle.p2.x, triangle.p3.x)
            min_x = min(triangle.p1.x, triangle.p2.x, triangle.p3.x)
            max_y = max(triangle.p1.y, triangle.p2.y, triangle.p3.y)
            min_y = min(triangle.p1.y, triangle.p2.y, triangle.p3.y)
            max_z = max(triangle.p1.z, triangle.p2.z, triangle.p3.z)
            min_z = min(triangle.p1.z, triangle.p2.z, triangle.p3.z)

            # Check if the triangle's bounds overlap the AABB
            if (
                max_x < self.min_point.x
                or min_x > self.max_point.x
                or max_y < self.min_point.y
                or min_y > self.max_point.y
                or max_z < self.min_point.z
                or min_z > self.max_point.z
            ):
                return False

        return True  # Conservative estimate

    def contains_point(self, point: Vector3) -> bool:
        """Checks if a point is inside the AABB.

        Args:
            point (Vector3): The point to test.

        Returns:
            bool: True if the point is inside the AABB, False otherwise.
        """
        return (
            self.min_point.x <= point.x <= self.max_point.x
            and self.min_point.y <= point.y <= self.max_point.y
            and self.min_point.z <= point.z <= self.max_point.z
        )

    def intersects_ray(self, origin: Vector3, direction: Vector3) -> bool:
        """Tests whether a ray intersects with the AABB.

        Uses an efficient ray-AABB intersection algorithm.

        Args:
            origin (Vector3): The origin point of the ray.
            direction (Vector3): The direction vector of the ray.

        Returns:
            bool: True if the ray intersects with the AABB, False otherwise.
        """
        inv_dir = Vector3(
            1.0 / direction.x if direction.x != 0 else float("inf"),
            1.0 / direction.y if direction.y != 0 else float("inf"),
            1.0 / direction.z if direction.z != 0 else float("inf"),
        )

        t1 = (self.min_point.x - origin.x) * inv_dir.x
        t2 = (self.max_point.x - origin.x) * inv_dir.x
        t3 = (self.min_point.y - origin.y) * inv_dir.y
        t4 = (self.max_point.y - origin.y) * inv_dir.y
        t5 = (self.min_point.z - origin.z) * inv_dir.z
        t6 = (self.max_point.z - origin.z) * inv_dir.z

        tmin = max(min(t1, t2), min(t3, t4), min(t5, t6))
        tmax = min(max(t1, t2), max(t3, t4), max(t5, t6))

        return tmax >= 0 and tmin <= tmax


class OctreeNode:
    """Represents a node in an octree for spatial partitioning.

    Each node may contain triangles or have up to 8 child nodes to subdivide the space.

    Attributes:
        bounds (AABB): The axis-aligned bounding box node region.
        triangles (list[Triangle]): List of triangles contained in this node.
        children (list[OctreeNode | None]): List of child nodes, or None if no children.
        max_triangles (int): Max tri allowed in leaf before splitting.
        max_depth (int): Maximum depth of the octree to prevent infinite subdivision.
    """

    def __init__(
        self, bounds: AABB, max_triangles: int = 32, max_depth: int = 10
    ) -> None:
        """Initializes an octree node.

        Args:
            bounds (AABB): The bounding box defining the spatial limits of this node.
            max_triangles (int, optional): Max tri in leaf before split. Defaults to 32.
            max_depth (int, optional): Maximum depth of the octree. Defaults to 10.
        """
        self.bounds = bounds
        self.triangles: list[Triangle] = []
        self.children: list[OctreeNode | None] = [None] * 8
        self.max_triangles = max_triangles
        self.max_depth = max_depth

    def insert(self, triangle: Triangle, depth: int = 0) -> None:
        """Inserts a triangle into the octree node, splitting the node if necessary.

        Args:
            triangle (Triangle): The triangle to insert.
            depth (int, optional): Current node depth in the octree. Defaults to 0.
        """
        if depth >= self.max_depth:
            self.triangles.append(triangle)
            return

        if not self.children[0]:  # Leaf node
            if len(self.triangles) < self.max_triangles:
                self.triangles.append(triangle)
                return

            # Split node
            center = Vector3(
                (self.bounds.min_point.x + self.bounds.max_point.x) / 2,
                (self.bounds.min_point.y + self.bounds.max_point.y) / 2,
                (self.bounds.min_point.z + self.bounds.max_point.z) / 2,
            )

            # Create eight children
            for i in range(8):
                min_point = Vector3(
                    self.bounds.min_point.x if (i & 1) == 0 else center.x,
                    self.bounds.min_point.y if (i & 2) == 0 else center.y,
                    self.bounds.min_point.z if (i & 4) == 0 else center.z,
                )
                max_point = Vector3(
                    center.x if (i & 1) == 0 else self.bounds.max_point.x,
                    center.y if (i & 2) == 0 else self.bounds.max_point.y,
                    center.z if (i & 4) == 0 else self.bounds.max_point.z,
                )
                self.children[i] = OctreeNode(
                    AABB(min_point, max_point), self.max_triangles, self.max_depth
                )

            # Redistribute existing triangles
            old_triangles = self.triangles
            self.triangles = []
            for tri in old_triangles:
                self._insert_to_children(tri, depth + 1)

            # Insert new triangle
            self._insert_to_children(triangle, depth + 1)
        else:
            self._insert_to_children(triangle, depth + 1)

    def _insert_to_children(self, triangle: Triangle, depth: int) -> None:
        """Attempts to insert a triangle into the child nodes of this node.

        Args:
            triangle (Triangle): The triangle to insert.
            depth (int): Current depth of the node in the octree.
        """
        for child in self.children:
            if child and self.bounds.triangle_intersects(triangle, child.bounds):
                child.insert(triangle, depth)


class VisibilityChecker:
    """Class for visibility checking in 3D space using an octree structure."""

    def __init__(self, triangles: list[Triangle]) -> None:
        """Initializes the VisibilityChecker with a set of triangles.

        Args:
            triangles (list[Triangle]): List of triangles representing the 3D scene.
        """
        # Find bounds for octree
        min_x = min(min(tri.p1.x, tri.p2.x, tri.p3.x) for tri in triangles)
        max_x = max(max(tri.p1.x, tri.p2.x, tri.p3.x) for tri in triangles)
        min_y = min(min(tri.p1.y, tri.p2.y, tri.p3.y) for tri in triangles)
        max_y = max(max(tri.p1.y, tri.p2.y, tri.p3.y) for tri in triangles)
        min_z = min(min(tri.p1.z, tri.p2.z, tri.p3.z) for tri in triangles)
        max_z = max(max(tri.p1.z, tri.p2.z, tri.p3.z) for tri in triangles)

        # Add some padding
        padding = 1.0
        bounds = AABB(
            Vector3(min_x - padding, min_y - padding, min_z - padding),
            Vector3(max_x + padding, max_y + padding, max_z + padding),
        )

        # Build octree
        self.root = OctreeNode(bounds)
        for triangle in triangles:
            self.root.insert(triangle)

    @staticmethod
    def read_tri_file(tri_file: str | pathlib.Path) -> list[Triangle]:
        """Reads a .tri file and returns a list of triangles.

        Args:
            tri_file (str | pathlib.Path): Path to the .tri file.

        Returns:
            list[Triangle]: List of triangles parsed from the file.
        """
        tri_file = pathlib.Path(tri_file)
        triangles = []
        with open(tri_file, "rb") as f:
            while True:
                # Try to read 9 floats (3 vertices * 3 coordinates)
                data = f.read(9 * 4)  # 4 bytes per float
                if not data or len(data) < 36:  # EOF or incomplete triangle
                    break

                # Unpack 9 floats
                values = struct.unpack("9f", data)

                # Create triangle from values
                triangle = Triangle(
                    Vector3(values[0], values[1], values[2]),
                    Vector3(values[3], values[4], values[5]),
                    Vector3(values[6], values[7], values[8]),
                )
                triangles.append(triangle)

        return triangles

    @staticmethod
    def ray_intersects_triangle(
        origin: Vector3, direction: Vector3, triangle: Triangle, epsilon: float = 1e-7
    ) -> float | None:
        """Moller-Trumbore ray-triangle intersection algorithm.

        Args:
            origin (Vector3 | tuple | list | np.ndarray): Ray origin.
            direction (Vector3 | tuple | list | np.ndarray): Ray direction.
            triangle (Triangle): The triangle to test intersection with.
            epsilon (float, optional): Tolerance for comparisons. Defaults to 1e-7.

        Returns:
            float | None: Distance to intersect point, or None if no intersection.
        """
        origin = Vector3.from_input(origin)
        direction = Vector3.from_input(direction)

        edge1 = Vector3(
            triangle.p2.x - triangle.p1.x,
            triangle.p2.y - triangle.p1.y,
            triangle.p2.z - triangle.p1.z,
        )
        edge2 = Vector3(
            triangle.p3.x - triangle.p1.x,
            triangle.p3.y - triangle.p1.y,
            triangle.p3.z - triangle.p1.z,
        )

        h = Vector3(
            direction.y * edge2.z - direction.z * edge2.y,
            direction.z * edge2.x - direction.x * edge2.z,
            direction.x * edge2.y - direction.y * edge2.x,
        )

        a = edge1.x * h.x + edge1.y * h.y + edge1.z * h.z
        if abs(a) < epsilon:
            return None

        f = 1.0 / a
        s = Vector3(
            origin.x - triangle.p1.x, origin.y - triangle.p1.y, origin.z - triangle.p1.z
        )

        u = f * (s.x * h.x + s.y * h.y + s.z * h.z)
        if u < 0.0 or u > 1.0:
            return None

        q = Vector3(
            s.y * edge1.z - s.z * edge1.y,
            s.z * edge1.x - s.x * edge1.z,
            s.x * edge1.y - s.y * edge1.x,
        )

        v = f * (direction.x * q.x + direction.y * q.y + direction.z * q.z)
        if v < 0.0 or u + v > 1.0:
            return None

        t = f * (edge2.x * q.x + edge2.y * q.y + edge2.z * q.z)
        return t if t > epsilon else None

    def is_visible(
        self,
        start: Vector3 | tuple | list | npt.NDArray,
        end: Vector3 | tuple | list | npt.NDArray,
    ) -> bool:
        """Check if there's a clear line of sight between start and end points.

        Args:
            start (Vector3 | tuple | list | npt.NDArray): Start point of the vis line.
            end (Vector3 | tuple | list | npt.NDArray): End point of the vis line.

        Returns:
            bool: True if the line of sight is clear, False otherwise.
        """
        start = Vector3.from_input(start)
        end = Vector3.from_input(end)

        direction = Vector3(end.x - start.x, end.y - start.y, end.z - start.z)
        length = (direction.x**2 + direction.y**2 + direction.z**2) ** 0.5
        if length < 1e-7:
            return True

        # Normalize direction
        direction.x /= length
        direction.y /= length
        direction.z /= length

        # Use queue for iterative traversal instead of recursion
        queue = deque([(self.root, 0.0, length)])
        while queue:
            node, tmin, tmax = queue.popleft()

            # Check node's triangles
            for triangle in node.triangles:
                t = self.ray_intersects_triangle(start, direction, triangle)
                if t is not None and t <= length:
                    return False

            # Add child nodes that intersect the ray
            if node.children[0]:  # If this node has children
                for child in node.children:
                    if child and child.bounds.intersects_ray(start, direction):
                        queue.append((child, tmin, tmax))

        return True
