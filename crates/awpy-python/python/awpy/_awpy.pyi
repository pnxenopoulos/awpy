"""Types and summaries for the compiled extension.

Keep these summaries consistent with ``crates/awpy-python/src/lib.rs``.
Rust docstrings supply ``help()`` for the public native classes.
"""

from collections.abc import Iterator, Sequence
from os import PathLike
from pathlib import Path
from typing import Any, TypedDict

import polars as pl

Point = tuple[float, float, float]

class InvalidDemoError(Exception):
    """Raised when a file is not a valid CS2 demo (bad magic bytes or a parse error)."""

class Events:
    """A demo's game events, keyed by name. Returned by :attr:`Demo.events`.

    Behaves like a read-only mapping from event name to DataFrame: iterating
    yields the (sorted) event names, ``in`` tests membership, and indexing or
    attribute access parses one event::

        demo.events.names            # every event name in the demo
        demo.events.counts           # {name: occurrences}
        demo.events.player_death     # -> DataFrame
        demo.events["player_ping"]   # -> DataFrame

    Each frame has a ``tick`` column plus one string column per event key
    (e.g. ``attacker``, ``weapon``, ``headshot`` for ``player_death``), is
    built on first access, and is cached.
    """

    @property
    def names(self) -> list[str]:
        """The event names present in the demo, sorted."""

    @property
    def counts(self) -> dict[str, int]:
        """Occurrence counts, as a ``{event_name: count}`` dict."""

    def __repr__(self) -> str: ...
    def __len__(self) -> int: ...
    def __contains__(self, name: str) -> bool: ...
    def __iter__(self) -> Iterator[str]: ...
    def __getitem__(self, name: str) -> pl.DataFrame:
        """One event's rows as a DataFrame (built once, then cached).

        Raises ``KeyError`` if the demo has no event with that name.
        """

    def __getattr__(self, name: str) -> pl.DataFrame:
        """Attribute access for one event (e.g. ``events.player_death``).

        Raises ``AttributeError`` if the demo has no event with that name.
        """

class Demo:
    """Open one CS2 demo or ordered recordings of one map.

    Single-file construction maps the file and checks its header. Multipart
    construction also checks round continuity and recording boundaries.
    Dataset access triggers decoding and caches the result.
    Multipart tables include ``part``; ticks and entity handles remain local.
    ``players`` and ``stats`` combine Steam IDs without a ``part`` column.

    Args:
        path: A string or path, or a nonempty sequence of strings and paths.

    Raises:
        FileNotFoundError: If the file does not exist.
        InvalidDemoError: If the file is not a valid CS2 demo.
    """

    path: Path
    def __init__(self, path: str | PathLike[str] | Sequence[str | PathLike[str]]) -> None: ...
    @property
    def paths(self) -> tuple[Path, ...]:
        """Source paths in the supplied order."""
    @property
    def parts(self) -> tuple[Demo, ...]:
        """Each source recording as a Demo, indexed from zero."""
    @property
    def headers(self) -> tuple[dict[str, Any], ...]:
        """Header and playback metadata for each source recording."""
    def __repr__(self) -> str: ...
    @staticmethod
    def available_datasets() -> list[str]:
        """Dataset names accepted by load()."""

    def load(self, *datasets: str) -> None:
        """Load and cache the named DataFrames.

        Compatible event requests share one pass, as do projectile requests.
        Stats reuse combat, round, and roster inputs. A combined stats request can
        also collect bomb and shot rows. Cached datasets are skipped.

        Raises:
            ValueError: If any dataset name is unknown, before loading begins.
        """

    @property
    def header(self) -> dict[str, Any]:
        """The demo file header and playback info as a dict.

        Keys: ``map_name``, ``server_name``, ``client_name``, ``build_num``,
        ``demo_version_name``, ``game_directory``, and (when available)
        ``playback_ticks``, ``playback_frames``, ``playback_time``.
        Multipart playback fields are in ``headers`` instead.
        """

    @property
    def tick_rate(self) -> float:
        """Ticks per second, from ``playback_ticks / playback_time``.

        Returns ``64.0`` when playback timing is unavailable.
        """

    def tick_to_seconds(self, tick: int) -> float:
        """Convert a demo tick to seconds from the start of the demo."""

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert seconds from the start of the demo to the nearest demo tick.

        Negative values are valid. The value must be finite and fit in a
        signed 32-bit tick.
        """

    @property
    def events(self) -> Events:
        """Cached game events, indexed by name.

        Use ``demo.events.names`` to list names and ``demo.events[name]`` or
        attribute access to read a cached DataFrame::

            demo.events.player_death
            demo.events["player_ping"]
        """

    def ticks(
        self, props: list[str] | None = ..., players_only: bool = ..., *, part: int | None = ...
    ) -> pl.DataFrame:
        """Read selected entity properties at every tick.

        With ``players_only=True``, merge each player pawn and controller into
        one row per tick. Columns are ``tick``, ``steamid``, and the requested
        properties. Only player pawns and controllers are decoded.

        With ``players_only=False``, return one row per entity per tick.
        Identity columns are ``tick``, ``entity_id``, ``entity_serial``, and
        ``class_name``. Use the id and serial together as the entity identity.

        Property types are inferred: Int64, Float64, Boolean, or Utf8.
        Mixed integer and float values use Float64.
        Names can be raw network fields or aliases: ``X``, ``Y``, ``Z``,
        ``velocity_x``, ``velocity_y``, ``velocity_z``, ``velocity`` (3D speed),
        ``health``, ``armor``, ``team_num``, ``name``, and ``money``.

        Player pawn fields and names can decode in parallel. Other controller-only
        fields and raw entity queries use serial decoding. Results are not cached.
        Set ``part`` to select a source recording in a multipart demo.

        Args:
            props: Property names. Defaults to
                ``["X", "Y", "Z", "health", "armor", "team_num"]``.
            players_only: Merge player entities if true; otherwise, return all entities.
        """

    def snapshots(
        self,
        *,
        ticks: int | Sequence[int] | None = ...,
        every: int | None = ...,
        seconds: float | None = ...,
        events: str | Sequence[str] | None = ...,
        start_tick: int | None = ...,
        end_tick: int | None = ...,
        part: int | None = ...,
    ) -> pl.DataFrame:
        """Read player state at selected ticks as a DataFrame.

        Return one row per active player per tick. See :data:`awpy.SNAPSHOT_PROPERTIES`
        for the schema. Select ticks with:

        - ``ticks``: one tick or a list.
        - ``every`` or ``seconds``: a stride in ticks or seconds. Do not set both.
        - ``events``: ticks with a named game event, or a list of event names.
        - ``start_tick`` and ``end_tick``: an inclusive window. Alone, this selects
          every tick in the window. With other selectors, it bounds the selection.

        Multipart local ticks and tick windows require ``part``.
        Stride and event queries can read all parts.
        At least one selector is required. One to four explicit ticks without
        other selectors use keyframe seeks. Other requests decode keyframe
        segments in parallel. Results are not cached.

        Examples::

            demo.snapshots(ticks=[29000, 30000])
            demo.snapshots(seconds=1, start_tick=0, end_tick=64000)
            demo.snapshots(events="player_death")
        """

    @property
    def players(self) -> pl.DataFrame:
        """Cached roster with one row per observed player.

        Columns: ``steamid``, ``name``, ``side``, and ``team_clan_name``.
        Bots have Steam ID 0. Side and team name are the last observed values.
        Team names come from ``CCSTeam`` and are null when not set.
        """

    @property
    def round_economy(self) -> pl.DataFrame:
        """Per-team economy and buy type per round (cached).

        One row per (round, side): ``round_num``, ``side``, ``equipment_value``
        (the team's total at freeze end), ``buy_type`` (``pistol`` / ``eco`` /
        ``force`` / ``full``), and ``n_players``.
        """

    @property
    def chat(self) -> pl.DataFrame:
        """Chat messages as a DataFrame (cached).

        Decoded from ``SayText``, ``SayText2``, and ``SayTextChannel``. Columns:
        ``tick``, ``entity_index`` (the sender's controller slot), ``name``,
        ``message``, and ``channel`` (e.g. ``Cstrike_Chat_All`` for all-chat,
        ``Cstrike_Chat_T`` / ``Cstrike_Chat_CT`` for team chat). Server-side
        (GOTV) demos often strip chat entirely — an empty frame is normal.
        """

    @property
    def blinds(self) -> pl.DataFrame:
        """Flash events as a DataFrame (cached): one row per player blinded.

        Reconstructed from pawn flash state and ``flashbang_detonate`` (so it
        works even on GOTV demos, which omit the ``player_blind`` event).
        Columns: ``tick``, the resolved ``attacker_*`` (thrower) and
        ``victim_*`` (blinded player) ``steamid`` / ``name`` / ``side`` /
        ``x`` / ``y`` / ``z``, and ``duration`` (blind seconds).
        """

    @property
    def item_events(self) -> pl.DataFrame:
        """Weapon-item transactions as a DataFrame (cached): purchases, pickups,
        and drops, reconstructed from inventory state (so they work on demos
        that omit the ``item_purchase`` event). Columns: ``tick``, ``action``
        (``purchase`` / ``pickup`` / ``drop``), ``steamid`` / ``name`` /
        ``side``, ``item``, ``x`` / ``y`` / ``z``, ``original_owner_steamid``,
        ``cost`` (purchases), and ``near_buy_zone`` (drops).
        """

    @property
    def convars(self) -> dict[str, str]:
        """Server console variables, as a ``{name: value}`` dict (cached).

        Collected from the demo's ``net_SetConVar`` messages; when a convar is
        set more than once, the last value wins.
        """

    @property
    def rounds(self) -> pl.DataFrame:
        """Per-round information as a DataFrame (cached).

        One row per round with ``round_num``, ``start_tick``,
        ``freeze_end_tick``, ``end_tick``, ``winner`` (team number),
        ``winner_side``, ``reason``, and ``reason_name``. Reconstructed from
        ``CCSGameRules`` state, so it works on demos without ``round_start`` /
        ``round_end`` events.
        """

    @property
    def kills(self) -> pl.DataFrame:
        """Cached ``player_death`` events with resolved participants.

        ``is_trade`` marks a kill that avenges a teammate within 5.25 seconds.
        ``victim_traded`` marks the earlier death; stats count it as ``traded_deaths``.
        Each kill trades only the earliest qualifying death. A kill can have both flags.
        """

    @property
    def damages(self) -> pl.DataFrame:
        """Every damage instance (``player_hurt`` event) as a DataFrame, all fields (cached)."""

    @property
    def bomb(self) -> pl.DataFrame:
        """Bomb actions (pickup / drop / plant / defuse) as a DataFrame (cached)."""

    @property
    def grenades(self) -> pl.DataFrame:
        """Thrown-grenade trajectories (one row per tick each grenade is live; cached)."""

    @property
    def fires(self) -> pl.DataFrame:
        """Burning infernos (one row per fire, with its ``[start_tick, end_tick]``; cached)."""

    @property
    def smokes(self) -> pl.DataFrame:
        """Smoke clouds (one row per smoke, with its ``[start_tick, end_tick]``; cached)."""

    @property
    def shots(self) -> pl.DataFrame:
        """Shots (``weapon_fire`` events) with shooter and weapon state (cached).

        Built in the same single pass as kills / damages / bomb / blinds.
        """

    @property
    def stats(self) -> pl.DataFrame:
        """Cached match statistics, with one row per player.

        Knife rounds are excluded. Includes kills, deaths, assists, headshots,
        openings, trades, multikills, KAST, ADR, clutches, and utility.
        ``clutch_1v1`` through ``clutch_1v5`` count wins by the opponent count
        when the clutch started. Their sum is ``clutches_won``.
        See the dataset and reference guides for columns and definitions.
        """

    def player_stats(self, include_knife_rounds: bool = ...) -> pl.DataFrame:
        """Read player statistics with optional knife rounds.

        Set ``include_knife_rounds=True`` to include rounds marked ``is_knife_round``.
        Both variants reuse decoded inputs and cache their DataFrames.
        The default returns the same cached object as :attr:`stats`.
        """

class VisibilityChecker:
    """Line-of-sight visibility over a map's collision geometry.

    Answers whether the straight segment between two world points is
    unobstructed, using the compact ``.mesh`` files published by ``awpy-data``.
    Construct it from either a map name or a mesh file:

    - ``VisibilityChecker("de_inferno")`` — newest release cached under
      ``~/.awpy`` (the latest release is downloaded if the cache is empty);
    - ``VisibilityChecker("de_inferno", version=2000873)`` — a pinned
      ``awpy-data`` release, downloaded on demand;
    - ``VisibilityChecker("path/to/de_inferno.mesh")`` — a specific file.
      Strings count as paths when they end in ``.mesh`` or contain a path
      separator; ``pathlib.Path`` objects always do.

    A bounding-volume hierarchy is built once at construction, so each query is
    fast; reuse a single checker for many queries.

    Coordinates are Hammer units, Z-up — the same frame as demo world positions
    (e.g. the ``*_x`` / ``*_y`` / ``*_z`` columns of :meth:`Demo.kills`), so you
    can pass entity positions in directly.

    Args:
        source: Map name (e.g. ``"de_inferno"``) or path to a ``.mesh`` file.
        version: ``awpy-data`` release to use when ``source`` is a map name —
            an integer ClientVersion (e.g. ``2000873``); defaults to the newest
            cached release.

    Raises:
        FileNotFoundError: If the file does not exist, or the release has no
            mesh for the map.
        ValueError: If the file is not a valid awpy mesh, or ``version`` is
            combined with a file path.

    Example:
        >>> from awpy import VisibilityChecker
        >>> vc = VisibilityChecker("de_inferno")
        >>> vc.is_visible((1258.04, 455.47, 181.22), (-158.62, 819.09, 103.73))
        True
    """

    path: Path | None
    triangle_count: int
    def __init__(self, source: str | Path, *, version: int | None = None) -> None: ...
    def __repr__(self) -> str: ...
    def is_visible(self, a: Point, b: Point) -> bool:
        """Is the straight segment from ``a`` to ``b`` clear of geometry?

        Args:
            a: Start point ``(x, y, z)`` in Hammer units.
            b: End point ``(x, y, z)`` in Hammer units.

        Returns:
            ``True`` if nothing blocks the line between the two points.
        """

    def is_occluded(self, a: Point, b: Point) -> bool:
        """Does any triangle block the segment from ``a`` to ``b``?

        The complement of :meth:`is_visible`.
        """

class NavArea(TypedDict):
    area_id: int
    hull_index: int
    dynamic_attribute_flags: int
    corners: list[Point]
    connections: list[int]
    ladders_above: list[int]
    ladders_below: list[int]
    centroid: Point
    size: float

class NavMesh:
    """A map's navigation mesh: walkable areas and the graph connecting them.

    CS2 tiles each map's walkable surface with convex polygonal *areas* joined
    by *connections*. This class parses the ``.nav`` files published by
    ``awpy-data`` and answers the two questions you'd ask of them: which area a
    world point sits in, and the shortest area-to-area path across the graph.
    Construct it from either a map name or a ``.nav`` file:

    - ``NavMesh("de_dust2")`` — newest release cached under ``~/.awpy`` (the
      latest release is downloaded if the cache is empty);
    - ``NavMesh("de_dust2", version=2000873)`` — a pinned ``awpy-data`` release;
    - ``NavMesh("path/to/de_dust2.nav")`` — a specific file. Strings count as
      paths when they end in ``.nav`` or contain a path separator;
      ``pathlib.Path`` objects always do.

    Coordinates are Hammer units, Z-up — the same frame as demo world positions,
    so entity positions can be passed straight into :meth:`find_area`. Areas are
    identified by numeric ``area_id``.

    Args:
        source: Map name (e.g. ``"de_dust2"``) or path to a ``.nav`` file.
        version: ``awpy-data`` release to use when ``source`` is a map name — an
            integer ClientVersion (e.g. ``2000873``); defaults to the newest
            cached release.

    Raises:
        FileNotFoundError: If the file does not exist, or the release has no nav
            for the map.
        ValueError: If the file is not a valid nav mesh, or ``version`` is
            combined with a file path.

    Example:
        >>> from awpy import NavMesh
        >>> nav = NavMesh("de_dust2")
        >>> area = nav.find_area((-1500.0, 900.0, 60.0))
        >>> nav.find_path(area, 42, weight="distance")  # doctest: +SKIP
        [..., 42]
    """

    path: Path | None
    version: int
    sub_version: int
    is_analyzed: bool
    area_count: int
    def __init__(self, source: str | Path, *, version: int | None = None) -> None: ...
    def __repr__(self) -> str: ...
    def __len__(self) -> int: ...
    @property
    def areas(self) -> pl.DataFrame:
        """Every area as a row: ``area_id``, ``hull_index``,
        ``dynamic_attribute_flags``, ``n_corners``, ``centroid_x/y/z``, ``size``
        (2D area), and ``n_connections`` (distinct neighbours).

        Full polygon geometry for one area is available via :meth:`area`.
        """

    def area(self, area_id: int) -> NavArea | None:
        """Full detail for one area, or ``None`` if no area has that ID.

        Returns a dict with ``area_id``, ``hull_index``,
        ``dynamic_attribute_flags``, ``corners`` (list of ``(x, y, z)``),
        ``connections`` (distinct neighbour IDs), ``ladders_above``,
        ``ladders_below``, ``centroid`` and ``size``.
        """

    def find_area(self, point: Point) -> int | None:
        """The area containing world point ``point`` (an ``(x, y, z)`` tuple), or
        ``None`` if the point is over no area.

        When areas overlap in the XY plane (stacked floors, a bridge over a
        tunnel), the area whose height is closest to the point's Z wins.
        """

    def neighbors(self, area_id: int) -> list[int]:
        """Distinct neighbour area IDs reachable directly from ``area_id``."""

    def find_path(
        self,
        start: int | Point,
        end: int | Point,
        *,
        weight: str = ...,
    ) -> list[int]:
        """Shortest path from ``start`` to ``end`` across the connection graph.

        ``start`` and ``end`` are each either an area ID (``int``) or a world
        point (``(x, y, z)`` tuple), which is resolved with :meth:`find_area`.
        Returns the list of area IDs from start to end inclusive, or an empty
        list if either endpoint maps to no area or no path connects them.

        Args:
            start: Start area ID or point.
            end: End area ID or point.
            weight: Edge cost — ``"distance"`` (default; 3D centroid distance),
                ``"hops"`` (fewest areas), or ``"size"`` (sum of adjacent area
                sizes; routes away from large open areas).
        """

def compute_map_control(
    nav: NavMesh,
    players: Sequence[tuple[float, float, float, str, bool, bool]],
    *,
    visibility: VisibilityChecker | None = ...,
    method: str = ...,
    smokes: Sequence[tuple[float, float, float, float]] = ...,
    fires: Sequence[tuple[float, float, float, float]] = ...,
    detail: bool = ...,
    eye_height: float = ...,
    crouch_eye_height: float = ...,
    target_height: float = ...,
    max_distance: float | None = ...,
    contest_margin: float = ...,
) -> dict[str, Any]:
    """Compute one snapshot's map control over a nav mesh (low-level primitive).

    Behind :func:`awpy.map_control.map_control`. Labels every nav area
    ``"ct"`` / ``"t"`` / ``"contested"`` / ``"neutral"`` and returns
    size-weighted summary fractions.

    Args:
        nav: The map's :class:`NavMesh`.
        players: ``(x, y, z, side, crouched, blind)`` for each living player.
        visibility: The map's :class:`VisibilityChecker`; required for
            ``method="vision"``.
        method: ``"vision"`` (line of sight, smoke-aware) or ``"reachability"``
            (who reaches each area first, fire-aware).
        smokes: Active smoke spheres ``(x, y, z, radius)`` (vision only).
        fires: Active inferno spheres ``(x, y, z, radius)`` (reachability only).
        detail: When ``True`` include per-area ``area_ids`` / ``control`` /
            ``ct`` / ``t`` lists; when ``False`` return only the summary.
        eye_height: Standing eye height above the feet (vision rays start here).
        crouch_eye_height: Eye height when crouched.
        target_height: Height above an area's floor that vision aims at.
        max_distance: Optional vision-range cap; ``None`` is unbounded.
        contest_margin: Reachability travel-distance tie band.

    Returns:
        A dict with ``ct_fraction``, ``t_fraction``, ``contested_fraction``,
        ``neutral_fraction``, ``net_control``, plus the per-area lists when
        ``detail`` is set.
    """
