"""Tests for the map-control primitive (offline; synthetic nav + mesh)."""

import struct
from pathlib import Path

import pytest
from awpy import NavMesh, VisibilityChecker
from awpy._awpy import compute_map_control

Square = list[tuple[float, float, float]]


def _square(x: float, y: float, z: float = 0.0) -> Square:
    """A unit square in the XY plane, lower-left corner at ``(x, y)``."""
    return [(x, y, z), (x + 1, y, z), (x + 1, y + 1, z), (x, y + 1, z)]


def _write_nav(path: Path, areas: list[tuple[int, Square, list[int]]]) -> None:
    """Write a minimal version-35 ``.nav`` (one 4-corner polygon per area)."""
    buf = bytearray()
    buf += struct.pack("<I", 0xFEEDFACE)
    buf += struct.pack("<III", 35, 1, 1)  # version, sub_version, analyzed
    buf += struct.pack("<I", len(areas) * 4)  # shared corner table
    for _, corners, _ in areas:
        for cx, cy, cz in corners:
            buf += struct.pack("<fff", cx, cy, cz)
    buf += struct.pack("<I", len(areas))  # polygon_count
    for i in range(len(areas)):
        buf += struct.pack("<B", 4)
        for k in range(4):
            buf += struct.pack("<I", i * 4 + k)
        buf += struct.pack("<I", 0)
    buf += struct.pack("<I", 0)  # v>=32
    buf += struct.pack("<I", 0)  # v>=35
    buf += struct.pack("<I", len(areas))  # area_count
    for i, (area_id, _, conns) in enumerate(areas):
        buf += struct.pack("<I", area_id)
        buf += struct.pack("<q", 0)
        buf += struct.pack("<B", 0)
        buf += struct.pack("<I", i)
        buf += struct.pack("<I", 0)
        buf += struct.pack("<I", len(conns))
        for c in conns:
            buf += struct.pack("<II", c, 0)
        for _ in range(3):
            buf += struct.pack("<I", 0)
        buf += b"\x00" * 5
        buf += struct.pack("<I", 0)
        buf += struct.pack("<I", 0)
    path.write_bytes(buf)


def _write_mesh(path: Path, verts: list[tuple], tris: list[tuple]) -> None:
    """Write an awpy ``.mesh`` (AWMH) from vertices and triangle indices."""
    buf = bytearray(b"AWMH")
    buf += struct.pack("<III", 1, len(verts), len(tris))
    for v in verts:
        buf += struct.pack("<fff", *v)
    for t in tris:
        buf += struct.pack("<III", *t)
    path.write_bytes(buf)


def _row_of(result: dict, area_id: int) -> str:
    idx = result["area_ids"].index(area_id)
    return result["control"][idx]


@pytest.fixture
def three_areas(tmp_path: Path) -> NavMesh:
    """Three unit squares in a row at x = 0, 100, 200 (unconnected)."""
    path = tmp_path / "row.nav"
    _write_nav(path, [(1, _square(0, 0), []), (2, _square(100, 0), []), (3, _square(200, 0), [])])
    return NavMesh(path)


@pytest.fixture
def empty_mesh(tmp_path: Path) -> VisibilityChecker:
    """A mesh with no geometry (nothing ever occludes)."""
    path = tmp_path / "empty.mesh"
    _write_mesh(path, [], [])
    return VisibilityChecker(path)


def test_raycast_open_map_is_all_contested(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    players = [
        (0.5, 0.5, 0.0, "ct", False, False, None),
        (200.5, 0.5, 0.0, "t", False, False, None),
    ]
    res = compute_map_control(three_areas, players, visibility=empty_mesh, method="raycast")
    assert _row_of(res, 1) == "contested"
    assert _row_of(res, 2) == "contested"
    assert _row_of(res, 3) == "contested"
    assert res["contested_fraction"] == pytest.approx(1.0)
    assert res["net_control"] == pytest.approx(0.0)


def test_raycast_wall_splits_control(tmp_path: Path) -> None:
    nav_path = tmp_path / "two.nav"
    _write_nav(nav_path, [(1, _square(0, 0), []), (2, _square(100, 0), [])])
    nav = NavMesh(nav_path)
    # A tall wall at x = 50 between the two areas.
    mesh_path = tmp_path / "wall.mesh"
    _write_mesh(
        mesh_path,
        [(50, -1000, -100), (50, 1000, -100), (50, 1000, 300), (50, -1000, 300)],
        [(0, 1, 2), (0, 2, 3)],
    )
    vc = VisibilityChecker(mesh_path)
    players = [
        (0.5, 0.5, 0.0, "ct", False, False, None),
        (100.5, 0.5, 0.0, "t", False, False, None),
    ]
    res = compute_map_control(nav, players, visibility=vc, method="raycast")
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 2) == "t"


def test_raycast_smoke_blocks_far_sightlines(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    players = [
        (0.5, 0.5, 0.0, "ct", False, False, None),
        (200.5, 0.5, 0.0, "t", False, False, None),
    ]
    smokes = [(100.5, 0.5, 40.0, 80.0)]  # over the middle area
    res = compute_map_control(
        three_areas, players, visibility=empty_mesh, method="raycast", smokes=smokes
    )
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 3) == "t"
    assert _row_of(res, 2) != "contested"  # the smoke cut both long sightlines


def test_raycast_blind_player_sees_nothing(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    players = [(0.5, 0.5, 0.0, "ct", False, True, None)]  # lone, blinded CT
    res = compute_map_control(three_areas, players, visibility=empty_mesh, method="raycast")
    assert res["neutral_fraction"] == pytest.approx(1.0)


def test_line_of_sight_requires_visibility(three_areas: NavMesh) -> None:
    with pytest.raises(ValueError, match="requires a VisibilityChecker"):
        compute_map_control(
            three_areas, [(0.5, 0.5, 0.0, "ct", False, False, None)], method="raycast"
        )


def test_summary_only_omits_area_detail(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    players = [(0.5, 0.5, 0.0, "ct", False, False, None)]
    res = compute_map_control(
        three_areas, players, visibility=empty_mesh, method="raycast", detail=False
    )
    assert "ct_fraction" in res
    assert "area_ids" not in res


@pytest.fixture
def chain(tmp_path: Path) -> NavMesh:
    """A connected 1-2-3-4-5 chain of unit squares."""
    path = tmp_path / "chain.nav"
    _write_nav(
        path,
        [
            (1, _square(0, 0), [2]),
            (2, _square(100, 0), [1, 3]),
            (3, _square(200, 0), [2, 4]),
            (4, _square(300, 0), [3, 5]),
            (5, _square(400, 0), [4]),
        ],
    )
    return NavMesh(path)


def test_reachability_awards_nearest_side(chain: NavMesh) -> None:
    players = [
        (0.5, 0.5, 0.0, "ct", False, False, None),
        (400.5, 0.5, 0.0, "t", False, False, None),
    ]
    res = compute_map_control(chain, players, method="reachability", contest_margin=1.0)
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 2) == "ct"
    assert _row_of(res, 3) == "contested"  # equidistant midpoint
    assert _row_of(res, 4) == "t"
    assert _row_of(res, 5) == "t"


def test_reachability_fire_denies_ground(chain: NavMesh) -> None:
    players = [
        (0.5, 0.5, 0.0, "ct", False, False, None),
        (400.5, 0.5, 0.0, "t", False, False, None),
    ]
    fires = [(200.5, 0.5, 0.0, 10.0)]  # on area 3, the only bridge
    res = compute_map_control(chain, players, method="reachability", fires=fires)
    assert _row_of(res, 3) == "neutral"  # burning: denied to both
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 5) == "t"


# --- vision: the field-of-view model --------------------------------------------


def test_vision_only_covers_the_arc_faced(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    """A player standing on the middle area sees ahead but not behind."""
    # Areas sit at x = 0, 100, 200; the CT is on the middle one facing +x.
    facing_pos_x = [(100.5, 0.5, 0.0, "ct", False, False, 0.0)]
    res = compute_map_control(three_areas, facing_pos_x, visibility=empty_mesh, method="vision")
    assert _row_of(res, 3) == "ct"  # ahead
    assert _row_of(res, 1) == "neutral"  # behind

    # Turn around and the held half flips.
    facing_neg_x = [(100.5, 0.5, 0.0, "ct", False, False, 180.0)]
    res = compute_map_control(three_areas, facing_neg_x, visibility=empty_mesh, method="vision")
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 3) == "neutral"


def test_vision_is_a_subset_of_raycast(three_areas: NavMesh, empty_mesh: VisibilityChecker) -> None:
    """The FOV cone can only remove areas, never add them."""
    players = [(100.5, 0.5, 0.0, "ct", False, False, 0.0)]
    raycast = compute_map_control(three_areas, players, visibility=empty_mesh, method="raycast")
    vision = compute_map_control(three_areas, players, visibility=empty_mesh, method="vision")
    assert vision["ct_fraction"] < raycast["ct_fraction"]
    assert raycast["ct_fraction"] == pytest.approx(1.0)


def test_vision_fov_360_matches_raycast(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    """A full-circle FOV is no constraint, so the two models must agree."""
    players = [(100.5, 0.5, 0.0, "ct", False, False, 0.0)]
    wide = compute_map_control(
        three_areas, players, visibility=empty_mesh, method="vision", fov=360.0
    )
    raycast = compute_map_control(three_areas, players, visibility=empty_mesh, method="raycast")
    assert wide["ct_fraction"] == pytest.approx(raycast["ct_fraction"])


def test_vision_without_a_yaw_is_unrestricted(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    """No known facing means no cone to test, not a dropped player."""
    players = [(100.5, 0.5, 0.0, "ct", False, False, None)]
    res = compute_map_control(three_areas, players, visibility=empty_mesh, method="vision")
    assert _row_of(res, 1) == "ct"
    assert _row_of(res, 3) == "ct"


def test_vision_narrow_fov_holds_less(three_areas: NavMesh, empty_mesh: VisibilityChecker) -> None:
    """`fov` monotonically widens what is held."""
    # Facing 45 degrees off the row, so a wide cone catches the far area and a
    # narrow one does not.
    players = [(100.5, 0.5, 0.0, "ct", False, False, 45.0)]
    fractions = [
        compute_map_control(three_areas, players, visibility=empty_mesh, method="vision", fov=fov)[
            "ct_fraction"
        ]
        for fov in (30.0, 120.0, 360.0)
    ]
    assert fractions == sorted(fractions), fractions
    assert fractions[0] < fractions[-1]


def test_unknown_method_lists_all_three(
    three_areas: NavMesh, empty_mesh: VisibilityChecker
) -> None:
    with pytest.raises(ValueError, match="raycast"):
        compute_map_control(
            three_areas,
            [(0.5, 0.5, 0.0, "ct", False, False, None)],
            visibility=empty_mesh,
            method="nonsense",
        )
