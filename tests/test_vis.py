"""Test the visibility module."""

import pytest
from click.testing import CliRunner

from awpy.cli import get
from awpy.data import AWPY_DATA_DIR
from awpy.vis import VisibilityChecker


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
        ct_spawn_pos = (15, 2168, -65)
        t_spawn_pos_1 = (-680, 834, 180)
        t_spawn_pos_2 = (-1349, 814, 180)
        mid_doors_ct = (-485.90, 1737.51, -60.28)
        mid_doors_t = (-489.97, 1532.02, -61.08)
        ct_spawn_towards_b = (-670.19, 2253.08, -56.78)
        long_a_near_site = (1320.44, 2012.22, 61.44)
        assert vc.is_visible(t_spawn_pos_1, t_spawn_pos_2)
        assert vc.is_visible(t_spawn_pos_2, t_spawn_pos_1)
        assert not vc.is_visible(t_spawn_pos_1, ct_spawn_pos)
        assert not vc.is_visible(ct_spawn_pos, t_spawn_pos_1)
        assert not vc.is_visible(mid_doors_ct, mid_doors_t)
        assert vc.is_visible(ct_spawn_towards_b, long_a_near_site)
