"""Module for calculating visibility."""

import numpy as np
from pxr import Usd, UsdGeom

from awpy.data import AWPY_DATA_DIR


def _load_usd(map_name: str) -> Usd.Stage:
    """Load the USD file.

    Args:
        map_name (str): The name of the map.

    Returns:
        Usd.Stage: The USD stage.
    """
    usd_path = AWPY_DATA_DIR / "usd" / f"{map_name}.usdc"
    return Usd.Stage.Open(usd_path)


# Function to calculate the line equation between two points
def _line_eq(point1: np.ndarray, point2: np.ndarray) -> tuple[float, float, float]:
    """Calculate the line equation between two points.

    Args:
        point1 (np.ndarray): The first point.
        point2 (np.ndarray): The second point.

    Returns:
        tuple(float, float, float): The line equation coefficients.
    """
    a = point1[1] - point2[1]
    b = point2[0] - point1[0]
    c = point1[0] * point2[1] - point2[0] * point1[1]
    return a, b, -c


def is_visible(point1: np.ndarray, point2: np.ndarray, map_name: str) -> bool:
    """Check if two points are visible to each other.

    Args:
        point1 (np.ndarray): The first point.
        point2 (np.ndarray): The second point.
        map_name (str): The name of the map.

    Returns:
        bool: True if the points are visible, False otherwise.
    """
    # Load the USD file
    stage = _load_usd(map_name)

    # Get the line equation coefficients
    a, b, c = _line_eq(point1, point2)

    # Iterate over all the meshes in the USD file
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            # Get the mesh vertices
            mesh = UsdGeom.Mesh(prim)
            points_attr = mesh.GetPointsAttr()
            vertices = points_attr.Get()
            # Check if the line intersects with the mesh
            for i in range(len(vertices) - 1):
                d = a * vertices[i][0] + b * vertices[i][1] + c
                if d == 0:
                    return False
            continue
    return True
