"""Single-file and multipart demo queries with local tick coordinates."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from functools import cached_property
from math import isclose
from os import PathLike
from pathlib import Path
from typing import Any, cast, overload

import polars as pl

from awpy._awpy import Demo as NativeDemo
from awpy._awpy import Events as NativeEvents
from awpy._awpy import multipart_player_stats

PathInput = str | PathLike[str]


def _combine(frames: Sequence[tuple[int, pl.DataFrame]]) -> pl.DataFrame:
    """Keep source ticks and entity IDs in separate recording namespaces."""
    return pl.concat(
        [
            frame.with_columns(pl.lit(index, dtype=pl.UInt32).alias("part"))
            for index, frame in frames
        ],
        how="diagonal_relaxed",
    )


class _Dataset:
    """Expose native dataset documentation and the shared cache policy."""

    def __set_name__(self, owner: type[Demo], name: str) -> None:
        self.name = name
        self.__doc__ = getattr(NativeDemo, name).__doc__

    @overload
    def __get__(self, instance: None, owner: type[Demo]) -> _Dataset: ...

    @overload
    def __get__(self, instance: Demo, owner: type[Demo] | None = None) -> pl.DataFrame: ...

    def __get__(self, instance: Demo | None, owner: type[Demo] | None = None) -> Any:
        return self if instance is None else instance._dataset(self.name)


class Demo:
    """Open a CS2 demo, or ordered recordings of one map.

    Args:
        path: A string or path, or a nonempty sequence of strings and paths.

    Single-file queries keep their existing schemas and native caches.
    Multipart recordings must have the same map, build, and tick rate. Their
    completed rounds must be consecutive. Splits during live play are rejected.
    Multipart tables add a zero-based ``part`` column. Ticks and entity handles
    remain local to that part; use ``(part, tick)`` to identify a moment.
    ``players`` and ``stats`` combine Steam IDs and have no ``part`` column.
    """

    rounds = _Dataset()
    kills = _Dataset()
    damages = _Dataset()
    bomb = _Dataset()
    grenades = _Dataset()
    fires = _Dataset()
    smokes = _Dataset()
    shots = _Dataset()
    stats = _Dataset()
    players = _Dataset()
    round_economy = _Dataset()
    chat = _Dataset()
    blinds = _Dataset()
    item_events = _Dataset()

    def __init__(self, path: PathInput | Sequence[PathInput]) -> None:
        if isinstance(path, (str, PathLike)):
            paths = (Path(cast(PathInput, path)),)
        elif isinstance(path, Sequence) and not isinstance(path, (bytes, bytearray)):
            paths = tuple(Path(item) for item in path)
        else:
            raise TypeError("pass a path or a sequence of paths")
        if not paths:
            raise ValueError("pass at least one demo path")
        if len({p.resolve() for p in paths}) != len(paths):
            raise ValueError("demo paths must not repeat")
        self._paths = paths
        self._parts = tuple(NativeDemo(p) for p in paths)
        self._cache: dict[str, pl.DataFrame] = {}
        if len(paths) > 1:
            self._validate_parts()

    def __repr__(self) -> str:
        if len(self._parts) == 1:
            return repr(self._parts[0])
        return f"Demo(paths={self.paths!r})"

    @property
    def paths(self) -> tuple[Path, ...]:
        """Source paths in the supplied order."""
        return self._paths

    @property
    def path(self) -> Path:
        """The single source path. For multipart recordings, use ``paths``."""
        if len(self._parts) != 1:
            raise ValueError("multipart demos have multiple paths; use paths")
        return self.paths[0]

    @property
    def parts(self) -> tuple[Demo, ...]:
        """Each source recording as a Demo, indexed from zero."""
        return (self,) if len(self._parts) == 1 else self._source_parts

    @cached_property
    def _source_parts(self) -> tuple[Demo, ...]:
        return tuple(self._from_native(part) for part in self._parts)

    @classmethod
    def _from_native(cls, native: NativeDemo) -> Demo:
        part = cls.__new__(cls)
        part._paths = (native.path,)
        part._parts = (native,)
        part._cache = {}
        return part

    @cached_property
    def headers(self) -> tuple[dict, ...]:
        """Header and playback metadata for each source recording."""
        return tuple(part.header for part in self._parts)

    @property
    def header(self) -> dict:
        """Header metadata. Multipart playback fields are in ``headers``."""
        header = self.headers[0].copy()
        if len(self._parts) > 1:
            for name in ("playback_ticks", "playback_frames", "playback_time"):
                header.pop(name, None)
        return header

    @property
    def tick_rate(self) -> float:
        """Ticks per second, shared by all parts."""
        return self._parts[0].tick_rate

    def tick_to_seconds(self, tick: int) -> float:
        """Convert a local tick to seconds from its recording's start."""
        return self._parts[0].tick_to_seconds(tick)

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert local seconds to the nearest signed 32-bit demo tick."""
        return self._parts[0].seconds_to_tick(seconds)

    @staticmethod
    def available_datasets() -> list[str]:
        """Dataset names accepted by ``load``."""
        return NativeDemo.available_datasets()

    def load(self, *datasets: str) -> None:
        """Batch and cache compatible requests within each recording."""
        for name in datasets:
            if name not in self.available_datasets():
                raise ValueError(
                    f"unknown dataset {name!r}; valid datasets: {self.available_datasets()}"
                )
        native_datasets = tuple(
            name for name in datasets if len(self._parts) == 1 or name != "round_economy"
        )
        for part in self._parts:
            part.load(*native_datasets)
        if len(self._parts) > 1:
            for name in datasets:
                self._dataset(name)

    def _dataset(self, name: str) -> pl.DataFrame:
        if len(self._parts) == 1:
            return getattr(self._parts[0], name)
        if name not in self._cache:
            if name == "stats":
                return self.player_stats()
            if name == "players":
                players = pl.concat([part.players for part in self._parts])
                known = pl.col("steamid").is_not_null() & (pl.col("steamid") != 0)
                frame = pl.concat(
                    [
                        players.filter(known).unique("steamid", keep="last", maintain_order=True),
                        players.filter(~known).unique(
                            ["steamid", "name"], keep="last", maintain_order=True
                        ),
                    ]
                )
            elif name == "round_economy":
                pistols = self._pistol_rounds()
                frame = _combine(
                    [(i, part._round_economy(pistols)) for i, part in enumerate(self._parts)]
                )
            else:
                frame = _combine([(i, getattr(part, name)) for i, part in enumerate(self._parts)])
            self._cache[name] = frame
        return self._cache[name]

    def player_stats(self, include_knife_rounds: bool = False) -> pl.DataFrame:
        """Combine exact stat counts, then calculate ADR, KAST, and headshot rate.

        Parts retain separate trade, flash, and round state. Restart deaths in
        freeze time remain raw events but do not enter the statistics.
        Both knife-round variants reuse native parsed inputs and cached results.
        """
        if len(self._parts) == 1:
            return self._parts[0].player_stats(include_knife_rounds)
        name = "stats_with_knife_rounds" if include_knife_rounds else "stats"
        if name not in self._cache:
            self._cache[name] = multipart_player_stats(list(self._parts), include_knife_rounds)
        return self._cache[name]

    @cached_property
    def events(self) -> NativeEvents | Events:
        """Cached raw events by name. Multipart rows include ``part``."""
        return self._parts[0].events if len(self._parts) == 1 else Events(self._parts)

    @property
    def convars(self) -> dict[str, str]:
        """Console variables; later parts replace earlier values.

        Use ``parts[index].convars`` for a specific recording's values.
        """
        return {key: value for part in self._parts for key, value in part.convars.items()}

    def _selected(self, part: int | None) -> list[tuple[int, NativeDemo]]:
        if part is None:
            return list(enumerate(self._parts))
        if not isinstance(part, int):
            raise TypeError("part must be an integer")
        if not 0 <= part < len(self._parts):
            raise ValueError(f"part must be between 0 and {len(self._parts) - 1}")
        return [(part, self._parts[part])]

    def ticks(
        self, props: list[str] | None = None, players_only: bool = True, *, part: int | None = None
    ) -> pl.DataFrame:
        """Read networked properties at every tick, optionally from one part.

        Accepts the same aliases and raw field names as the native tick query.
        Multipart entity identity is ``(part, entity_id, entity_serial)``.
        """
        frames = [(i, demo.ticks(props, players_only)) for i, demo in self._selected(part)]
        return frames[0][1] if len(self._parts) == 1 else _combine(frames)

    def snapshots(
        self,
        *,
        ticks: int | Sequence[int] | None = None,
        every: int | None = None,
        seconds: float | None = None,
        events: str | Sequence[str] | None = None,
        start_tick: int | None = None,
        end_tick: int | None = None,
        part: int | None = None,
    ) -> pl.DataFrame:
        """Read recorded player state at selected local ticks.

        Select ``ticks``, a stride (``every`` or ``seconds``), event names, or a
        tick window. In multipart demos, explicit ticks and tick windows require
        ``part``. Stride and event queries can read all parts.
        """
        if (
            len(self._parts) > 1
            and part is None
            and any(value is not None for value in (ticks, start_tick, end_tick))
        ):
            raise ValueError("select part when querying local ticks in a multipart demo")
        frames = [
            (
                i,
                demo.snapshots(
                    ticks=ticks,
                    every=every,
                    seconds=seconds,
                    events=events,
                    start_tick=start_tick,
                    end_tick=end_tick,
                ),
            )
            for i, demo in self._selected(part)
        ]
        return frames[0][1] if len(self._parts) == 1 else _combine(frames)

    def _validate_parts(self) -> None:
        previous = None
        for index, part in enumerate(self._parts):
            for key in ("map_name", "build_num"):
                if self.headers[index].get(key) != self.headers[0].get(key):
                    raise ValueError(f"part {index} has a different {key}")
            if not isclose(part.tick_rate, self.tick_rate, rel_tol=1e-6):
                raise ValueError(f"part {index} has a different tick rate")
            if part._round_coverage() != (True, True):
                raise ValueError(f"part {index} has incomplete or unknown live-round boundaries")
            rounds = part.rounds.filter(~pl.col("is_knife_round"))
            if rounds["freeze_end_tick"].null_count():
                raise ValueError(f"part {index} has incomplete round-start evidence")
            numbers = rounds["round_num"].to_list()
            if not numbers:
                raise ValueError(f"part {index} has no completed match rounds")
            if numbers != list(range(numbers[0], numbers[-1] + 1)):
                raise ValueError(f"part {index} has overlapping or missing rounds")
            if previous is not None and numbers[0] != previous + 1:
                raise ValueError(f"part {index} has overlapping, unordered, or missing rounds")
            previous = numbers[-1]

    def _pistol_rounds(self) -> list[int]:
        """Find the first match round and first side switch across all parts."""
        pistols: list[int] = []
        previous: dict[int, str] = {}
        for part in self._parts:
            rounds = part.rounds.filter(~pl.col("is_knife_round"))
            sampled = part.snapshots(ticks=rounds["freeze_end_tick"].drop_nulls().to_list())
            for row in rounds.iter_rows(named=True):
                current = {
                    state["steamid"]: state["side"]
                    for state in sampled.filter(pl.col("tick") == row["freeze_end_tick"]).iter_rows(
                        named=True
                    )
                    if state["steamid"] and state["side"] in ("terrorist", "counter-terrorist")
                }
                if not pistols:
                    pistols.append(row["round_num"])
                common = current.keys() & previous.keys()
                if common and sum(current[key] != previous[key] for key in common) * 2 > len(
                    common
                ):
                    pistols.append(row["round_num"])
                    return pistols
                if current:
                    previous = current
        return pistols


class Events(Mapping[str, pl.DataFrame]):
    """Raw events from ordered recordings, with a zero-based ``part`` column."""

    def __init__(self, parts: tuple[NativeDemo, ...]) -> None:
        self._parts = parts
        self._frames: dict[str, pl.DataFrame] = {}

    @cached_property
    def counts(self) -> dict[str, int]:
        """Occurrence counts across all parts."""
        counts: Counter[str] = Counter()
        for part in self._parts:
            counts.update(part.events.counts)
        return dict(sorted(counts.items()))

    @property
    def names(self) -> list[str]:
        """Sorted event names across all parts."""
        return list(self.counts)

    def __getitem__(self, name: str) -> pl.DataFrame:
        if name not in self.counts:
            raise KeyError(f"no event {name!r} in this demo")
        if name not in self._frames:
            self._frames[name] = _combine(
                [
                    (i, part.events[name])
                    for i, part in enumerate(self._parts)
                    if name in part.events
                ]
            )
        return self._frames[name]

    def __getattr__(self, name: str) -> pl.DataFrame:
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(f"no event {name!r} in this demo; use names") from error

    def __contains__(self, name: object) -> bool:
        return name in self.counts

    def __iter__(self) -> Iterator[str]:
        return iter(self.names)

    def __len__(self) -> int:
        return len(self.counts)

    def __repr__(self) -> str:
        return f"Events({self.names!r})"
