"""Module for calculating visibility.

Reference: https://github.com/AtomicBool/cs2-map-parser
"""

from __future__ import annotations

import pathlib
import struct
from dataclasses import dataclass
from typing import Literal, overload

from loguru import logger

import awpy.vector


@dataclass
class Triangle:
    """A triangle in 3D space defined by three vertices.

    Attributes:
        p1: First vertex of the triangle.
        p2: Second vertex of the triangle.
        p3: Third vertex of the triangle.
    """

    p1: awpy.vector.Vector3
    p2: awpy.vector.Vector3
    p3: awpy.vector.Vector3

    def get_centroid(self) -> awpy.vector.Vector3:
        """Calculate the centroid of the triangle.

        Returns:
            awpy.vector.Vector3: Centroid of the triangle.
        """
        return awpy.vector.Vector3(
            (self.p1.x + self.p2.x + self.p3.x) / 3,
            (self.p1.y + self.p2.y + self.p3.y) / 3,
            (self.p1.z + self.p2.z + self.p3.z) / 3,
        )


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
        if char == "#" and self.index + 1 < len(self.content) and self.content[self.index + 1] == "[":
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
        self.triangles: list[Triangle] = []
        self.kv3_parser = KV3Parser()
        self.parse()

    @overload
    @staticmethod
    def bytes_to_vec(byte_str: str, element_type: Literal["uint8", "int32"]) -> list[int]: ...

    @overload
    @staticmethod
    def bytes_to_vec(byte_str: str, element_type: Literal["float"]) -> list[float]: ...

    @staticmethod
    def bytes_to_vec(byte_str: str, element_type: Literal["uint8", "int32", "float"]) -> list[int] | list[float]:
        """Converts a space-separated string of byte values into a list of numbers.

        Args:
            byte_str (str): Space-separated string of hexadecimal byte values.
            element_type (int): Types represented by the bytes (uint8, int32, float).

        Returns:
            list[int | float]: List of converted values (integers for
                uint8, floats for size 4).
        """
        bytes_list = [int(b, 16) for b in byte_str.split()]
        result = []

        if element_type == "uint8":
            return bytes_list

        element_size = 4  # For int and float

        # Convert bytes to appropriate type based on size
        for i in range(0, len(bytes_list), element_size):
            chunk = bytes(bytes_list[i : i + element_size])
            if element_type == "float":  # float
                val = struct.unpack("f", chunk)[0]
                result.append(val)
            else:  # int32
                val = struct.unpack("i", chunk)[0]
                result.append(val)
        return result

    def get_collision_attribute_indices_for_default_group(self) -> list[str]:
        """Get collision attribute indices for the default group.

        Returns:
            list[int]: List of collision attribute indices for the default group.
        """
        collision_attribute_indices = []
        idx = 0
        while True:
            collision_group_string = self.kv3_parser.get_value(f"m_collisionAttributes[{idx}].m_CollisionGroupString")
            if not collision_group_string:
                break
            if collision_group_string.lower() == '"default"':
                collision_attribute_indices.append(str(idx))
            idx += 1
        return collision_attribute_indices

    def parse(self) -> None:
        """Parses the VPhys file and extracts collision geometry.

        Processes hulls and meshes in the VPhys file to generate a list of triangles.
        """
        if len(self.triangles) > 0:
            logger.debug(f"VPhys data already parsed, got {len(self.triangles)} triangles.")
            return

        logger.debug(f"Parsing vphys file: {self.vphys_file}")

        # Read file
        with open(self.vphys_file) as f:
            data = f.read()

        # Parse VPhys data
        self.kv3_parser.parse(data)

        collision_attribute_indices = self.get_collision_attribute_indices_for_default_group()

        logger.debug(f"Extracted collision attribute indices: {collision_attribute_indices}")

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

            if collision_idx in collision_attribute_indices:
                # Get vertices
                vertex_str = self.kv3_parser.get_value(
                    f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_VertexPositions"
                )
                if not vertex_str:
                    vertex_str = self.kv3_parser.get_value(
                        f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Vertices"
                    )

                vertex_data = self.bytes_to_vec(vertex_str, "float")
                vertices = [
                    awpy.vector.Vector3(vertex_data[i], vertex_data[i + 1], vertex_data[i + 2])
                    for i in range(0, len(vertex_data), 3)
                ]

                # Get faces and edges
                faces = self.bytes_to_vec(
                    self.kv3_parser.get_value(f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Faces"),
                    "uint8",
                )
                edge_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(f"m_parts[0].m_rnShape.m_hulls[{hull_idx}].m_Hull.m_Edges"),
                    "uint8",
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
            logger.debug(f"Processing mesh {mesh_idx}...")
            collision_idx = self.kv3_parser.get_value(
                f"m_parts[0].m_rnShape.m_meshes[{mesh_idx}].m_nCollisionAttributeIndex"
            )
            if not collision_idx:
                break

            if collision_idx in collision_attribute_indices:
                # Get triangles and vertices
                tri_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(f"m_parts[0].m_rnShape.m_meshes[{mesh_idx}].m_Mesh.m_Triangles"),
                    "int32",
                )
                vertex_data = self.bytes_to_vec(
                    self.kv3_parser.get_value(f"m_parts[0].m_rnShape.m_meshes[{mesh_idx}].m_Mesh.m_Vertices"),
                    "float",
                )

                vertices = [
                    awpy.vector.Vector3(vertex_data[i], vertex_data[i + 1], vertex_data[i + 2])
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
                # Write all awpy.vector.Vector3 components as float32
                f.write(struct.pack("f", triangle.p1.x))
                f.write(struct.pack("f", triangle.p1.y))
                f.write(struct.pack("f", triangle.p1.z))
                f.write(struct.pack("f", triangle.p2.x))
                f.write(struct.pack("f", triangle.p2.y))
                f.write(struct.pack("f", triangle.p2.z))
                f.write(struct.pack("f", triangle.p3.x))
                f.write(struct.pack("f", triangle.p3.y))
                f.write(struct.pack("f", triangle.p3.z))

        logger.success(f"Processed {len(self.triangles)} triangles from {self.vphys_file} -> {outpath}")


class AABB:
    """Axis-Aligned Bounding Box for efficient collision detection."""

    def __init__(self, min_point: awpy.vector.Vector3, max_point: awpy.vector.Vector3) -> None:
        """Initialize the AABB with minimum and maximum points.

        Args:
            min_point (awpy.vector.Vector3): Minimum point of the AABB.
            max_point (awpy.vector.Vector3): Maximum point of the AABB.
        """
        self.min_point = min_point
        self.max_point = max_point

    @classmethod
    def from_triangle(cls, triangle: Triangle) -> AABB:
        """Create an AABB from a triangle.

        Args:
            triangle (Triangle): Triangle to create the AABB from.

        Returns:
            AABB: Axis-Aligned Bounding Box encompassing the triangle.
        """
        min_point = awpy.vector.Vector3(
            min(triangle.p1.x, triangle.p2.x, triangle.p3.x),
            min(triangle.p1.y, triangle.p2.y, triangle.p3.y),
            min(triangle.p1.z, triangle.p2.z, triangle.p3.z),
        )
        max_point = awpy.vector.Vector3(
            max(triangle.p1.x, triangle.p2.x, triangle.p3.x),
            max(triangle.p1.y, triangle.p2.y, triangle.p3.y),
            max(triangle.p1.z, triangle.p2.z, triangle.p3.z),
        )
        return cls(min_point, max_point)

    def intersects_ray(self, ray_origin: awpy.vector.Vector3, ray_direction: awpy.vector.Vector3) -> bool:
        """Check if a ray intersects with the AABB.

        Args:
            ray_origin (awpy.vector.Vector3): Ray origin point.
            ray_direction (awpy.vector.Vector3): Ray direction vector.

        Returns:
            bool: True if the ray intersects with the AABB, False otherwise.
        """
        epsilon = 1e-6

        def check_axis(origin: float, direction: float, min_val: float, max_val: float) -> tuple[float, float]:
            if abs(direction) < epsilon:
                if origin < min_val or origin > max_val:
                    return float("inf"), float("-inf")
                return float("-inf"), float("inf")

            t1 = (min_val - origin) / direction
            t2 = (max_val - origin) / direction
            return (min(t1, t2), max(t1, t2))

        tx_min, tx_max = check_axis(ray_origin.x, ray_direction.x, self.min_point.x, self.max_point.x)
        ty_min, ty_max = check_axis(ray_origin.y, ray_direction.y, self.min_point.y, self.max_point.y)
        tz_min, tz_max = check_axis(ray_origin.z, ray_direction.z, self.min_point.z, self.max_point.z)

        t_enter = max(tx_min, ty_min, tz_min)
        t_exit = min(tx_max, ty_max, tz_max)

        return t_enter <= t_exit and t_exit >= 0


class BVHNode:
    """Node in the Bounding Volume Hierarchy tree."""

    def __init__(
        self,
        aabb: AABB,
        triangle: Triangle | None = None,
        left: BVHNode | None = None,
        right: BVHNode | None = None,
    ) -> None:
        """Initialize a BVHNode with an AABB and optional triangle and children.

        Args:
            aabb (AABB): Axis-Aligned Bounding Box of the node.
            triangle (Triangle | None, optional): Triangle contained
                in the node. Defaults to None.
            left (BVHNode | None, optional): Left child node. Defaults to None.
            right (BVHNode | None, optional): Right child node. Defaults to None.
        """
        self.aabb = aabb
        self.triangle = triangle
        self.left = left
        self.right = right


class VisibilityChecker:
    """Class for visibility checking in 3D space using a BVH structure."""

    def __init__(self, path: pathlib.Path | None = None, triangles: list[Triangle] | None = None) -> None:
        """Initialize the visibility checker with a list of triangles.

        Args:
            path (pathlib.Path | None, optional): Path to a .tri file to read
                triangles from.
            triangles (list[Triangle] | None, optional): List of triangles to
                build the BVH from.
        """
        if path is not None:
            triangles = self.read_tri_file(path)
        self.n_triangles = len(triangles)
        self.root = self._build_bvh(triangles)

    def __repr__(self) -> str:
        """Return a string representation of the VisibilityChecker."""
        return f"VisibilityChecker(n_triangles={self.n_triangles})"

    def _build_bvh(self, triangles: list[Triangle]) -> BVHNode:
        """Build a BVH tree from a list of triangles.

        Args:
            triangles (list[Triangle]): List of triangles to build the BVH from.

        Returns:
            BVHNode: Root node of the BVH tree.
        """
        if len(triangles) == 1:
            return BVHNode(AABB.from_triangle(triangles[0]), triangle=triangles[0])

        # Calculate centroids and find split axis
        centroids = [t.get_centroid() for t in triangles]

        # Find the axis with the largest spread
        min_x = min(c.x for c in centroids)
        max_x = max(c.x for c in centroids)
        min_y = min(c.y for c in centroids)
        max_y = max(c.y for c in centroids)
        min_z = min(c.z for c in centroids)
        max_z = max(c.z for c in centroids)

        x_spread = max_x - min_x
        y_spread = max_y - min_y
        z_spread = max_z - min_z

        # Choose split axis
        if x_spread >= y_spread and x_spread >= z_spread:
            axis = 0  # x-axis
        elif y_spread >= z_spread:
            axis = 1  # y-axis
        else:
            axis = 2  # z-axis

        # Sort triangles based on centroid position
        triangles = sorted(
            triangles,
            key=lambda t: (
                t.get_centroid().x if axis == 0 else t.get_centroid().y if axis == 1 else t.get_centroid().z
            ),
        )

        # Split triangles into two groups
        mid = len(triangles) // 2
        left = self._build_bvh(triangles[:mid])
        right = self._build_bvh(triangles[mid:])

        # Create encompassing AABB
        min_point = awpy.vector.Vector3(
            min(left.aabb.min_point.x, right.aabb.min_point.x),
            min(left.aabb.min_point.y, right.aabb.min_point.y),
            min(left.aabb.min_point.z, right.aabb.min_point.z),
        )
        max_point = awpy.vector.Vector3(
            max(left.aabb.max_point.x, right.aabb.max_point.x),
            max(left.aabb.max_point.y, right.aabb.max_point.y),
            max(left.aabb.max_point.z, right.aabb.max_point.z),
        )

        return BVHNode(AABB(min_point, max_point), left=left, right=right)

    def _ray_triangle_intersection(
        self,
        ray_origin: awpy.vector.Vector3,
        ray_direction: awpy.vector.Vector3,
        triangle: Triangle,
    ) -> float | None:
        """Check if a ray intersects with a triangle.

        Args:
            ray_origin (awpy.vector.Vector3): Ray origin point.
            ray_direction (awpy.vector.Vector3): Ray direction vector.
            triangle (Triangle): Triangle to check intersection with.

        Returns:
            float | None: Distance to the intersection point, or
                None if no intersection.
        """
        epsilon = 1e-6

        edge1 = triangle.p2 - triangle.p1
        edge2 = triangle.p3 - triangle.p1
        h = ray_direction.cross(edge2)
        a = edge1.dot(h)

        if -epsilon < a < epsilon:
            return None

        f = 1.0 / a
        s = ray_origin - triangle.p1
        u = f * s.dot(h)

        if u < 0.0 or u > 1.0:
            return None

        q = s.cross(edge1)
        v = f * ray_direction.dot(q)

        if v < 0.0 or u + v > 1.0:
            return None

        t = f * edge2.dot(q)

        if t > epsilon:
            return t

        return None

    def _traverse_bvh(
        self,
        node: BVHNode,
        ray_origin: awpy.vector.Vector3,
        ray_direction: awpy.vector.Vector3,
        max_distance: float,
    ) -> bool:
        """Traverse the BVH tree to check for ray-triangle intersections.

        Args:
            node (BVHNode): Current node in the BVH tree.
            ray_origin (awpy.vector.Vector3): Ray origin point.
            ray_direction (awpy.vector.Vector3): Ray direction vector.
            max_distance (float): Maximum distance to check for intersections.

        Returns:
            bool: True if an intersection is found, False otherwise.
        """
        if not node.aabb.intersects_ray(ray_origin, ray_direction):
            return False

        # Leaf node - check triangle intersection
        if node.triangle:
            t = self._ray_triangle_intersection(ray_origin, ray_direction, node.triangle)
            return bool(t is not None and t <= max_distance)

        # Internal node - recurse through children
        return self._traverse_bvh(node.left, ray_origin, ray_direction, max_distance) or self._traverse_bvh(
            node.right, ray_origin, ray_direction, max_distance
        )

    def is_visible(
        self,
        start: awpy.vector.Vector3 | tuple | list,
        end: awpy.vector.Vector3 | tuple | list,
    ) -> bool:
        """Check if a line segment is visible in the 3D space.

        Args:
            start (awpy.vector.Vector3 | tuple | list): Start point of the line segment.
            end (awpy.vector.Vector3 | tuple | list): End point of the line segment.

        Returns:
            bool: True if the line segment is visible, False otherwise.
        """
        start_vec = awpy.vector.Vector3.from_input(start)
        end_vec = awpy.vector.Vector3.from_input(end)

        # Calculate ray direction and length
        direction = end_vec - start_vec
        distance = direction.length()

        if distance < 1e-6:
            return True

        direction = direction.normalize()

        # Check for intersections
        return not self._traverse_bvh(self.root, start_vec, direction, distance)

    @staticmethod
    def read_tri_file(tri_file: str | pathlib.Path, buffer_size: int = 1000) -> list[Triangle]:
        """Read triangles from a .tri file."""
        tri_file = pathlib.Path(tri_file)

        triangles: list[Triangle] = []

        with open(tri_file, "rb") as f:
            chunk_size = buffer_size * 9 * 4

            while True:
                data = f.read(chunk_size)
                if not data:
                    break

                num_floats = len(data) // 4
                num_complete_triangles = num_floats // 9

                for i in range(num_complete_triangles):
                    offset = i * 36
                    values = struct.unpack("9f", data[offset : offset + 36])

                    triangles.append(
                        Triangle(
                            awpy.vector.Vector3(values[0], values[1], values[2]),
                            awpy.vector.Vector3(values[3], values[4], values[5]),
                            awpy.vector.Vector3(values[6], values[7], values[8]),
                        )
                    )

        return triangles
