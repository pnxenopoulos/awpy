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
        ct_spawn_pos = np.array([15, 2168, -65])
        t_spawn_pos_1 = np.array([-680, 834, 180])
        t_spawn_pos_2 = np.array([-1349, -814, 180])
        assert is_visible(t_spawn_pos_1, t_spawn_pos_2, "de_dust2")
        assert not is_visible(t_spawn_pos_1, ct_spawn_pos, "de_dust2")
