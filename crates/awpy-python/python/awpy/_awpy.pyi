"""Type stubs for the compiled ``awpy._awpy`` extension.

These exist for type checkers and editor tooltips, so each entry carries its types
plus a summary. The **authoritative** prose lives in the ``///`` docstrings in
``crates/awpy-python/src/lib.rs``: those are what ``help()`` returns and what the
published API reference is built from, since ``sphinx.ext.autodoc`` reads the
compiled objects rather than this file. Keep the two consistent, and put new detail
in the Rust docstrings rather than only here — anything added only here is invisible
on the website.
"""

from collections.abc import Iterator, Sequence
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
    """A parsed Counter-Strike 2 demo file.

    Construction is cheap: it opens and memory-maps the file and verifies its
    magic bytes, but does not decode it. Decoding happens lazily on the first
    access to a dataset or event, and every dataset is cached on the object
    afterwards (see the individual properties). Open a new ``Demo`` to re-read
    the file from scratch.

    Args:
        path: Path to the ``.dem`` file.

    Raises:
        FileNotFoundError: If the file does not exist.
        InvalidDemoError: If the file is not a valid CS2 demo.
    """

    path: Path
    def __init__(self, path: str | Path) -> None: ...
    def __repr__(self) -> str: ...
    @staticmethod
    def available_datasets() -> list[str]:
        """Dataset names accepted by load()."""

    def load(self, *datasets: str) -> None:
        """Materialize and cache one or more DataFrame datasets.

        Compatible event and projectile requests are unioned into one pass.
        Loading stats also prepares rounds, players, and requested combat
        datasets, including fully enriched bomb/shot rows, so mixed loads do
        not decode the same events twice. Ordinary property access still
        eagerly prepares its compatible group for efficient sequential use.

        Raises:
            ValueError: If a dataset name is unknown.
        """

    @property
    def header(self) -> dict[str, Any]:
        """The demo file header and playback info as a dict.

        Keys: ``map_name``, ``server_name``, ``client_name``, ``build_num``,
        ``demo_version_name``, ``game_directory``, and (when available)
        ``playback_ticks``, ``playback_frames``, ``playback_time``.
        """

    @property
    def tick_rate(self) -> float:
        """Ticks per second, for converting tick counts to seconds.

        Computed from the demo's playback timing (``playback_ticks`` divided by
        ``playback_time``), falling back to ``64.0`` when the demo does not
        report it. Competitive demos are 64 tick; some are recorded at 128::

            seconds = (row["end_tick"] - row["start_tick"]) / demo.tick_rate
        """

    @property
    def events(self) -> Events:
        """The demo's game events, keyed by name.

        Returns an :class:`Events` mapping: iterate it (or read ``.names``) to
        see which events the demo contains, and index or use attribute access
        to get one event as a DataFrame::

            demo.events.names          # ['bomb_planted', 'player_death', ...]
            demo.events.player_death   # -> DataFrame (parsed once, then cached)
            demo.events["player_ping"]

        The event stream is parsed on first access and cached, as is each
        event's DataFrame.
        """

    def ticks(self, props: list[str] | None = ..., players_only: bool = ...) -> pl.DataFrame:
        """Sample per-tick entity properties into a long-format DataFrame.

        With ``players_only=True`` (the default) there is **one row per player
        per tick**: each player's pawn and controller are merged into a single
        row identified by ``steamid``, and each requested property is read from
        whichever of the two entities carries it (so both pawn fields like
        ``m_iHealth`` and controller fields like ``m_iszPlayerName`` work).
        Columns: ``tick``, ``steamid``, then one column per requested property.
        Only the player pawn/controller entities are decoded.

        With ``players_only=False`` every entity is dumped raw — one row per
        (tick, entity) with columns ``tick``, ``entity_id``,
        ``entity_serial``, ``class_name``, then the requested properties. The
        id and serial together uniquely identify a slot occupant.

        Each property column is typed from its values: integer fields become
        Int64, floats Float64, bools Boolean, and strings Utf8 (a column mixing
        integers and floats widens to Float64).

        Property names accept friendly aliases — ``"X"``/``"Y"``/``"Z"`` for
        computed world position; ``"velocity_x"`` / ``"velocity_y"`` /
        ``"velocity_z"``, ``"velocity"`` (3D speed), and ``"health"``, ``"armor"``,
        ``"team_num"``,
        ``"name"``, ``"money"`` — as well as raw network names (``"m_iHealth"``).
        Omitting ``props`` uses a sensible default (position, health, armor,
        team).

        This decodes the demo in parallel across keyframe segments, so it is
        fast even over a full match. The result is **not** cached (each call
        re-decodes); keep the returned DataFrame if you need it again.

        Args:
            props: Property names to extract. Defaults to
                ``["X","Y","Z","health","armor","team_num"]``.
            players_only: When ``True`` (default), return one merged row per
                player; otherwise dump every entity separately.
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
    ) -> pl.DataFrame:
        """Per-player game state at chosen ticks, as a DataFrame.

        One row per active player per tick, with the full player + equipment
        schema (see :data:`awpy.SNAPSHOT_PROPERTIES`) — ready to feed
        :func:`awpy.plot.frame` via :class:`awpy.plot.Player`. Choose the ticks
        with any combination of:

        - ``ticks`` — a single tick or a list of ticks.
        - ``every`` / ``seconds`` — a periodic stride (mutually exclusive).
          ``every=64`` is one sample per 64 ticks; ``seconds=1.0`` converts via
          the tick rate.
        - ``events`` — the ticks on which these game events fired (a name or list).
        - ``start_tick`` / ``end_tick`` — restrict to this window. Given **on
          their own**, they yield every tick in the window (a contiguous range);
          combined with a sampler, they bound it.

        At least one of the above must be given. A single ``ticks`` value seeks
        directly to that tick (fast); everything else decodes in parallel across
        the demo's keyframes.

        Examples::

            demo.snapshots(ticks=29000)                    # one moment
            demo.snapshots(ticks=[29000, 30000])           # specific ticks
            demo.snapshots(start_tick=29000, end_tick=30000)  # a contiguous range
            demo.snapshots(every=64)                       # every 64 ticks
            demo.snapshots(seconds=1.0)                    # ~1 sample / second
            demo.snapshots(events="player_death")          # at kill ticks
            demo.snapshots(every=64, start_tick=0, end_tick=64000)
        """

    @property
    def players(self) -> pl.DataFrame:
        """The roster: every player seen in the demo (cached).

        One row per player with ``steamid``, ``name``, ``side`` (the last team
        observed — players swap at halftime), and ``team_clan_name``. Bots have
        ``steamid`` 0.

        ``team_clan_name`` is the organization the player's team was playing
        under (e.g. ``"Imperial"``), from the ``CCSTeam`` entities. Tournament
        servers set it; casual matchmaking leaves it null. It is captured
        alongside ``side``, so a player who leaves mid-match keeps the team they
        actually played for rather than whoever held their side afterwards.
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

        Decoded from ``SayText`` / ``SayText2`` user messages. Columns:
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
        """Every kill (``player_death`` event) as a DataFrame, all fields typed (cached).

        Includes two trade flags:

        - ``is_trade`` — this kill **is** a trade: the attacker killed someone
          who had just killed one of their teammates (within 5 seconds).
        - ``victim_traded`` — this kill's **victim was traded**: a teammate of
          the victim killed this attacker within the window.

        The two are duals, so the kill that avenges a death carries ``is_trade``
        and the death it avenged carries ``victim_traded``. The latter is what
        :attr:`stats` tallies as ``traded_deaths`` — both come from one
        classifier, so they cannot disagree::

            demo.kills.filter(pl.col("is_trade"))        # every trade kill
            demo.kills.filter(pl.col("victim_traded"))   # every traded death

        The two counts need not be equal: one kill can avenge several teammates
        at once (a player who kills two enemies and is then killed by a third
        trades both of those deaths), so ``victim_traded`` is typically the
        larger of the two.
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
        """Per-player match statistics (kills, KAST, ADR, openings, trades,
        clutches, ...; cached).

        One row per player, knife rounds excluded. See the docs for the full
        column list and the definitions of opening kills/deaths, traded deaths,
        clutches, KAST, and ADR.

        Clutch columns: ``clutches_played`` (rounds entered as the last player
        alive against at least one opponent), ``clutches_won``, and
        ``clutch_1v1`` … ``clutch_1v5`` (clutches *won*, bucketed by how many
        opponents were alive at the moment the player was left alone).

        This is the **cached** form: it is computed once (as part of the shared
        first-parse pass) and returned instantly thereafter. Use it unless you
        need to include knife rounds — for which call :meth:`player_stats`.
        """

    def player_stats(self, include_knife_rounds: bool = ...) -> pl.DataFrame:
        """Per-player stats, with control over knife rounds.

        The :attr:`stats` property excludes knife rounds (a side-decider round
        of all-melee kills) from every tally and denominator, matching
        competitive scoreboards. Pass ``include_knife_rounds=True`` here to
        count them instead. See :attr:`rounds` (``is_knife_round``) for which
        rounds these are.

        Unlike the cached :attr:`stats` property, this method **recomputes on
        every call** — it re-runs the kill/damage entity pass and the
        aggregation, and the result is not cached. On a large demo that is a
        few seconds each time. Prefer :attr:`stats` for the default
        (knife-rounds-excluded) result, and store the returned DataFrame if you
        call this repeatedly.
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
