"""Test the visibility module."""

import pytest
from click.testing import CliRunner

from awpy.cli import get
from awpy.data import AWPY_DATA_DIR
from awpy.vector import Vector3
from awpy.vis import Triangle, VisibilityChecker


def check_visibility_brute_force(
    start: Vector3 | tuple | list,
    end: Vector3 | tuple | list,
    triangles: list[Triangle],
) -> bool:
    """Check visibility by testing against all triangles directly."""
    start_vec = Vector3.from_input(start)
    end_vec = Vector3.from_input(end)

    # Calculate ray direction and length
    direction = end_vec - start_vec
    distance = direction.length()

    if distance < 1e-6:
        return True

    direction = direction.normalize()

    # Check intersection with each triangle
    for triangle in triangles:
        t = VisibilityChecker._ray_triangle_intersection(
            None, start_vec, direction, triangle
        )
        if t is not None and t <= distance:
            return False

    return True


class TestVisibility:
    """Tests the Awpy calculation functions."""

    @pytest.fixture(autouse=True)
    def setup_runner(self):
        """Setup CLI runner."""
        self.runner = CliRunner()
        self.runner.invoke(get, ["usd", "de_dust2"])

    def test_basic_visibility(self):
        """Tests basic visibility for de_dust2."""
        de_dust2_tri = AWPY_DATA_DIR / "tri" / "de_dust2.tri"
        tris = VisibilityChecker.read_tri_file(de_dust2_tri)
        vc = VisibilityChecker(triangles=tris)

        test_points = [
            # Structured as (point1, point2, expected_visibility)
            (
                (-680, 834, 180),  # t_spawn_pos_1
                (-1349, 814, 180),  # t_spawn_pos_2
                True,
            ),
            (
                (-680, 834, 180),  # t_spawn_pos_1
                (15, 2168, -65),  # ct_spawn_pos
                False,
            ),
            (
                (-485.90, 1737.51, -60.28),  # mid_doors_ct
                (-489.97, 1532.02, -61.08),  # mid_doors_t
                False,
            ),
            (
                (-670.19, 2253.08, -56.78),  # ct_spawn_towards_b
                (1320.44, 2012.22, 61.44),  # long_a_near_site
                True,
            ),
        ]

        # Test both BVH and brute force methods
        for start, end, expected in test_points:
            bvh_result = vc.is_visible(start, end)
            brute_force_result = check_visibility_brute_force(start, end, tris)

            # Test visibility in both directions
            bvh_result_reverse = vc.is_visible(end, start)
            brute_force_result_reverse = check_visibility_brute_force(end, start, tris)

            # Assert all results match the expected outcome
            assert (
                bvh_result == expected
            ), f"BVH visibility from {start} to {end} failed"
            assert (
                brute_force_result == expected
            ), f"Brute force visibility from {start} to {end} failed"
            assert (
                bvh_result == brute_force_result
            ), f"BVH and brute force results differ for {start} to {end}"

            # Assert reverse direction matches
            assert (
                bvh_result == bvh_result_reverse
            ), f"BVH visibility not symmetric for {start} and {end}"
            assert (
                brute_force_result == brute_force_result_reverse
            ), f"Brute force visibility not symmetric for {start} and {end}"
