"""Test the visibility module."""

import numpy as np
import pytest
from click.testing import CliRunner

from awpy.cli import get
from awpy.vis import is_visible


class TestVisibility:
    """Tests the Awpy calculation functions."""

    @pytest.fixture(autouse=True)
    def setup_runner(self):  # noqa: PT004
        """Setup CLI runner."""
        self.runner = CliRunner()
        self.runner.invoke(get, ["usd", "de_dust2"])

    def test_basic_visibility(self):
        """Tests basic visibility for de_dust2."""
        ct_spawn_pos = (15, 2168, -65)
        t_spawn_pos_1 = (-680, 834, 180)
        t_spawn_pos_2 = (-1349, 814, 180)
        mid_doors_ct = (-485.90, 1737.51, -60.28)
        mid_doors_t = (-489.97, 1532.02, -61.08)
        ct_spawn_towards_b = (-670.19, 2253.08, -56.78)
        long_a_near_site = (1320.44, 2012.22, 61.44)
        assert is_visible(t_spawn_pos_1, t_spawn_pos_2, "de_dust2")
        assert not is_visible(t_spawn_pos_1, ct_spawn_pos, "de_dust2")
        assert not is_visible(mid_doors_ct, mid_doors_t, "de_dust2")
        assert is_visible(ct_spawn_towards_b, long_a_near_site, "de_dust2")
