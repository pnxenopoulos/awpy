"""Module for calculating visibility."""

from typing import Dict, List, Optional, Tuple

import numpy as np
from pxr import Usd, UsdGeom

from awpy.data import AWPY_DATA_DIR


class AxisAlignedBoundingBox:
    """Axis-Aligned Bounding Box class."""

    def __init__(self, min_point: np.ndarray, max_point: np.ndarray) -> None:
        """Initialize AxisAlignedBoundingBox with minimum and maximum points.

        Args:
            min_point (np.ndarray): Minimum point of the bounding box.
            max_point (np.ndarray): Maximum point of the bounding box.
        """
        self.min_point = np.array(min_point)
        self.max_point = np.array(max_point)

    def intersects_ray(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> bool:
        """Check if a ray intersects with the AxisAlignedBoundingBox.

        Args:
            ray_origin (np.ndarray): Origin of the ray.
            ray_direction (np.ndarray): Direction of the ray.

        Returns:
            bool: True if the ray intersects the
                AxisAlignedBoundingBox, False otherwise.
        """
        epsilon = 1e-6  # Small value to handle floating point precision

        t_min = np.zeros(3)
        t_max = np.zeros(3)

        for i in range(3):
            if abs(ray_direction[i]) < epsilon:
                if (
                    ray_origin[i] < self.min_point[i]
                    or ray_origin[i] > self.max_point[i]
                ):
                    return False
                t_min[i] = float("-inf")
                t_max[i] = float("inf")
            else:
                t1 = (self.min_point[i] - ray_origin[i]) / ray_direction[i]
                t2 = (self.max_point[i] - ray_origin[i]) / ray_direction[i]
                t_min[i] = min(t1, t2)
                t_max[i] = max(t1, t2)

        t_enter = np.max(t_min)
        t_exit = np.min(t_max)

        return t_enter <= t_exit and t_exit >= 0


class BoundingVolumeHierarchyNode:
    """Bounding Volume Hierarchy Node class."""

    def __init__(
        self,
        aabb: AxisAlignedBoundingBox,
        mesh: Optional[Dict] = None,
        left: Optional["BoundingVolumeHierarchyNode"] = None,
        right: Optional["BoundingVolumeHierarchyNode"] = None,
    ) -> None:
        """Initialize BVH node.

        Args:
            aabb (AxisAlignedBoundingBox): Axis-aligned bounding box for this node.
            mesh (Optional[Dict]): Mesh data if this is a leaf node.
            left (Optional[BoundingVolumeHierarchyNode]): Left child node.
            right (Optional[BoundingVolumeHierarchyNode]): Right child node.
        """
        self.aabb = aabb
        self.mesh = mesh
        self.left = left
        self.right = right


def _build_bvh(meshes: List[Dict]) -> BoundingVolumeHierarchyNode:
    """Build a Bounding Volume Hierarchy from a list of meshes.

    Args:
        meshes (List[Dict]): List of mesh dictionaries.

    Returns:
        BoundingVolumeHierarchyNode: Root node of the BVH.
    """
    if len(meshes) == 1:
        return BoundingVolumeHierarchyNode(meshes[0]["aabb"], mesh=meshes[0])

    centroids = np.array(
        [
            m["aabb"].min_point + (m["aabb"].max_point - m["aabb"].min_point) / 2
            for m in meshes
        ]
    )
    axis = np.argmax(np.max(centroids, axis=0) - np.min(centroids, axis=0))
    meshes.sort(key=lambda m: m["aabb"].min_point[axis])

    mid = len(meshes) // 2
    left = _build_bvh(meshes[:mid])
    right = _build_bvh(meshes[mid:])

    min_point = np.minimum(left.aabb.min_point, right.aabb.min_point)
    max_point = np.maximum(left.aabb.max_point, right.aabb.max_point)
    aabb = AxisAlignedBoundingBox(min_point, max_point)

    return BoundingVolumeHierarchyNode(aabb, left=left, right=right)


def _create_mesh_aabb(points: np.ndarray) -> AxisAlignedBoundingBox:
    """Create an AxisAlignedBoundingBox for a mesh given its points.

    Args:
        points (np.ndarray): Array of mesh vertices.

    Returns:
        AxisAlignedBoundingBox: Axis-aligned bounding box for the mesh.
    """
    min_point = np.min(points, axis=0)
    max_point = np.max(points, axis=0)
    return AxisAlignedBoundingBox(min_point, max_point)


def _line_mesh_intersection(
    start: np.ndarray,
    end: np.ndarray,
    points: np.ndarray,
    face_vertex_counts: np.ndarray,
    face_vertex_indices: np.ndarray,
) -> bool:
    """Check if a line segment intersects with a mesh.

    Args:
        start (np.ndarray): Start point of the line segment.
        end (np.ndarray): End point of the line segment.
        points (np.ndarray): Mesh vertices.
        face_vertex_counts (np.ndarray): Number of vertices for each face.
        face_vertex_indices (np.ndarray): Indices of vertices for each face.

    Returns:
        bool: True if there's an intersection, False otherwise.
    """
    start = np.array(start)
    end = np.array(end)
    direction = end - start
    direction /= np.linalg.norm(direction)

    vertex_index = 0
    for face_vertex_count in face_vertex_counts:
        face_indices = face_vertex_indices[
            vertex_index : vertex_index + face_vertex_count
        ]
        vertex_index += face_vertex_count

        for i in range(1, face_vertex_count - 1):
            triangle = [
                np.array(points[face_indices[0]]),
                np.array(points[face_indices[i]]),
                np.array(points[face_indices[i + 1]]),
            ]

            intersection = _ray_triangle_intersection(start, direction, triangle)
            if intersection is not None:
                t = np.dot(intersection - start, direction)
                if 0 <= t <= np.linalg.norm(end - start):
                    return True  # Return immediately if an intersection is found

    return False


def _ray_triangle_intersection(
    ray_origin: np.ndarray, ray_direction: np.ndarray, triangle: List[np.ndarray]
) -> Optional[np.ndarray]:
    """Find the intersection point between a ray and a triangle.

    Args:
        ray_origin (np.ndarray): Origin of the ray.
        ray_direction (np.ndarray): Direction of the ray.
        triangle (List[np.ndarray]): List of three vertices defining the triangle.

    Returns:
        Optional[np.ndarray]: Intersection point if it exists, None otherwise.
    """
    epsilon = 1e-6
    vertex0, vertex1, vertex2 = triangle
    edge1 = vertex1 - vertex0
    edge2 = vertex2 - vertex0
    h = np.cross(ray_direction, edge2)
    a = np.dot(edge1, h)

    if -epsilon < a < epsilon:
        return None

    f = 1.0 / a
    s = ray_origin - vertex0
    u = f * np.dot(s, h)

    if u < 0.0 or u > 1.0:
        return None

    q = np.cross(s, edge1)
    v = f * np.dot(ray_direction, q)

    if v < 0.0 or u + v > 1.0:
        return None

    t = f * np.dot(edge2, q)

    if t > epsilon:
        return ray_origin + t * ray_direction

    return None


def _traverse_bvh(
    node: BoundingVolumeHierarchyNode,
    ray_origin: np.ndarray,
    ray_direction: np.ndarray,
    point2: np.ndarray,
) -> bool:
    """Traverse the BVH to find if there's any intersection with a ray.

    Args:
        node (BoundingVolumeHierarchyNode): Current BVH node.
        ray_origin (np.ndarray): Origin of the ray.
        ray_direction (np.ndarray): Direction of the ray.
        point2 (np.ndarray): End point of the ray.

    Returns:
        bool: True if there's an intersection, False otherwise.
    """
    if not node.aabb.intersects_ray(ray_origin, ray_direction):
        return False

    if node.mesh:
        return _line_mesh_intersection(
            ray_origin,
            point2,
            node.mesh["points"],
            node.mesh["face_vertex_counts"],
            node.mesh["face_vertex_indices"],
        )

    return _traverse_bvh(node.left, ray_origin, ray_direction, point2) or _traverse_bvh(
        node.right, ray_origin, ray_direction, point2
    )


def is_visible(
    point1: Tuple[float, float, float],
    point2: Tuple[float, float, float],
    map_name: str,
) -> bool:
    """Check for intersections between a line segment and meshes in a USD file.

    Args:
        point1 (Tuple[float, float, float]): Start point of the line segment.
        point2 (Tuple[float, float, float]): End point of the line segment.
        map_name (str): Name of the map to check.

    Returns:
        bool: True if there's an intersection, False otherwise.

    Raises:
        FileNotFoundError: If the USD file for the map is not found
    """
    usd_path = AWPY_DATA_DIR / "usd" / f"{map_name}.usdc"
    if not usd_path.exists():
        missing_usd_msg = f"USD file {usd_path} not found. Try calling awpy get {map_name} to download the map."  # noqa: E501
        raise FileNotFoundError(missing_usd_msg)

    stage = Usd.Stage.Open(str(usd_path))

    meshes = []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get()
            face_vertex_counts = mesh.GetFaceVertexCountsAttr().Get()
            face_vertex_indices = mesh.GetFaceVertexIndicesAttr().Get()

            aabb = _create_mesh_aabb(points)
            meshes.append(
                {
                    "prim": prim,
                    "points": points,
                    "face_vertex_counts": face_vertex_counts,
                    "face_vertex_indices": face_vertex_indices,
                    "aabb": aabb,
                }
            )

    bvh = _build_bvh(meshes)

    point1 = np.array(point1)
    point2 = np.array(point2)
    direction = point2 - point1
    direction /= np.linalg.norm(direction)

    intersects = _traverse_bvh(bvh, point1, direction, point2)

    if intersects:
        return True

    return False
