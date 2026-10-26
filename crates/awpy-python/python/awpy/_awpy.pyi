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
# Points for the batch visibility queries: an ``(N, 3)`` array (NumPy or any
# other buffer of float32/float64 values) or a sequence of points.
Points = Sequence[Point] | Any

class InvalidDemoError(Exception):
    """Raised when a file is not a valid CS2 demo (bad magic bytes or a parse error)."""

class Events:
    """Read recorded CS2 game events as cached Polars DataFrames.

    Attributes:
        names: Sorted recorded event names.
        counts: Event names mapped to occurrence counts.

    Notes:
        Each frame contains ``tick`` and string-valued event fields. Participant fields such as
        ``attacker`` are user IDs. Dedicated datasets resolve Steam IDs. Multipart event frames also
        contain ``part``.

    Examples:
        >>> from awpy import Demo
        >>> events = Demo("match.dem").events
        >>> deaths = events["player_death"]
    """

    @property
    def names(self) -> list[str]:
        """List recorded CS2 game-event names.

        Returns:
            Sorted event names present in the demo.
        """

    @property
    def counts(self) -> dict[str, int]:
        """Count each recorded CS2 game-event name.

        Returns:
            Event names mapped to occurrence counts.
        """

    def __repr__(self) -> str:
        """Describe the loaded Awpy object.

        Returns:
            A short object description.
        """
        ...
    def __len__(self) -> int:
        """Count the loaded entries.

        Returns:
            The number of distinct recorded event names.
        """
        ...
    def __contains__(self, name: str) -> bool:
        """Check whether a CS2 event name was recorded.

        Args:
            name: Game-event name.

        Returns:
            True if the demo contains this event.
        """
        ...
    def __iter__(self) -> Iterator[str]:
        """Iterate over recorded CS2 event names.

        Returns:
            An iterator over sorted event names.
        """
        ...
    def __getitem__(self, name: str) -> pl.DataFrame:
        """Read one recorded CS2 game-event table.

        Args:
            name: Game-event name.

        Returns:
            A cached Polars DataFrame with tick and raw event fields.

        Raises:
            KeyError: If the demo has no event with that name.
        """

    def __getattr__(self, name: str) -> pl.DataFrame:
        """Read one recorded CS2 game-event table.

        Args:
            name: Game-event name.

        Returns:
            A cached Polars DataFrame with tick and raw event fields.

        Raises:
            AttributeError: If the demo has no event with that name.
        """

class Demo:
    """Read one CS2 demo or ordered recordings of one map.

    Args:
        path: One string or path-like object, or a nonempty sequence in recording order.

    Attributes:
        path: Source ``Path`` for a single recording. Access on a multipart demo raises
            ``ValueError``.
        paths: Source paths in recording order.
        parts: Each source recording as a ``Demo``.
        headers: Header and playback metadata for each source recording.

    Raises:
        FileNotFoundError: If a file does not exist.
        InvalidDemoError: If a file cannot be decoded as a supported CS2 demo.
        ValueError: If a multipart selection is empty, incompatible, incomplete, or split during
            live play.

    Notes:
        Single-file construction maps the file and checks its header. Multipart construction also
        validates round continuity and recording boundaries. Dataset properties decode on access and
        cache results. Multipart tables retain local ticks and include ``part``. ``players`` and
        ``stats`` combine Steam IDs.

    Examples:
        >>> from awpy import Demo
        >>> demo = Demo("match.dem")
        >>> demo.load("kills", "damages", "shots")
        >>> print(demo.stats)
    """

    path: Path
    def __init__(self, path: str | PathLike[str] | Sequence[str | PathLike[str]]) -> None:
        """Open CS2 demo paths in the supplied recording order.

        Args:
            path: One string or path-like object, or a nonempty sequence in recording order.
        """
        ...
    @property
    def paths(self) -> tuple[Path, ...]:
        """Read the source paths in recording order.

        Returns:
            Source Path objects in supplied order.
        """
    @property
    def parts(self) -> tuple[Demo, ...]:
        """Read each source recording as a Demo.

        Returns:
            Source Demo objects in supplied order.
        """
    @property
    def headers(self) -> tuple[dict[str, Any], ...]:
        """Read header and playback metadata for each recording.

        Returns:
            One header dictionary for each source recording.
        """
    def __repr__(self) -> str:
        """Describe the loaded Awpy object.

        Returns:
            A short object description.
        """
        ...
    @staticmethod
    def available_datasets() -> list[str]:
        """List cached dataset names accepted by Demo.load.

        Returns:
            Supported dataset names as strings.
        """

    def load(self, *datasets: str) -> None:
        """Decode and cache selected Awpy datasets.

        Args:
            *datasets: Dataset names from ``available_datasets()``.

        Raises:
            ValueError: If any name is unknown, before decoding starts.

        Notes:
            Compatible combat and projectile requests share passes. Stats reuse combat, round, and
            roster inputs. Already cached datasets are skipped.
        """

    @property
    def header(self) -> dict[str, Any]:
        """Read cached CS2 header and playback metadata.

        Returns:
            The header dictionary. Multipart playback fields are retained in ``headers``.

        Notes:
            Keys: ``map_name``, ``server_name``, ``client_name``, ``build_num``,
            ``demo_version_name``, ``game_directory``, and (when available)
            ``playback_ticks``, ``playback_frames``, ``playback_time``.
            Multipart playback fields are in ``headers`` instead.
        """

    @property
    def tick_rate(self) -> float:
        """Read the CS2 recording tick rate.

        Returns:
            Ticks per second from playback timing, or 64.0 when timing is unavailable.

        Notes:
            Returns ``64.0`` when playback timing is unavailable.
        """

    def tick_to_seconds(self, tick: int) -> float:
        """Convert a local demo tick to seconds from recording start.

        Args:
            tick: Local signed demo tick.

        Returns:
            Seconds, using the demo tick rate.
        """

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert recording seconds to the nearest local demo tick.

        Args:
            seconds: Finite seconds from recording start. Negative values are permitted.

        Returns:
            The nearest signed 32-bit tick.

        Raises:
            ValueError: If the value is nonfinite or outside the supported tick range.
        """

    @property
    def events(self) -> Events:
        """Read the cached CS2 game-event mapping.

        Returns:
            The cached Events mapping.

        Notes:
            Use ``demo.events.names`` to list names and ``demo.events[name]`` or
            attribute access to read a cached DataFrame::

                demo.events.player_death
                demo.events["player_ping"]
        """

    def ticks(
        self, props: list[str] | None = ..., players_only: bool = ..., *, part: int | None = ...
    ) -> pl.DataFrame:
        """Read selected networked CS2 properties at every recorded tick.

        Args:
            props: Raw field names or aliases. Defaults to ``X``, ``Y``, ``Z``, ``health``,
                ``armor``, and ``team_num``.
            players_only: Merge each player pawn and controller when true; read all entities when
                false.
            part: Zero-based source recording. Required for multipart explicit ticks or windows.

        Returns:
            A Polars DataFrame. Player rows include ``tick`` and ``steamid``. Entity rows include
            ``tick``, ``entity_id``, ``entity_serial``, and ``class_name``. Multipart queries also
            include ``part``.

        Notes:
            Aliases include ``X``, ``Y``, ``Z``, ``velocity_x``, ``velocity_y``, ``velocity_z``,
            ``velocity``, ``health``, ``armor``, ``team_num``, ``name``, and ``money``. Types are
            Int64, Float64, Boolean, or String; mixed integers and floats use Float64. Use entity ID
            and serial together. Pawn fields and names can decode in parallel; other controller
            fields and all-entity queries use serial decoding. Results are not cached.
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
        """Read CS2 player state at selected local ticks.

        Args:
            ticks: One local demo tick or a sequence of local ticks.
            every: Positive sampling stride in ticks. Do not combine with ``seconds``.
            seconds: Positive sampling interval in seconds. Do not combine with ``every``.
            events: One game-event name or a sequence of names whose ticks are selected.
            start_tick: Inclusive lower bound. Alone with ``end_tick``, select every tick in the
                window.
            end_tick: Inclusive upper bound for the selected ticks.
            part: Zero-based source recording. Required for multipart explicit ticks or windows.

        Returns:
            A Polars DataFrame with one row per active player and tick. See
            ``awpy.SNAPSHOT_PROPERTIES`` for fields. Multipart queries add ``part``.

        Raises:
            ValueError: If selectors conflict, no selector is supplied, or a multipart local query
                has no part.

        Notes:
            The window bounds the other selectors. One to four explicit ticks without other
            selectors use keyframe seeks. Other requests decode keyframe segments in parallel.
            Results are not cached.

        Examples:
            >>> from awpy import Demo
            >>> demo = Demo("match.dem")
            >>> sampled = demo.snapshots(seconds=1.0)
            >>> exact = demo.snapshots(ticks=[10000, 10100])
        """

    @property
    def players(self) -> pl.DataFrame:
        """Read the cached CS2 player roster.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            Columns: ``steamid``, ``name``, ``side``, and ``team_clan_name``.
            Bots have Steam ID 0. Side and team name are the last observed values.
            Team names come from ``CCSTeam`` and are null when not set.
        """

    @property
    def round_economy(self) -> pl.DataFrame:
        """Read cached CS2 team equipment values and buy types.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            One row per (round, side): ``round_num``, ``side``, ``equipment_value``
            (the team's total at freeze end), ``buy_type`` (``pistol`` / ``eco`` /
            ``force`` / ``full``), and ``n_players``.
        """

    @property
    def chat(self) -> pl.DataFrame:
        """Read cached CS2 chat messages.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            Decoded from ``SayText``, ``SayText2``, and ``SayTextChannel``. Columns:
            ``tick``, ``entity_index`` (the sender's controller slot), ``name``,
            ``message``, and ``channel`` (e.g. ``Cstrike_Chat_All`` for all-chat,
            ``Cstrike_Chat_T`` / ``Cstrike_Chat_CT`` for team chat). Server-side
            (GOTV) demos often strip chat entirely — an empty frame is normal.
        """

    @property
    def blinds(self) -> pl.DataFrame:
        """Read cached CS2 flash victims, throwers, and durations.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            Reconstructed from pawn flash state and ``flashbang_detonate`` (so it
            works even on GOTV demos, which omit the ``player_blind`` event).
            Columns: ``tick``, the resolved ``attacker_*`` (thrower) and
            ``victim_*`` (blinded player) ``steamid`` / ``name`` / ``side`` /
            ``x`` / ``y`` / ``z``, and ``duration`` (blind seconds).
        """

    @property
    def item_events(self) -> pl.DataFrame:
        """Read cached CS2 item purchases, pickups, and drops.

        Returns:
            A Polars DataFrame with transaction tick, action, player, item, position, original
            owner, cost, and buy-zone state.

        Notes:
            Transactions are reconstructed from inventory state, including demos without
            item_purchase events.
        """

    @property
    def convars(self) -> dict[str, str]:
        """Read cached CS2 server console variables.

        Returns:
            dict[str, str].

        Notes:
            Collected from the demo's ``net_SetConVar`` messages; when a convar is
            set more than once, the last value wins.
        """

    @property
    def rounds(self) -> pl.DataFrame:
        """Read cached CS2 round timings, winners, and end reasons.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            One row per round with ``round_num``, ``start_tick``,
            ``freeze_end_tick``, ``end_tick``, ``winner`` (team number),
            ``winner_side``, ``reason``, and ``reason_name``. Reconstructed from
            ``CCSGameRules`` state, so it works on demos without ``round_start`` /
            ``round_end`` events.
        """

    @property
    def kills(self) -> pl.DataFrame:
        """Read cached CS2 kills and resolved participants.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            ``is_trade`` marks a kill that avenges a teammate within 5.25 seconds.
            ``victim_traded`` marks the earlier death; stats count it as ``traded_deaths``.
            Each kill trades only the earliest qualifying death. A kill can have both flags.
        """

    @property
    def damages(self) -> pl.DataFrame:
        """Read cached CS2 player_hurt events and resolved participants.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.
        """

    @property
    def bomb(self) -> pl.DataFrame:
        """Read cached CS2 bomb actions.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.
        """

    @property
    def grenades(self) -> pl.DataFrame:
        """Read cached CS2 grenade positions at each tick.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.
        """

    @property
    def fires(self) -> pl.DataFrame:
        """Read cached CS2 fire intervals.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.
        """

    @property
    def smokes(self) -> pl.DataFrame:
        """Read cached CS2 smoke intervals.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.
        """

    @property
    def shots(self) -> pl.DataFrame:
        """Read cached CS2 shots with player and weapon state.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            Built in the same single pass as kills / damages / bomb / blinds.
        """

    @property
    def stats(self) -> pl.DataFrame:
        """Read cached CS2 match statistics for each player.

        Returns:
            The cached Polars DataFrame. See the dataset guide for all columns.

        Notes:
            Knife rounds are excluded. Includes kills, deaths, assists, headshots,
            openings, trades, multikills, KAST, ADR, clutches, and utility.
            ``clutch_1v1`` through ``clutch_1v5`` count wins by the opponent count
            when the clutch started. Their sum is ``clutches_won``.
            See the dataset and reference guides for columns and definitions.
        """

    def player_stats(self, include_knife_rounds: bool = ...) -> pl.DataFrame:
        """Read CS2 player statistics with optional knife rounds.

        Args:
            include_knife_rounds: Include rounds marked ``is_knife_round`` when true.

        Returns:
            A cached Polars scoreboard with one row per player.

        Notes:
            Both variants reuse decoded inputs. The default is the same cached result as ``stats``.
        """

class VisibilityChecker:
    """Check CS2 line of sight against static collision geometry.

    Args:
        source: CS2 map name or local ``.mesh`` path. A ``Path`` is always a file path.
        version: awpy-data ClientVersion for a map name. Omit to select the newest cached release;
            an empty cache selects the latest release.

    Attributes:
        path: The loaded mesh path, or ``None``.
        triangle_count: Number of collision triangles.

    Raises:
        FileNotFoundError: If the mesh file or map asset is missing.
        ValueError: If the mesh is invalid or a version is combined with a file path.

    Notes:
        Coordinates use Hammer units, with Z vertical. Missing map assets download through
        ``awpy.data``. Reuse the checker to retain its spatial index. Smokes, moving doors, and
        bullet penetration are not modeled.

    Examples:
        >>> from awpy import VisibilityChecker
        >>> checker = VisibilityChecker("de_inferno")
        >>> clear = checker.is_visible((-158.6, 819.1, 103.7), (1258.0, 455.5, 181.2))
    """

    path: Path | None
    triangle_count: int
    def __init__(self, source: str | Path, *, version: int | None = None) -> None:
        """Load a CS2 collision mesh and build its spatial index.

        Args:
            source: CS2 map name or local ``.mesh`` path. A ``Path`` is always a file path.
            version: awpy-data ClientVersion for a map name. Omit to select the newest cached
                release; an empty cache selects the latest release.
        """
        ...
    def __repr__(self) -> str:
        """Describe the loaded Awpy object.

        Returns:
            A short object description.
        """
        ...
    def is_visible(self, a: Point, b: Point) -> bool:
        """Check whether static geometry leaves a CS2 line segment clear.

        Args:
            a: Start ``(x, y, z)`` in Hammer units.
            b: End ``(x, y, z)`` in Hammer units.

        Returns:
            True if no collision triangle blocks the segment.
        """

    def is_occluded(self, a: Point, b: Point) -> bool:
        """Check whether static geometry blocks a CS2 line segment.

        Args:
            a: Start ``(x, y, z)`` in Hammer units.
            b: End ``(x, y, z)`` in Hammer units.

        Returns:
            True if a collision triangle blocks the segment. The complement of ``is_visible``.
        """

    def is_visible_many(
        self, a: Point | Points, b: Points, *, threads: int | None = None
    ) -> pl.Series:
        """Check whether static geometry leaves each of many CS2 line segments clear.

        Args:
            a: Start ``(x, y, z)`` shared by every segment, or an ``(N, 3)`` array of starts.
            b: Ends as an ``(N, 3)`` array, in Hammer units.
            threads: Most threads to use. Omit to use a shared pool with a thread per core
                (``RAYON_NUM_THREADS`` sets its size). Pass ``1`` inside a process pool that
                already uses every core.

        Returns:
            A Boolean ``polars.Series`` named ``visible``, one value per segment. Each value
            equals ``is_visible`` on the same pair.

        Raises:
            ValueError: If a shape is wrong, ``a`` holds neither 1 nor ``N`` points, or
                ``threads`` is below 1.
            TypeError: If the points are not float values.
            RuntimeError: If a pool of ``threads`` threads cannot be created.

        Notes:
            Points may be NumPy arrays or other buffers of ``float32`` or ``float64`` values, or
            sequences of ``(x, y, z)`` triples. ``float64`` rounds to ``float32`` as
            ``is_visible`` rounds Python floats. Inputs are copied, then the segments are checked
            in parallel with the GIL released.

        Examples:
            >>> from awpy import VisibilityChecker
            >>> checker = VisibilityChecker("de_inferno")
            >>> eye = (-158.6, 819.1, 103.7)
            >>> clear = checker.is_visible_many(eye, [(1258.0, 455.5, 181.2), (0.0, 0.0, 64.0)])
        """

    def is_occluded_many(
        self, a: Point | Points, b: Points, *, threads: int | None = None
    ) -> pl.Series:
        """Check whether static geometry blocks each of many CS2 line segments.

        Args:
            a: Start ``(x, y, z)`` shared by every segment, or an ``(N, 3)`` array of starts.
            b: Ends as an ``(N, 3)`` array, in Hammer units.
            threads: Most threads to use, as for ``is_visible_many``.

        Returns:
            A Boolean ``polars.Series`` named ``occluded``, one value per segment. The complement
            of ``is_visible_many``.

        Raises:
            ValueError: If a shape is wrong, ``a`` holds neither 1 nor ``N`` points, or
                ``threads`` is below 1.
            TypeError: If the points are not float values.
            RuntimeError: If a pool of ``threads`` threads cannot be created.
        """

class NavArea(TypedDict):
    """Describe one CS2 navigation polygon returned by NavMesh.area.

    Attributes:
        area_id: Navigation area ID.
        hull_index: Collision hull used to generate this area.
        dynamic_attribute_flags: Recorded engine attribute bitset.
        corners: World ``(x, y, z)`` polygon corners in Hammer units.
        connections: Distinct outgoing neighbor area IDs.
        ladders_above: Connected ladder IDs above the area.
        ladders_below: Connected ladder IDs below the area.
        centroid: Polygon center in Hammer units.
        size: Horizontal polygon area in square Hammer units.
    """

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
    """Read CS2 navigation areas and query directed paths.

    Args:
        source: CS2 map name or local ``.nav`` path. A ``Path`` is always a file path.
        version: awpy-data ClientVersion for a map name. Omit to select the newest cached release;
            an empty cache selects the latest release.

    Attributes:
        path: The loaded navigation file path, or ``None``.
        version: Navigation file format version.
        sub_version: Navigation file format subversion.
        is_analyzed: Whether the file contains analyzed bot-navigation data.
        area_count: Number of navigation areas.

    Raises:
        FileNotFoundError: If the file or map asset is missing.
        ValueError: If the navigation file is invalid or a version is combined with a file path.

    Notes:
        World coordinates use Hammer units, with Z vertical. Missing map assets download through
        ``awpy.data``. Keep the mesh for repeated queries. Navigation file versions differ from
        awpy-data release versions.

    Examples:
        >>> from awpy import NavMesh
        >>> nav = NavMesh("de_dust2")
        >>> route = nav.find_path((-680.0, 1500.0, 0.0), (1200.0, 2400.0, 0.0))
    """

    path: Path | None
    version: int
    sub_version: int
    is_analyzed: bool
    area_count: int
    def __init__(self, source: str | Path, *, version: int | None = None) -> None:
        """Load a CS2 navigation mesh.

        Args:
            source: CS2 map name or local ``.nav`` path. A ``Path`` is always a file path.
            version: awpy-data ClientVersion for a map name. Omit to select the newest cached
                release; an empty cache selects the latest release.
        """
        ...
    def __repr__(self) -> str:
        """Describe the loaded Awpy object.

        Returns:
            A short object description.
        """
        ...
    def __len__(self) -> int:
        """Count the loaded entries.

        Returns:
            The number of navigation areas.
        """
        ...
    @property
    def areas(self) -> pl.DataFrame:
        """Read CS2 navigation area summaries as a Polars table.

        Returns:
            A Polars DataFrame with area ID, hull, flags, corner count, centroid, size, and neighbor
            count.

        Notes:
            Use ``area(area_id)`` to read polygon corners and connected IDs.
        """

    def area(self, area_id: int) -> NavArea | None:
        """Read the complete geometry of one CS2 navigation area.

        Args:
            area_id: Navigation area ID.

        Returns:
            A ``NavArea`` dictionary, or ``None`` if the ID is absent.
        """

    def find_area(self, point: Point) -> int | None:
        """Find the CS2 navigation area containing a world point.

        Args:
            point: World ``(x, y, z)`` in Hammer units.

        Returns:
            The area ID, or ``None`` if no area covers the point. Overlapping floors use the area
            height nearest the point Z.
        """

    def neighbors(self, area_id: int) -> list[int]:
        """List outgoing neighbors of one CS2 navigation area.

        Args:
            area_id: Navigation area ID.

        Returns:
            Distinct directly reachable area IDs.
        """

    def find_path(
        self,
        start: int | Point,
        end: int | Point,
        *,
        weight: str = ...,
    ) -> list[int]:
        """Find a directed route through the CS2 navigation graph.

        Args:
            start: Start area ID or world ``(x, y, z)`` point.
            end: End area ID or world ``(x, y, z)`` point.
            weight: ``distance`` uses 3D centroid distances; ``hops`` uses area count; ``size`` uses
                adjacent area sizes.

        Returns:
            Area IDs from start through end. Empty if an endpoint has no area or no route exists.

        Raises:
            ValueError: If the weight is unknown.
        """

def compute_map_control(
    nav: NavMesh,
    players: Sequence[tuple[float, float, float, str, bool, bool, float | None]],
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
    fov: float = ...,
) -> dict[str, Any]:
    """Estimate CS2 map control from player observations.

    Args:
        nav: Loaded ``NavMesh``.
        players: Living-player tuples ``(x, y, z, side, crouched, blind, yaw)``. Coordinates use
            Hammer units. Yaw uses degrees and can be ``None``.
        visibility: Collision checker, required by ``raycast`` and ``vision``.
        method: ``raycast`` for all-direction sight, ``vision`` for horizontal field of view, or
            ``reachability`` for graph travel distance.
        smokes: Active ``(x, y, z, radius)`` smoke spheres for both sight models.
        fires: Active ``(x, y, z, radius)`` fire spheres for reachability.
        detail: Include per-area arrays. Default true.
        eye_height: Standing ray origin above the feet; default 64 Hammer units.
        crouch_eye_height: Crouched ray origin above the feet; default 46 Hammer units.
        target_height: Ray target above the area floor; default 46 Hammer units.
        max_distance: Maximum ray distance in Hammer units, or ``None`` for no limit.
        contest_margin: Travel-distance difference for contested areas; default 200 Hammer units.
        fov: Horizontal field of view in degrees; default 90. Values of 360 or more, or missing yaw,
            remove the limit.

    Returns:
        A dictionary with ``ct_fraction``, ``t_fraction``, ``contested_fraction``,
        ``neutral_fraction``, and ``net_control``. Detailed results also contain ``area_ids``,
        ``control``, ``ct``, and ``t`` lists.

    Raises:
        ValueError: If the method is unknown or a sight model has no collision checker.
    """
