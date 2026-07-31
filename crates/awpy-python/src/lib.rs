//! Python bindings for the Awpy Counter-Strike 2 demo parser.
//!
//! Exposes a [`Demo`] class that returns demo metadata as a dict and game
//! events / per-tick entity state as Polars `DataFrame`s.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};

use polars::prelude::*;
use pyo3::exceptions::{PyAttributeError, PyFileNotFoundError, PyKeyError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyIterator, PyList, PyString};
use pyo3_polars::PyDataFrame;

use awpy::datasets::{EventDatasets, Projectiles};
use awpy::geometry::VisibilityMesh;
use awpy::map_control::{
    Observer, Occluder, Params as McParams, Team, raycast_control, reachability_control,
    vision_control,
};
use awpy::nav::{Nav, PathWeight};
use awpy::{
    Blind, BombEvent, ChatMessage, Context, Damage, Entity, FieldValue, Fire, GameEvent, Grenade,
    ItemEvent, Kill, Parser, Player, PlayerState, PlayerStats, Round, RoundEconomy, Serializer,
    Shot, Smoke, cell_to_world,
};

pyo3::create_exception!(_awpy, InvalidDemoError, pyo3::exceptions::PyException);

/// Event name(s) for `Demo.snapshots(events=...)`: a single name or a list of
/// names. `One(String)` is tried first so a bare `str` is taken whole rather
/// than as a sequence of one-character strings.
#[derive(FromPyObject)]
enum EventNames {
    One(String),
    Many(Vec<String>),
}

impl EventNames {
    fn into_vec(self) -> Vec<String> {
        match self {
            EventNames::One(name) => vec![name],
            EventNames::Many(names) => names,
        }
    }
}

/// Tick(s) for `Demo.snapshots(ticks=...)`: a single tick or a list.
#[derive(FromPyObject)]
enum TicksArg {
    One(i32),
    Many(Vec<i32>),
}

impl TicksArg {
    fn into_vec(self) -> Vec<i32> {
        match self {
            TicksArg::One(t) => vec![t],
            TicksArg::Many(ts) => ts,
        }
    }
}

/// Player classes surfaced by [`Demo::ticks`] when `players_only=True`.
const PLAYER_CLASSES: &[&str] = &["CCSPlayerPawn", "CCSPlayerController"];

/// Build a `DataFrame` from columns, inferring the row count from the first
/// column (polars 0.53's `DataFrame::new` requires an explicit height).
fn df_from_columns(columns: Vec<Column>) -> PolarsResult<DataFrame> {
    let height = columns.first().map_or(0, |c| c.len());
    DataFrame::new(height, columns)
}

/// Fallible, thread-safe lazy initialization for Rust-side dataset groups.
///
/// `OnceLock::get_or_try_init` is not available on the crate's minimum Rust
/// version, so a small mutex supplies the same successful-value-only behavior:
/// failures are returned and a later call may retry.
struct LazyCache<T> {
    value: OnceLock<T>,
    init: Mutex<()>,
}

impl<T> Default for LazyCache<T> {
    fn default() -> Self {
        Self {
            value: OnceLock::new(),
            init: Mutex::new(()),
        }
    }
}

impl<T> LazyCache<T> {
    fn get_or_try_init<E>(&self, build: impl FnOnce() -> Result<T, E>) -> Result<&T, E> {
        if let Some(value) = self.value.get() {
            return Ok(value);
        }
        let _guard = self.init.lock().expect("dataset cache lock poisoned");
        if self.value.get().is_none() {
            self.value
                .set(build()?)
                .unwrap_or_else(|_| unreachable!("dataset cache initialized while locked"));
        }
        Ok(self.value.get().expect("dataset cache populated"))
    }
}

fn to_py_err(e: awpy::Error) -> PyErr {
    match e {
        awpy::Error::Io(io_err) => PyErr::from(io_err),
        other => InvalidDemoError::new_err(format!("{other}")),
    }
}

/// A parsed Counter-Strike 2 demo file.
///
/// Args:
///     path: Path to the ``.dem`` file.
///
/// Raises:
///     FileNotFoundError: If the file does not exist.
///     InvalidDemoError: If the file is not a valid CS2 demo.
#[pyclass]
struct Demo {
    parser: Parser,
    #[pyo3(get)]
    path: PathBuf,
    events_cache: OnceLock<Py<Events>>,
    frames_cache: Mutex<HashMap<&'static str, Py<PyAny>>>,
    convars_cache: LazyCache<Vec<(String, String)>>,
    event_datasets_cache: LazyCache<EventDatasets>,
    projectiles_cache: LazyCache<Projectiles>,
    rounds_cache: LazyCache<Vec<Round>>,
    players_cache: LazyCache<Vec<Player>>,
}

#[pymethods]
impl Demo {
    #[new]
    #[pyo3(text_signature = "(path)")]
    fn new(path: PathBuf) -> PyResult<Self> {
        if !path.exists() {
            return Err(PyFileNotFoundError::new_err(format!(
                "no such file: {}",
                path.display()
            )));
        }
        let parser = Parser::from_file(&path).map_err(to_py_err)?;
        parser.verify().map_err(to_py_err)?;
        Ok(Self {
            parser,
            path,
            events_cache: OnceLock::new(),
            frames_cache: Mutex::new(HashMap::new()),
            convars_cache: LazyCache::default(),
            event_datasets_cache: LazyCache::default(),
            projectiles_cache: LazyCache::default(),
            rounds_cache: LazyCache::default(),
            players_cache: LazyCache::default(),
        })
    }

    fn __repr__(&self) -> String {
        format!("Demo(path={:?})", self.path)
    }

    /// The demo file header and playback info as a dict.
    #[getter]
    fn header<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let header = self.parser.file_header().map_err(to_py_err)?;
        let dict = PyDict::new(py);
        dict.set_item("map_name", header.map_name)?;
        dict.set_item("server_name", header.server_name)?;
        dict.set_item("client_name", header.client_name)?;
        dict.set_item("build_num", header.build_num)?;
        dict.set_item("demo_version_name", header.demo_version_name)?;
        dict.set_item("game_directory", header.game_directory)?;

        if let Ok(info) = self.parser.file_info() {
            dict.set_item("playback_ticks", info.playback_ticks)?;
            dict.set_item("playback_frames", info.playback_frames)?;
            dict.set_item("playback_time", info.playback_time)?;
        }
        Ok(dict)
    }

    /// Ticks per second as a ``float``, for converting tick counts to seconds.
    ///
    /// Computed from the demo's playback timing (``playback_ticks`` divided by
    /// ``playback_time``), falling back to ``64.0`` when the demo does not report
    /// it. Competitive demos are 64 tick; some are recorded at 128::
    ///
    ///     seconds = (row["end_tick"] - row["freeze_end_tick"]) / demo.tick_rate
    #[getter]
    fn tick_rate(&self) -> f32 {
        self.parser.tickrate()
    }

    /// The demo's game events, keyed by name.
    ///
    /// Returns an :class:`Events` mapping: iterate it (or read ``.names``) to
    /// see which events the demo contains, and index or use attribute access
    /// to get one event as a DataFrame::
    ///
    ///     demo.events.names          # ['bomb_planted', 'player_death', ...]
    ///     demo.events.player_death   # -> DataFrame (parsed once, then cached)
    ///     demo.events["player_ping"]
    ///
    /// The event stream is parsed on first access and cached, as is each
    /// event's DataFrame.
    #[getter]
    fn events(&self, py: Python<'_>) -> PyResult<Py<Events>> {
        if let Some(cached) = self.events_cache.get() {
            return Ok(cached.clone_ref(py));
        }
        let events = py
            .detach(|| self.parser.events_shared())
            .map_err(to_py_err)?;
        let mut groups: BTreeMap<String, Vec<usize>> = BTreeMap::new();
        for (index, event) in events.iter().enumerate() {
            if let Some(group) = groups.get_mut(&event.name) {
                group.push(index);
            } else {
                groups.insert(event.name.clone(), vec![index]);
            }
        }
        let obj = Py::new(
            py,
            Events {
                events,
                groups,
                frames: Mutex::new(HashMap::new()),
            },
        )?;
        let _ = self.events_cache.set(obj.clone_ref(py));
        Ok(self
            .events_cache
            .get()
            .expect("events object cache populated")
            .clone_ref(py))
    }

    /// Sample per-tick entity properties into a long-format DataFrame.
    ///
    /// With ``players_only=True`` (the default) there is **one row per player
    /// per tick**: each player's pawn and controller are merged into a single
    /// row identified by ``steamid``, and each requested property is read from
    /// whichever of the two entities carries it (so both pawn fields like
    /// ``m_iHealth`` and controller fields like ``m_iszPlayerName`` work).
    /// Columns: ``tick``, ``steamid``, then one column per requested property.
    /// Only the player pawn/controller entities are decoded.
    ///
    /// With ``players_only=False`` every entity is dumped raw — one row per
    /// (tick, entity) with columns ``tick``, ``entity_id``, ``class_name``, then
    /// the requested properties.
    ///
    /// Each property column is typed from its values: integer fields become
    /// Int64, floats Float64, bools Boolean, and strings Utf8 (a column mixing
    /// integers and floats widens to Float64).
    ///
    /// Property names accept friendly aliases — ``"X"``/``"Y"``/``"Z"`` for
    /// computed world position, and ``"health"``, ``"armor"``, ``"team_num"``,
    /// ``"name"``, ``"money"`` — as well as raw network names (``"m_iHealth"``).
    /// Omitting ``props`` uses a sensible default (position, health, armor,
    /// team).
    ///
    /// Args:
    ///     props: Property names to extract. Defaults to
    ///         ``["X","Y","Z","health","armor","team_num"]``.
    ///     players_only: When ``True`` (default), return one merged row per
    ///         player; otherwise dump every entity separately.
    #[pyo3(signature = (props=None, players_only=true))]
    #[pyo3(text_signature = "($self, props=None, players_only=True)")]
    fn ticks(
        &self,
        py: Python<'_>,
        props: Option<Vec<String>>,
        players_only: bool,
    ) -> PyResult<PyDataFrame> {
        py.detach(move || {
            let props = props.unwrap_or_else(default_tick_props);
            if players_only {
                return self.ticks_by_player(props);
            }
            let mut ticks: Vec<i64> = Vec::new();
            let mut entity_ids: Vec<i64> = Vec::new();
            let mut classes: Vec<String> = Vec::new();
            let mut prop_cols: Vec<TickColumn> =
                (0..props.len()).map(|_| TickColumn::new()).collect();

            // Cache resolved (class, prop) → field key so we don't re-walk the
            // serializer hierarchy on every tick.
            let mut key_cache: HashMap<String, Vec<Option<u64>>> = HashMap::new();

            // `players_only=False`: dump every entity separately (the merged
            // one-row-per-player path returned earlier).
            self.parser
                .run_to_end(|ctx| {
                    for (_, entity) in ctx.entities.iter() {
                        if !entity.active {
                            continue;
                        }
                        let Some(serializer) = ctx.serializers.get(&entity.class_name) else {
                            continue;
                        };
                        let keys = key_cache
                            .entry(entity.class_name.clone())
                            .or_insert_with(|| resolve_keys(serializer, &props));

                        ticks.push(ctx.tick as i64);
                        entity_ids.push(entity.index as i64);
                        classes.push(entity.class_name.clone());
                        for (i, key) in keys.iter().enumerate() {
                            prop_cols[i].push(read_field(entity, *key));
                        }
                    }
                })
                .map_err(to_py_err)?;

            let mut columns: Vec<Column> = vec![
                Column::new("tick".into(), ticks),
                Column::new("entity_id".into(), entity_ids),
                Column::new("class_name".into(), classes),
            ];
            for (prop, col) in props.iter().zip(prop_cols) {
                columns.push(col.into_column(prop.as_str()));
            }
            let df = df_from_columns(columns).map_err(polars_err)?;
            Ok(PyDataFrame(df))
        })
    }

    /// Per-round information as a DataFrame (cached).
    ///
    /// One row per round with ``round_num``, ``start_tick``, ``freeze_end_tick``,
    /// ``end_tick``, ``winner`` (team number), ``winner_side``, ``reason``, and
    /// ``reason_name``. Reconstructed from ``CCSGameRules`` state, so it works on
    /// demos without ``round_start`` / ``round_end`` events.
    #[getter]
    fn rounds(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let rounds = self.parsed_rounds(py)?;
        self.cached_frame(py, "rounds", move || {
            rounds_to_frame(rounds).map_err(polars_err)
        })
    }

    /// Every kill (``player_death`` event) as a DataFrame, all fields typed (cached).
    ///
    /// Includes two trade flags:
    ///
    /// * ``is_trade`` — this kill **is** a trade: the attacker killed someone who
    ///   had just killed one of their teammates (within 5 seconds).
    /// * ``victim_traded`` — this kill's **victim was traded**: a teammate of the
    ///   victim killed this attacker within the window.
    ///
    /// The two are duals, so the kill that avenges a death carries ``is_trade``
    /// and the death it avenged carries ``victim_traded``; the latter is what
    /// :attr:`stats` tallies as ``traded_deaths``, from the same classifier, so
    /// they cannot disagree. Their totals differ, though: one kill can avenge
    /// several teammates at once, so ``victim_traded`` is usually more common.
    #[getter]
    fn kills(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.event_frame(py, "kills")
    }

    /// Every damage instance (``player_hurt`` event) as a DataFrame, all fields (cached).
    #[getter]
    fn damages(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.event_frame(py, "damages")
    }

    /// Bomb actions (pickup / drop / plant / defuse) as a DataFrame (cached).
    #[getter]
    fn bomb(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.event_frame(py, "bomb")
    }

    /// Thrown-grenade trajectories (one row per tick each grenade is live; cached).
    #[getter]
    fn grenades(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.projectile_frame(py, "grenades")
    }

    /// Burning infernos (one row per fire, with its `[start_tick, end_tick]`; cached).
    #[getter]
    fn fires(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.projectile_frame(py, "fires")
    }

    /// Deployed smoke clouds (one row per smoke, with its `[start_tick, end_tick]`; cached).
    #[getter]
    fn smokes(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.projectile_frame(py, "smokes")
    }

    /// Shots (``weapon_fire`` events) with shooter and weapon state (cached).
    ///
    /// Built in the same single pass as kills / damages / bomb / blinds.
    #[getter]
    fn shots(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.event_frame(py, "shots")
    }

    /// Per-player match statistics as a DataFrame (cached).
    ///
    /// One row per player, knife rounds excluded. Columns: ``steamid``, ``name``,
    /// ``rounds_played``, ``kills``, ``deaths``, ``assists``, ``flash_assists``,
    /// ``headshot_kills``, ``headshot_pct``, ``opening_kills``,
    /// ``opening_deaths``, ``traded_deaths``, ``multikill_2k`` …
    /// ``multikill_5k``, ``kast``, ``adr``, the clutch columns below, and utility
    /// (``utility_damage``, ``flashes_thrown``, ``enemies_flashed``,
    /// ``flash_duration_dealt``).
    ///
    /// Clutches: ``clutches_played`` (rounds entered as the last player alive
    /// against at least one opponent), ``clutches_won``, and ``clutch_1v1`` …
    /// ``clutch_1v5`` — clutches *won*, bucketed by how many opponents were alive
    /// at the moment the player was left alone, so the five sum to
    /// ``clutches_won``.
    ///
    /// See the reference docs for how opening kills/deaths, traded deaths,
    /// clutches, KAST, and ADR are defined.
    #[getter]
    fn stats(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let event_datasets = self.event_datasets(py)?;
        let rounds = self.parsed_rounds(py)?;
        self.cached_frame(py, "stats", move || {
            let stats = self.parser.player_stats_from(event_datasets, rounds, true);
            stats_to_frame(&stats).map_err(polars_err)
        })
    }

    /// Per-player stats, with control over knife rounds.
    ///
    /// The :attr:`stats` property excludes knife rounds (a side-decider round of
    /// all-melee kills) from every tally and denominator, matching competitive
    /// scoreboards. Pass ``include_knife_rounds=True`` here to count them
    /// instead. See :attr:`rounds` (``is_knife_round``) for which rounds these
    /// are.
    ///
    /// Unlike the cached :attr:`stats` property, this method **recomputes on
    /// every call** — it re-runs the kill/damage entity pass and the
    /// aggregation, and the result is not cached (a few seconds each on a large
    /// demo). Prefer :attr:`stats` for the default (knife-rounds-excluded)
    /// result, and keep the returned DataFrame if you call this repeatedly.
    #[pyo3(signature = (include_knife_rounds=false))]
    #[pyo3(text_signature = "($self, include_knife_rounds=False)")]
    fn player_stats(&self, py: Python<'_>, include_knife_rounds: bool) -> PyResult<PyDataFrame> {
        py.detach(|| {
            let stats = self
                .parser
                .player_stats(!include_knife_rounds)
                .map_err(to_py_err)?;
            Ok(PyDataFrame(stats_to_frame(&stats).map_err(polars_err)?))
        })
    }

    /// The roster: every player seen in the demo (cached).
    ///
    /// One row per player with ``steamid``, ``name``, ``side`` (the last team
    /// observed — players swap at halftime), and ``team_clan_name``. Bots have
    /// ``steamid`` 0.
    ///
    /// ``team_clan_name`` is the organization the player's team was playing under
    /// (e.g. ``"Imperial"``), from the ``CCSTeam`` entities. Tournament servers
    /// set it; casual matchmaking leaves it null. It is captured alongside
    /// ``side``, so a player who leaves mid-match keeps the team they actually
    /// played for rather than whoever held their side afterwards.
    #[getter]
    fn players(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let players = self.parsed_players(py)?;
        self.cached_frame(py, "players", move || {
            players_to_frame(players).map_err(polars_err)
        })
    }

    /// Per-team economy and buy type per round (cached).
    ///
    /// One row per (round, side): ``round_num``, ``side``, ``equipment_value``
    /// (team total at round start), ``buy_type`` (``pistol`` / ``eco`` /
    /// ``force`` / ``full``), and ``n_players``.
    #[getter]
    fn round_economy(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.cached_frame(py, "round_economy", || {
            let econ = self.parser.round_economy().map_err(to_py_err)?;
            round_economy_to_frame(&econ).map_err(polars_err)
        })
    }

    /// Chat messages as a DataFrame (cached).
    ///
    /// Decoded from ``SayText`` / ``SayText2`` user messages. Columns:
    /// ``tick``, ``entity_index`` (the sender's controller slot), ``name``,
    /// ``message``, and ``channel`` (e.g. ``Cstrike_Chat_All`` for all-chat,
    /// ``Cstrike_Chat_T`` / ``Cstrike_Chat_CT`` for team chat).
    #[getter]
    fn chat(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.cached_frame(py, "chat", || {
            let chat = self.parser.chat().map_err(to_py_err)?;
            chat_to_frame(&chat).map_err(polars_err)
        })
    }

    /// Flash events as a DataFrame (cached): one row per player blinded.
    ///
    /// Reconstructed from pawn flash state and ``flashbang_detonate`` (so it
    /// works even on GOTV demos, which omit the ``player_blind`` event).
    /// Columns: ``tick``, the resolved ``attacker_*`` (thrower) and
    /// ``victim_*`` (blinded player) ``steamid`` / ``name`` / ``side`` /
    /// ``x`` / ``y`` / ``z``, and ``duration`` (blind seconds).
    #[getter]
    fn blinds(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.event_frame(py, "blinds")
    }

    /// Weapon-item transactions as a DataFrame (cached): purchases, pickups,
    /// and drops, reconstructed from inventory state (so they work on demos
    /// that omit the ``item_purchase`` event). Columns: ``tick``, ``action``
    /// (``purchase`` / ``pickup`` / ``drop``), ``steamid`` / ``name`` /
    /// ``side``, ``item``, ``x`` / ``y`` / ``z``, ``original_owner_steamid``,
    /// ``cost`` (purchases), and ``near_buy_zone`` (drops).
    #[getter]
    fn item_events(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.cached_frame(py, "item_events", || {
            let items = self.parser.item_events().map_err(to_py_err)?;
            item_events_to_frame(&items).map_err(polars_err)
        })
    }

    /// Server console variables, as a ``{name: value}`` dict (cached).
    ///
    /// Collected from the demo's ``net_SetConVar`` messages; when a convar is
    /// set more than once, the last value wins.
    #[getter]
    fn convars<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let convars = py
            .detach(|| self.convars_cache.get_or_try_init(|| self.parser.convars()))
            .map_err(to_py_err)?;
        let dict = PyDict::new(py);
        for (name, value) in convars {
            dict.set_item(name, value)?;
        }
        Ok(dict)
    }

    /// Per-player game state at chosen ticks, as a DataFrame.
    ///
    /// One row per active player per tick, with the full player + equipment
    /// schema (see :data:`awpy.SNAPSHOT_PROPERTIES`) — ready to feed
    /// :func:`awpy.plot.frame` via :class:`awpy.plot.Player`. Choose the ticks
    /// with any combination of:
    ///
    /// - ``ticks`` — a single tick or a list of ticks.
    /// - ``every`` / ``seconds`` — a periodic stride (mutually exclusive).
    ///   ``every=64`` is one sample per 64 ticks; ``seconds=1.0`` converts via
    ///   the tick rate.
    /// - ``events`` — the ticks on which these game events fired (a name or list).
    /// - ``start_tick`` / ``end_tick`` — restrict to this window. Given **on
    ///   their own**, they yield every tick in the window (a contiguous range);
    ///   combined with a sampler, they bound it.
    ///
    /// At least one of the above must be given. A single ``ticks`` value seeks
    /// directly to that tick (fast); everything else decodes in parallel across
    /// the demo's keyframes.
    ///
    /// Examples::
    ///
    ///     demo.snapshots(ticks=29000)                    # one moment
    ///     demo.snapshots(ticks=[29000, 30000])           # specific ticks
    ///     demo.snapshots(start_tick=29000, end_tick=30000)  # a contiguous range
    ///     demo.snapshots(every=64)                       # every 64 ticks
    ///     demo.snapshots(seconds=1.0)                    # ~1 sample / second
    ///     demo.snapshots(events="player_death")          # at kill ticks
    ///     demo.snapshots(every=64, start_tick=0, end_tick=64000)
    #[pyo3(signature = (*, ticks=None, every=None, seconds=None, events=None, start_tick=None, end_tick=None))]
    #[pyo3(
        text_signature = "($self, *, ticks=None, every=None, seconds=None, events=None, start_tick=None, end_tick=None)"
    )]
    #[allow(clippy::too_many_arguments)]
    fn snapshots(
        &self,
        py: Python<'_>,
        ticks: Option<TicksArg>,
        every: Option<i32>,
        seconds: Option<f32>,
        events: Option<EventNames>,
        start_tick: Option<i32>,
        end_tick: Option<i32>,
    ) -> PyResult<PyDataFrame> {
        if every.is_some() && seconds.is_some() {
            return Err(PyValueError::new_err(
                "pass either `every` or `seconds`, not both",
            ));
        }
        let explicit = ticks.map(TicksArg::into_vec).unwrap_or_default();
        let has_window = start_tick.is_some() || end_tick.is_some();

        // A single tick with no other selector seeks directly (fast path).
        if explicit.len() == 1
            && every.is_none()
            && seconds.is_none()
            && events.is_none()
            && !has_window
        {
            return py.detach(|| {
                let states = self.parser.snapshot(explicit[0]).map_err(to_py_err)?;
                Ok(PyDataFrame(states_to_frame(&states).map_err(polars_err)?))
            });
        }

        let stride: Option<i32> = match (every, seconds) {
            (Some(step), _) if step < 1 => {
                return Err(PyValueError::new_err("`every` must be >= 1 tick"));
            }
            (Some(step), _) => Some(step),
            (_, Some(secs)) if !secs.is_finite() || secs <= 0.0 => {
                return Err(PyValueError::new_err("`seconds` must be a positive number"));
            }
            (_, Some(secs)) => Some(((secs * self.parser.tickrate()).round() as i32).max(1)),
            (None, None) => None,
        };

        let mut tick_set: HashSet<i32> = HashSet::new();
        if let Some(events) = events {
            let names = events.into_vec();
            let refs: HashSet<&str> = names.iter().map(String::as_str).collect();
            tick_set = py
                .detach(|| self.parser.event_ticks(&refs))
                .map_err(to_py_err)?;
        }
        tick_set.extend(&explicit);

        if stride.is_none() && tick_set.is_empty() && !has_window {
            return Err(PyValueError::new_err(
                "specify at least one of `ticks`, `every`, `seconds`, `events`, \
                 or `start_tick` / `end_tick`",
            ));
        }

        py.detach(|| {
            let states = self
                .parser
                .snapshots_query(
                    stride,
                    &tick_set,
                    start_tick.unwrap_or(i32::MIN),
                    end_tick.unwrap_or(i32::MAX),
                )
                .map_err(to_py_err)?;
            let df = states_to_frame(&states).map_err(polars_err)?;
            Ok(PyDataFrame(df))
        })
    }
}

impl Demo {
    fn event_datasets(&self, py: Python<'_>) -> PyResult<&EventDatasets> {
        py.detach(|| {
            self.event_datasets_cache
                .get_or_try_init(|| self.parser.event_datasets())
        })
        .map_err(to_py_err)
    }

    fn projectiles(&self, py: Python<'_>) -> PyResult<&Projectiles> {
        py.detach(|| {
            self.projectiles_cache
                .get_or_try_init(|| self.parser.projectiles())
        })
        .map_err(to_py_err)
    }

    fn parsed_rounds(&self, py: Python<'_>) -> PyResult<&[Round]> {
        py.detach(|| self.rounds_cache.get_or_try_init(|| self.parser.rounds()))
            .map(Vec::as_slice)
            .map_err(to_py_err)
    }

    fn parsed_players(&self, py: Python<'_>) -> PyResult<&[Player]> {
        py.detach(|| self.players_cache.get_or_try_init(|| self.parser.players()))
            .map(Vec::as_slice)
            .map_err(to_py_err)
    }

    /// `ticks(players_only=True)`: one row per player per tick, decoded in
    /// **parallel** across keyframe segments.
    ///
    /// Anchors on each player pawn and folds in its controller (so a player is a
    /// single `steamid`-keyed row, not separate pawn/controller rows), reading
    /// each prop from whichever entity defines it. Player pawn + controller state
    /// is fully re-keyframed at every `DEM_FullPacket`, so the demo is split at
    /// those keyframes and the segments decoded concurrently, then stitched back
    /// in tick order — identical to a single serial pass. Only the two player
    /// classes are decoded.
    fn ticks_by_player(&self, props: Vec<String>) -> PyResult<PyDataFrame> {
        let filter: HashSet<&str> = HashSet::from([PLAYER_CLASSES[0], PLAYER_CLASSES[1]]);
        let offsets = self.parser.full_packet_offsets().map_err(to_py_err)?;

        // A cold-restarted segment can't populate a *controller-only* field at its
        // first ticks: the pawn→controller link is a sticky field CS2 does not
        // re-key on full packets, so the fallback (name, money, …) would read null
        // until a later delta re-sends it. Steamid is exempt — it's constant, so
        // it's filled from a global slot map after the merge. When any other
        // controller-only field is requested, decode serially so every value
        // matches a single pass exactly; pure pawn-state props (the default) stay
        // parallel.
        let needs_serial = {
            let ctx = self.parser.parse_init().map_err(to_py_err)?;
            let keys = PlayerTickKeys::resolve(&ctx, &props);
            keys.props.iter().any(|p| {
                matches!(
                    p,
                    ResolvedProp::Field {
                        pawn: None,
                        ctrl: Some(_)
                    }
                )
            })
        };

        // One segment per worker: segment 0 from the signon baseline, the rest
        // cold-restarting at an evenly-spaced full packet. Capped by the keyframe
        // count and the thread budget (`AWPY_TICK_SEGMENTS` overrides, mainly so a
        // test can force the serial path and compare).
        let budget = std::env::var("AWPY_TICK_SEGMENTS")
            .ok()
            .and_then(|s| s.parse::<usize>().ok())
            .unwrap_or_else(|| {
                std::thread::available_parallelism()
                    .map(|n| n.get())
                    .unwrap_or(1)
            });
        let n = if needs_serial {
            1
        } else {
            budget.clamp(1, offsets.len().max(1))
        };
        let segments: Vec<(Option<usize>, i32)> = (0..n)
            .map(|i| {
                let start = (i != 0).then(|| offsets[i * offsets.len() / n].0);
                let end_tick = if i == n - 1 {
                    i32::MAX
                } else {
                    offsets[(i + 1) * offsets.len() / n].1
                };
                (start, end_tick)
            })
            .collect();

        let parser = &self.parser;
        let props_ref: &[String] = &props;
        let filter_ref = &filter;
        let parts: Vec<TickSegment> = if n == 1 {
            let (start, end) = segments[0];
            vec![run_tick_segment(parser, filter_ref, props_ref, start, end).map_err(to_py_err)?]
        } else {
            std::thread::scope(|s| {
                let handles: Vec<_> = segments
                    .iter()
                    .map(|&(start, end)| {
                        s.spawn(move || run_tick_segment(parser, filter_ref, props_ref, start, end))
                    })
                    .collect();
                handles
                    .into_iter()
                    .map(|h| h.join().expect("tick segment panicked"))
                    .collect::<Result<Vec<_>, _>>()
            })
            .map_err(to_py_err)?
        };

        // A player's steamid is constant, so union each segment's slot→steamid map
        // into a global one: this fills the identity for a segment's early rows
        // (which cold-restart before the sticky pawn→controller link reappears),
        // matching the serial forward-fill and making the result segment-count
        // independent.
        let mut slot_steamid: HashMap<i32, u64> = HashMap::new();
        for part in &parts {
            slot_steamid.extend(part.slot_steamid.iter().map(|(&k, &v)| (k, v)));
        }

        // Stitch the segments back together in tick order.
        let mut ticks: Vec<i64> = Vec::new();
        let mut steamids: Vec<Option<u64>> = Vec::new();
        let mut col_parts: Vec<Vec<TickColumn>> = (0..props.len()).map(|_| Vec::new()).collect();
        for part in parts {
            ticks.extend(part.ticks);
            steamids.extend(part.pawn_idx.iter().map(|i| slot_steamid.get(i).copied()));
            for (i, c) in part.cols.into_iter().enumerate() {
                col_parts[i].push(c);
            }
        }

        let mut columns: Vec<Column> = vec![
            Column::new("tick".into(), ticks),
            Column::new("steamid".into(), steamids),
        ];
        for (prop, parts) in props.iter().zip(col_parts) {
            columns.push(TickColumn::concat(parts).into_column(prop.as_str()));
        }
        let df = df_from_columns(columns).map_err(polars_err)?;
        Ok(PyDataFrame(df))
    }

    /// Fetch a dataset from the cache, building (and caching) it on a miss.
    fn cached_frame(
        &self,
        py: Python<'_>,
        key: &'static str,
        build: impl FnOnce() -> PyResult<DataFrame> + Send,
    ) -> PyResult<Py<PyAny>> {
        if let Some(df) = self
            .frames_cache
            .lock()
            .expect("dataset cache poisoned")
            .get(key)
        {
            return Ok(df.clone_ref(py));
        }

        let built = py.detach(build)?;
        let obj = PyDataFrame(built).into_pyobject(py)?.unbind();
        let mut cache = self.frames_cache.lock().expect("dataset cache poisoned");
        if let Some(existing) = cache.get(key) {
            return Ok(existing.clone_ref(py));
        }
        cache.insert(key, obj.clone_ref(py));
        Ok(obj)
    }

    /// Fetch one of the five event-based datasets (kills / damages / bomb /
    /// blinds / shots). The typed group is decoded once; only the requested
    /// frame is materialized.
    fn event_frame(&self, py: Python<'_>, key: &'static str) -> PyResult<Py<PyAny>> {
        let ds = self.event_datasets(py)?;
        self.cached_frame(py, key, move || {
            match key {
                "kills" => kills_to_frame(&ds.kills),
                "damages" => damages_to_frame(&ds.damages),
                "bomb" => bomb_to_frame(&ds.bomb),
                "blinds" => blinds_to_frame(&ds.blinds),
                "shots" => shots_to_frame(&ds.shots),
                _ => unreachable!("unknown event dataset"),
            }
            .map_err(polars_err)
        })
    }

    /// Fetch one of the three projectile datasets (grenades / fires / smokes),
    /// decoding the typed group once and materializing only the requested frame.
    fn projectile_frame(&self, py: Python<'_>, key: &'static str) -> PyResult<Py<PyAny>> {
        let projectiles = self.projectiles(py)?;
        self.cached_frame(py, key, move || {
            match key {
                "grenades" => grenades_to_frame(&projectiles.grenades),
                "fires" => fires_to_frame(&projectiles.fires),
                "smokes" => smokes_to_frame(&projectiles.smokes),
                _ => unreachable!("unknown projectile dataset"),
            }
            .map_err(polars_err)
        })
    }
}

/// A demo's game events, keyed by name. Returned by :attr:`Demo.events`.
///
/// Behaves like a read-only mapping from event name to DataFrame: iterating
/// yields the (sorted) event names, ``in`` tests membership, and indexing or
/// attribute access parses one event::
///
///     demo.events.names            # every event name in the demo
///     demo.events.counts           # {name: occurrences}
///     demo.events.player_death     # -> DataFrame
///     demo.events["player_ping"]   # -> DataFrame
///
/// Each frame has a ``tick`` column plus one string column per event key
/// (e.g. ``attacker``, ``weapon``, ``headshot`` for ``player_death``), is
/// built on first access, and is cached.
#[pyclass]
struct Events {
    /// The parser's single shared copy of the decoded event stream.
    events: Arc<[GameEvent]>,
    /// Event indices grouped by name (sorted, so listings are deterministic).
    groups: BTreeMap<String, Vec<usize>>,
    /// Frames already built, by event name.
    frames: Mutex<HashMap<String, Py<PyAny>>>,
}

impl Events {
    /// Build (or fetch the cached) DataFrame for one event; `None` if absent.
    fn frame(&self, py: Python<'_>, name: &str) -> Option<PyResult<Py<PyAny>>> {
        let group = self.groups.get(name)?;
        if let Some(df) = self.frames.lock().expect("events cache poisoned").get(name) {
            return Some(Ok(df.clone_ref(py)));
        }
        let refs: Vec<&GameEvent> = group.iter().map(|&index| &self.events[index]).collect();
        let built = match py.detach(|| events_to_frame(&refs).map_err(polars_err)) {
            Ok(df) => df,
            Err(error) => return Some(Err(error)),
        };
        let obj = match PyDataFrame(built).into_pyobject(py) {
            Ok(obj) => obj.unbind(),
            Err(error) => return Some(Err(error)),
        };
        let mut cache = self.frames.lock().expect("events cache poisoned");
        if let Some(existing) = cache.get(name) {
            return Some(Ok(existing.clone_ref(py)));
        }
        cache.insert(name.to_string(), obj.clone_ref(py));
        Some(Ok(obj))
    }
}

#[pymethods]
impl Events {
    /// The event names present in the demo, sorted.
    #[getter]
    fn names(&self) -> Vec<String> {
        self.groups.keys().cloned().collect()
    }

    /// Occurrence counts, as a ``{event_name: count}`` dict.
    #[getter]
    fn counts(&self) -> BTreeMap<String, usize> {
        self.groups
            .iter()
            .map(|(name, group)| (name.clone(), group.len()))
            .collect()
    }

    fn __repr__(&self) -> String {
        let names: Vec<&str> = self.groups.keys().map(String::as_str).collect();
        format!("Events([{}])", names.join(", "))
    }

    fn __len__(&self) -> usize {
        self.groups.len()
    }

    fn __contains__(&self, name: &str) -> bool {
        self.groups.contains_key(name)
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyResult<Py<PyIterator>> {
        let names = PyList::new(slf.py(), slf.names())?;
        Ok(names.try_iter()?.unbind())
    }

    fn __getitem__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        self.frame(py, name).unwrap_or_else(|| {
            Err(PyKeyError::new_err(format!(
                "no event '{name}' in this demo"
            )))
        })
    }

    fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        self.frame(py, name).unwrap_or_else(|| {
            Err(PyAttributeError::new_err(format!(
                "no event '{name}' in this demo; `.names` lists the {} available",
                self.groups.len()
            )))
        })
    }
}

fn mesh_to_py_err(e: awpy::Error) -> PyErr {
    match e {
        awpy::Error::Io(io_err) => PyErr::from(io_err),
        other => PyValueError::new_err(format!("{other}")),
    }
}

/// Resolve a map-data `source` to a local file with the given `suffix` (e.g.
/// `.mesh`, `.nav`).
///
/// A bare string with no path separator and no `suffix` is a map name: it
/// resolves through `awpy.data.<resolver>` (e.g. `mesh_path` / `nav_path`),
/// which uses the newest cached release — downloading the latest if the cache is
/// empty — and honors `version=`. Anything else — a `Path`, or a string that
/// looks like a file path — is used as-is, and combining it with `version=` is
/// an error.
fn resolve_asset_source(
    py: Python<'_>,
    source: &Bound<'_, PyAny>,
    version: Option<&Bound<'_, PyAny>>,
    suffix: &str,
    resolver: &str,
) -> PyResult<PathBuf> {
    let map_name = source
        .cast::<PyString>()
        .ok()
        .map(|s| s.to_cow())
        .transpose()?
        .filter(|s| !s.ends_with(suffix) && !s.contains(['/', '\\']));

    match map_name {
        Some(map) => py
            .import("awpy.data")?
            .call_method1(resolver, (map.as_ref(), version))?
            .extract(),
        None => {
            if version.is_some() {
                return Err(PyValueError::new_err(format!(
                    "version= applies only when source is a map name like 'de_inferno', \
                     not a {suffix} file path"
                )));
            }
            let path: PathBuf = source.extract()?;
            if !path.exists() {
                return Err(PyFileNotFoundError::new_err(format!(
                    "no such file: {}",
                    path.display()
                )));
            }
            Ok(path)
        }
    }
}

/// Line-of-sight visibility over a map's collision geometry.
///
/// Answers whether the straight segment between two world points is
/// unobstructed, using the compact `.mesh` files published by ``awpy-data``.
/// Construct it from either a map name or a mesh file:
///
/// - ``VisibilityChecker("de_inferno")`` — newest release cached under
///   ``~/.awpy`` (the latest release is downloaded if the cache is empty);
/// - ``VisibilityChecker("de_inferno", version=2000873)`` — a pinned
///   ``awpy-data`` release, downloaded on demand;
/// - ``VisibilityChecker("path/to/de_inferno.mesh")`` — a specific file.
///   Strings count as paths when they end in ``.mesh`` or contain a path
///   separator; ``pathlib.Path`` objects always do.
///
/// A bounding-volume hierarchy is built once at construction, so
/// each query is fast; reuse a single checker for many queries.
///
/// Coordinates are Hammer units, Z-up — the same frame as demo world positions
/// (e.g. the ``*_x`` / ``*_y`` / ``*_z`` columns of :meth:`Demo.kills`), so you
/// can pass entity positions in directly.
///
/// Args:
///     source: Map name (e.g. ``"de_inferno"``) or path to a ``.mesh`` file.
///     version: ``awpy-data`` release to use when ``source`` is a map name —
///         an integer ClientVersion (e.g. ``2000873``); defaults to the
///         newest cached release.
///
/// Raises:
///     FileNotFoundError: If the file does not exist, or the release has no
///         mesh for the map.
///     ValueError: If the file is not a valid awpy mesh, or ``version`` is
///         combined with a file path.
///
/// Example:
///     >>> from awpy import VisibilityChecker
///     >>> vc = VisibilityChecker("de_inferno")
///     >>> vc.is_visible((1258.04, 455.47, 181.22), (-158.62, 819.09, 103.73))
///     True
#[pyclass]
struct VisibilityChecker {
    mesh: VisibilityMesh,
    #[pyo3(get)]
    path: Option<PathBuf>,
}

#[pymethods]
impl VisibilityChecker {
    #[new]
    #[pyo3(signature = (source, *, version=None))]
    #[pyo3(text_signature = "(source, *, version=None)")]
    fn new(
        py: Python<'_>,
        source: &Bound<'_, PyAny>,
        version: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let path = resolve_asset_source(py, source, version, ".mesh", "mesh_path")?;
        let mesh = VisibilityMesh::from_file(&path).map_err(mesh_to_py_err)?;
        Ok(Self {
            mesh,
            path: Some(path),
        })
    }

    fn __repr__(&self) -> String {
        match &self.path {
            Some(p) => format!(
                "VisibilityChecker(path={:?}, triangles={})",
                p,
                self.mesh.triangle_count()
            ),
            None => format!(
                "VisibilityChecker(triangles={})",
                self.mesh.triangle_count()
            ),
        }
    }

    /// Number of triangles in the loaded mesh.
    #[getter]
    fn triangle_count(&self) -> usize {
        self.mesh.triangle_count()
    }

    /// Is the straight segment from ``a`` to ``b`` clear of geometry?
    ///
    /// Args:
    ///     a: Start point ``(x, y, z)`` in Hammer units.
    ///     b: End point ``(x, y, z)`` in Hammer units.
    ///
    /// Returns:
    ///     ``True`` if nothing blocks the line between the two points.
    #[pyo3(text_signature = "($self, a, b)")]
    fn is_visible(&self, a: [f32; 3], b: [f32; 3]) -> bool {
        self.mesh.is_visible(a, b)
    }

    /// Does any triangle block the segment from ``a`` to ``b``?
    ///
    /// The complement of :meth:`is_visible`.
    #[pyo3(text_signature = "($self, a, b)")]
    fn is_occluded(&self, a: [f32; 3], b: [f32; 3]) -> bool {
        self.mesh.is_occluded(a, b)
    }
}

/// Resolve a `NavMesh` source to a local `.nav` file.
///
/// Parse a `weight` string into a [`PathWeight`].
fn parse_path_weight(weight: &str) -> PyResult<PathWeight> {
    match weight.to_ascii_lowercase().as_str() {
        "distance" | "dist" => Ok(PathWeight::Distance),
        "hops" | "hop" => Ok(PathWeight::Hops),
        "size" => Ok(PathWeight::Size),
        other => Err(PyValueError::new_err(format!(
            "unknown weight {other:?}; expected 'distance', 'hops', or 'size'"
        ))),
    }
}

/// A map's navigation mesh: walkable areas and the graph connecting them.
///
/// CS2 tiles each map's walkable surface with convex polygonal *areas* joined
/// by *connections*. This class parses the ``.nav`` files published by
/// ``awpy-data`` and answers the two questions you'd ask of them: which area a
/// world point sits in, and the shortest area-to-area path across the graph.
/// Construct it from either a map name or a ``.nav`` file:
///
/// - ``NavMesh("de_dust2")`` — newest release cached under ``~/.awpy`` (the
///   latest release is downloaded if the cache is empty);
/// - ``NavMesh("de_dust2", version=2000873)`` — a pinned ``awpy-data`` release;
/// - ``NavMesh("path/to/de_dust2.nav")`` — a specific file. Strings count as
///   paths when they end in ``.nav`` or contain a path separator;
///   ``pathlib.Path`` objects always do.
///
/// Coordinates are Hammer units, Z-up — the same frame as demo world positions,
/// so entity positions can be passed straight into :meth:`find_area`. Areas are
/// identified by numeric ``area_id``.
///
/// Args:
///     source: Map name (e.g. ``"de_dust2"``) or path to a ``.nav`` file.
///     version: ``awpy-data`` release to use when ``source`` is a map name — an
///         integer ClientVersion (e.g. ``2000873``); defaults to the newest
///         cached release.
///
/// Raises:
///     FileNotFoundError: If the file does not exist, or the release has no nav
///         for the map.
///     ValueError: If the file is not a valid nav mesh, or ``version`` is
///         combined with a file path.
///
/// Example:
///     >>> from awpy import NavMesh
///     >>> nav = NavMesh("de_dust2")
///     >>> area = nav.find_area((-1500.0, 900.0, 60.0))
///     >>> nav.find_path(area, 42, weight="distance")  # doctest: +SKIP
///     [..., 42]
#[pyclass]
struct NavMesh {
    nav: Nav,
    #[pyo3(get)]
    path: Option<PathBuf>,
}

impl NavMesh {
    /// Resolve a Python argument that is either an area ID (int) or a world
    /// point (3-tuple) to an area ID, returning `None` when it maps to no area.
    fn resolve_area_arg(&self, arg: &Bound<'_, PyAny>) -> PyResult<Option<u32>> {
        if let Ok(id) = arg.extract::<u32>() {
            return Ok(self.nav.area(id).map(|_| id));
        }
        let point: [f32; 3] = arg.extract().map_err(|_| {
            PyValueError::new_err("expected an area id (int) or a point (x, y, z) tuple of floats")
        })?;
        Ok(self.nav.find_area(point))
    }
}

#[pymethods]
impl NavMesh {
    #[new]
    #[pyo3(signature = (source, *, version=None))]
    #[pyo3(text_signature = "(source, *, version=None)")]
    fn new(
        py: Python<'_>,
        source: &Bound<'_, PyAny>,
        version: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let path = resolve_asset_source(py, source, version, ".nav", "nav_path")?;
        let nav = Nav::from_file(&path).map_err(mesh_to_py_err)?;
        Ok(Self {
            nav,
            path: Some(path),
        })
    }

    fn __repr__(&self) -> String {
        let ver = format!("{}.{}", self.nav.version, self.nav.sub_version);
        match &self.path {
            Some(p) => format!(
                "NavMesh(path={:?}, areas={}, version={})",
                p,
                self.nav.area_count(),
                ver
            ),
            None => format!("NavMesh(areas={}, version={})", self.nav.area_count(), ver),
        }
    }

    /// Number of areas in the mesh.
    fn __len__(&self) -> usize {
        self.nav.area_count()
    }

    /// Nav-mesh major version (CS2 currently ships 36).
    #[getter]
    fn version(&self) -> u32 {
        self.nav.version
    }

    /// Nav-mesh sub-version.
    #[getter]
    fn sub_version(&self) -> u32 {
        self.nav.sub_version
    }

    /// Whether the mesh has been analyzed (bot-navigation data generated).
    #[getter]
    fn is_analyzed(&self) -> bool {
        self.nav.is_analyzed
    }

    /// Number of areas in the mesh.
    #[getter]
    fn area_count(&self) -> usize {
        self.nav.area_count()
    }

    /// Every area as a row: ``area_id``, ``hull_index``,
    /// ``dynamic_attribute_flags``, ``n_corners``, ``centroid_x/y/z``, ``size``
    /// (2D area), and ``n_connections`` (distinct neighbours).
    ///
    /// Full polygon geometry for one area is available via :meth:`area`.
    #[getter]
    fn areas(&self) -> PyResult<PyDataFrame> {
        let areas = &self.nav.areas;
        let mut area_id = Vec::with_capacity(areas.len());
        let mut hull_index = Vec::with_capacity(areas.len());
        let mut flags = Vec::with_capacity(areas.len());
        let mut n_corners = Vec::with_capacity(areas.len());
        let mut cx = Vec::with_capacity(areas.len());
        let mut cy = Vec::with_capacity(areas.len());
        let mut cz = Vec::with_capacity(areas.len());
        let mut size = Vec::with_capacity(areas.len());
        let mut n_conn = Vec::with_capacity(areas.len());
        for a in areas {
            let c = a.centroid();
            area_id.push(a.area_id);
            hull_index.push(a.hull_index as u32);
            flags.push(a.dynamic_attribute_flags);
            n_corners.push(a.corners.len() as u32);
            cx.push(c[0]);
            cy.push(c[1]);
            cz.push(c[2]);
            size.push(a.size());
            n_conn.push(self.nav.neighbors(a.area_id).len() as u32);
        }
        let df = df_from_columns(vec![
            Column::new("area_id".into(), area_id),
            Column::new("hull_index".into(), hull_index),
            Column::new("dynamic_attribute_flags".into(), flags),
            Column::new("n_corners".into(), n_corners),
            Column::new("centroid_x".into(), cx),
            Column::new("centroid_y".into(), cy),
            Column::new("centroid_z".into(), cz),
            Column::new("size".into(), size),
            Column::new("n_connections".into(), n_conn),
        ])
        .map_err(polars_err)?;
        Ok(PyDataFrame(df))
    }

    /// Full detail for one area, or ``None`` if no area has that ID.
    ///
    /// Returns a dict with ``area_id``, ``hull_index``,
    /// ``dynamic_attribute_flags``, ``corners`` (list of ``(x, y, z)``),
    /// ``connections`` (distinct neighbour IDs), ``ladders_above``,
    /// ``ladders_below``, ``centroid`` and ``size``.
    #[pyo3(text_signature = "($self, area_id)")]
    fn area(&self, py: Python<'_>, area_id: u32) -> PyResult<Option<Py<PyDict>>> {
        let Some(a) = self.nav.area(area_id) else {
            return Ok(None);
        };
        let d = PyDict::new(py);
        d.set_item("area_id", a.area_id)?;
        d.set_item("hull_index", a.hull_index)?;
        d.set_item("dynamic_attribute_flags", a.dynamic_attribute_flags)?;
        let corners: Vec<(f32, f32, f32)> = a.corners.iter().map(|c| (c[0], c[1], c[2])).collect();
        d.set_item("corners", corners)?;
        d.set_item("connections", self.nav.neighbors(area_id))?;
        d.set_item("ladders_above", a.ladders_above.clone())?;
        d.set_item("ladders_below", a.ladders_below.clone())?;
        let c = a.centroid();
        d.set_item("centroid", (c[0], c[1], c[2]))?;
        d.set_item("size", a.size())?;
        Ok(Some(d.unbind()))
    }

    /// The area containing world point ``point`` (an ``(x, y, z)`` tuple), or
    /// ``None`` if the point is over no area.
    ///
    /// When areas overlap in the XY plane (stacked floors, a bridge over a
    /// tunnel), the area whose height is closest to the point's Z wins.
    #[pyo3(text_signature = "($self, point)")]
    fn find_area(&self, point: [f32; 3]) -> Option<u32> {
        self.nav.find_area(point)
    }

    /// Distinct neighbour area IDs reachable directly from ``area_id``.
    #[pyo3(text_signature = "($self, area_id)")]
    fn neighbors(&self, area_id: u32) -> Vec<u32> {
        self.nav.neighbors(area_id)
    }

    /// Shortest path from ``start`` to ``end`` across the connection graph.
    ///
    /// ``start`` and ``end`` are each either an area ID (``int``) or a world
    /// point (``(x, y, z)`` tuple), which is resolved with :meth:`find_area`.
    /// Returns the list of area IDs from start to end inclusive, or an empty
    /// list if either endpoint maps to no area or no path connects them.
    ///
    /// Args:
    ///     start: Start area ID or point.
    ///     end: End area ID or point.
    ///     weight: Edge cost — ``"distance"`` (default; 3D centroid distance),
    ///         ``"hops"`` (fewest areas), or ``"size"`` (sum of adjacent area
    ///         sizes; routes away from large open areas).
    #[pyo3(signature = (start, end, *, weight="distance"))]
    #[pyo3(text_signature = "($self, start, end, *, weight='distance')")]
    fn find_path(
        &self,
        start: &Bound<'_, PyAny>,
        end: &Bound<'_, PyAny>,
        weight: &str,
    ) -> PyResult<Vec<u32>> {
        let w = parse_path_weight(weight)?;
        let (Some(s), Some(e)) = (self.resolve_area_arg(start)?, self.resolve_area_arg(end)?)
        else {
            return Ok(Vec::new());
        };
        Ok(self.nav.find_path(s, e, w))
    }
}

/// One player observation for [`compute_map_control`]:
/// `(x, y, z, side, crouched, blind)`. `side` is the demo's `"terrorist"` /
/// `"counter-terrorist"` (or `"t"` / `"ct"`); other sides are dropped.
/// `(x, y, z, side, crouched, blind, yaw)` for one living player. `yaw` is the
/// eye-angle yaw in degrees and may be `None`; only `method="vision"` reads it.
type PlayerObs = (f32, f32, f32, String, bool, bool, Option<f32>);
/// A sphere occluder for [`compute_map_control`]: `(x, y, z, radius)`.
type Sphere = (f32, f32, f32, f32);

/// Map a side string to a [`Team`], or `None` for a side that holds no control
/// (unassigned / spectator).
fn parse_team(side: &str) -> Option<Team> {
    match side.to_ascii_lowercase().as_str() {
        "t" | "terrorist" => Some(Team::T),
        "ct" | "counter-terrorist" => Some(Team::Ct),
        _ => None,
    }
}

/// Compute one snapshot's map control over a nav mesh.
///
/// The low-level primitive behind :func:`awpy.map_control.map_control`. Given
/// player positions and (for vision) a :class:`VisibilityChecker`, it labels
/// every nav area ``"ct"`` / ``"t"`` / ``"contested"`` / ``"neutral"`` and
/// returns size-weighted summary fractions.
///
/// Args:
///     nav: The map's :class:`NavMesh`.
///     players: Sequence of ``(x, y, z, side, crouched, blind, yaw)`` for the
///         living players at the tick. ``yaw`` is the eye-angle yaw in degrees and
///         may be ``None``; only ``method="vision"`` reads it, and a player with
///         no yaw is left unrestricted.
///     visibility: The map's :class:`VisibilityChecker`; required for
///         ``method="vision"`` and ``method="raycast"``.
///     method: ``"raycast"`` (line of sight in any direction, smoke-aware),
///         ``"vision"`` (the same, narrowed to each player's field of view), or
///         ``"reachability"`` (who reaches each area first, fire-aware).
///     smokes: Active smoke spheres ``(x, y, z, radius)`` (vision only).
///     fires: Active inferno spheres ``(x, y, z, radius)`` (reachability only).
///     detail: When ``True`` (default) include the per-area arrays; when
///         ``False`` return only the summary fractions.
///     eye_height: Standing eye height above the feet, where vision rays start.
///     crouch_eye_height: Eye height when crouched.
///     target_height: Height above an area's floor that vision aims at.
///     max_distance: Optional cap on vision range; ``None`` is unbounded.
///     contest_margin: Reachability travel-distance tie band.
///     fov: Horizontal field of view in degrees for ``method="vision"``
///         (default ``90.0``, CS2's own FOV); ``360.0`` or more removes the limit,
///         making it equivalent to ``"raycast"``. See
///         :class:`awpy.map_control.MapControlParams` for all six.
///
/// Returns:
///     A dict with ``ct_fraction``, ``t_fraction``, ``contested_fraction``,
///     ``neutral_fraction``, ``net_control``, and (when ``detail``) the
///     ``area_ids`` / ``control`` / ``ct`` / ``t`` per-area lists.
#[pyfunction]
#[pyo3(signature = (
    nav,
    players,
    *,
    visibility=None,
    method="vision",
    smokes=Vec::new(),
    fires=Vec::new(),
    detail=true,
    eye_height=64.0,
    crouch_eye_height=46.0,
    target_height=46.0,
    max_distance=None,
    contest_margin=200.0,
    fov=90.0,
))]
#[pyo3(
    text_signature = "(nav, players, *, visibility=None, method='vision', smokes=[], fires=[], \
                       detail=True, eye_height=64.0, crouch_eye_height=46.0, target_height=46.0, \
                       max_distance=None, contest_margin=200.0, fov=90.0)"
)]
#[allow(clippy::too_many_arguments)]
fn compute_map_control(
    py: Python<'_>,
    nav: PyRef<'_, NavMesh>,
    players: Vec<PlayerObs>,
    visibility: Option<PyRef<'_, VisibilityChecker>>,
    method: &str,
    smokes: Vec<Sphere>,
    fires: Vec<Sphere>,
    detail: bool,
    eye_height: f32,
    crouch_eye_height: f32,
    target_height: f32,
    max_distance: Option<f32>,
    contest_margin: f64,
    fov: f32,
) -> PyResult<Py<PyDict>> {
    let observers: Vec<Observer> = players
        .iter()
        .filter_map(|(x, y, z, side, crouched, blind, yaw)| {
            parse_team(side).map(|team| Observer {
                pos: [*x, *y, *z],
                team,
                crouched: *crouched,
                blind: *blind,
                yaw: *yaw,
            })
        })
        .collect();

    let params = McParams {
        eye_height,
        crouch_eye_height,
        target_height,
        max_distance,
        contest_margin,
        fov,
    };
    let to_occluders = |spheres: &[Sphere]| {
        spheres
            .iter()
            .map(|(x, y, z, r)| Occluder {
                center: [*x, *y, *z],
                radius: *r,
            })
            .collect::<Vec<_>>()
    };

    let result = match method.to_ascii_lowercase().as_str() {
        line_of_sight @ ("vision" | "raycast") => {
            let vc = visibility.as_ref().ok_or_else(|| {
                PyValueError::new_err(format!(
                    "method={line_of_sight:?} requires a VisibilityChecker (pass visibility=...)"
                ))
            })?;
            // The two share everything but the field-of-view cone.
            let model = if line_of_sight == "vision" {
                vision_control
            } else {
                raycast_control
            };
            model(
                &nav.nav,
                &vc.mesh,
                &observers,
                &to_occluders(&smokes),
                &params,
            )
        }
        "reachability" | "reach" => {
            reachability_control(&nav.nav, &observers, &to_occluders(&fires), &params)
        }
        other => {
            return Err(PyValueError::new_err(format!(
                "unknown method {other:?}; expected 'vision', 'raycast' or 'reachability'"
            )));
        }
    };

    let d = PyDict::new(py);
    d.set_item("ct_fraction", result.ct_fraction)?;
    d.set_item("t_fraction", result.t_fraction)?;
    d.set_item("contested_fraction", result.contested_fraction)?;
    d.set_item("neutral_fraction", result.neutral_fraction)?;
    d.set_item("net_control", result.net_control)?;
    if detail {
        let n = result.areas.len();
        let (mut ids, mut control, mut ct, mut t) = (
            Vec::with_capacity(n),
            Vec::with_capacity(n),
            Vec::with_capacity(n),
            Vec::with_capacity(n),
        );
        for a in &result.areas {
            ids.push(a.area_id);
            control.push(a.control.as_str());
            ct.push(a.ct);
            t.push(a.t);
        }
        d.set_item("area_ids", ids)?;
        d.set_item("control", control)?;
        d.set_item("ct", ct)?;
        d.set_item("t", t)?;
    }
    Ok(d.unbind())
}

/// Column helper: collect a field from each item via a getter.
macro_rules! col {
    ($name:literal, $items:expr, $f:expr) => {
        Column::new($name.into(), $items.iter().map($f).collect::<Vec<_>>())
    };
}

fn rounds_to_frame(rounds: &[Round]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("round_num", rounds, |r| r.round_num),
        col!("start_tick", rounds, |r| r.start_tick),
        col!("freeze_end_tick", rounds, |r| r.freeze_end_tick),
        col!("end_tick", rounds, |r| r.end_tick),
        col!("official_end_tick", rounds, |r| r.official_end_tick),
        col!("winner", rounds, |r| r.winner),
        col!("winner_side", rounds, |r| r.winner_side.clone()),
        col!("reason", rounds, |r| r.reason),
        col!("reason_name", rounds, |r| r.reason_name.clone()),
        col!("is_knife_round", rounds, |r| r.is_knife_round),
    ])
}

fn round_economy_to_frame(econ: &[RoundEconomy]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("round_num", econ, |e| e.round_num),
        col!("side", econ, |e| e.side),
        col!("equipment_value", econ, |e| e.equipment_value),
        col!("buy_type", econ, |e| e.buy_type),
        col!("n_players", econ, |e| e.n_players),
    ])
}

fn kills_to_frame(kills: &[Kill]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("attacker_steamid", kills, |k| k.attacker_steamid),
        col!("attacker_name", kills, |k| k.attacker_name.clone()),
        col!("attacker_side", kills, |k| k.attacker_side.clone()),
        col!("attacker_x", kills, |k| k.attacker_x),
        col!("attacker_y", kills, |k| k.attacker_y),
        col!("attacker_z", kills, |k| k.attacker_z),
        col!("victim_steamid", kills, |k| k.victim_steamid),
        col!("victim_name", kills, |k| k.victim_name.clone()),
        col!("victim_side", kills, |k| k.victim_side.clone()),
        col!("victim_x", kills, |k| k.victim_x),
        col!("victim_y", kills, |k| k.victim_y),
        col!("victim_z", kills, |k| k.victim_z),
        col!("assister_steamid", kills, |k| k.assister_steamid),
        col!("assister_name", kills, |k| k.assister_name.clone()),
        col!("assister_side", kills, |k| k.assister_side.clone()),
        col!("assister_x", kills, |k| k.assister_x),
        col!("assister_y", kills, |k| k.assister_y),
        col!("assister_z", kills, |k| k.assister_z),
        col!("weapon", kills, |k| k.weapon.clone()),
        col!("headshot", kills, |k| k.headshot),
        col!("assist_flash", kills, |k| k.assist_flash),
        col!("dominated", kills, |k| k.dominated),
        col!("noscope", kills, |k| k.noscope),
        col!("penetrated", kills, |k| k.penetrated),
        col!("revenge", kills, |k| k.revenge),
        col!("thrusmoke", kills, |k| k.thrusmoke),
        col!("hitgroup", kills, |k| k.hitgroup),
        col!("hitgroup_name", kills, |k| k.hitgroup_name.clone()),
        col!("is_trade", kills, |k| k.is_trade),
        col!("victim_traded", kills, |k| k.victim_traded),
        col!("tick", kills, |k| k.tick),
    ])
}

fn damages_to_frame(damages: &[Damage]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("attacker_steamid", damages, |d| d.attacker_steamid),
        col!("attacker_name", damages, |d| d.attacker_name.clone()),
        col!("attacker_side", damages, |d| d.attacker_side.clone()),
        col!("attacker_x", damages, |d| d.attacker_x),
        col!("attacker_y", damages, |d| d.attacker_y),
        col!("attacker_z", damages, |d| d.attacker_z),
        col!("victim_steamid", damages, |d| d.victim_steamid),
        col!("victim_name", damages, |d| d.victim_name.clone()),
        col!("victim_side", damages, |d| d.victim_side.clone()),
        col!("victim_x", damages, |d| d.victim_x),
        col!("victim_y", damages, |d| d.victim_y),
        col!("victim_z", damages, |d| d.victim_z),
        col!("weapon", damages, |d| d.weapon.clone()),
        col!("dmg_health", damages, |d| d.dmg_health),
        col!("dmg_armor", damages, |d| d.dmg_armor),
        col!("hitgroup", damages, |d| d.hitgroup),
        col!("hitgroup_name", damages, |d| d.hitgroup_name.clone()),
        col!("health_pre", damages, |d| d.health_pre),
        col!("health_post", damages, |d| d.health_post),
        col!("armor_pre", damages, |d| d.armor_pre),
        col!("armor_post", damages, |d| d.armor_post),
        col!("tick", damages, |d| d.tick),
    ])
}

fn bomb_to_frame(bomb: &[BombEvent]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", bomb, |b| b.tick),
        col!("event", bomb, |b| b.event.clone()),
        col!("steamid", bomb, |b| b.steamid),
        col!("name", bomb, |b| b.name.clone()),
        col!("bombsite", bomb, |b| b.bombsite.clone()),
        col!("x", bomb, |b| b.x),
        col!("y", bomb, |b| b.y),
        col!("z", bomb, |b| b.z),
    ])
}

fn grenades_to_frame(grenades: &[Grenade]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", grenades, |g| g.tick),
        col!("thrower_name", grenades, |g| g.thrower_name.clone()),
        col!("thrower_steamid", grenades, |g| g.thrower_steamid),
        col!("thrower_side", grenades, |g| g.thrower_side.clone()),
        col!("type", grenades, |g| g.grenade_type.clone()),
        col!("entity_id", grenades, |g| g.entity_id),
        col!("x", grenades, |g| g.x),
        col!("y", grenades, |g| g.y),
        col!("z", grenades, |g| g.z),
    ])
}

fn fires_to_frame(fires: &[Fire]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("start_tick", fires, |f| f.start_tick),
        col!("end_tick", fires, |f| f.end_tick),
        col!("thrower_name", fires, |f| f.thrower_name.clone()),
        col!("thrower_steamid", fires, |f| f.thrower_steamid),
        col!("thrower_side", fires, |f| f.thrower_side.clone()),
        col!("type", fires, |f| f.fire_type.clone()),
        col!("entity_id", fires, |f| f.entity_id),
        col!("x", fires, |f| f.x),
        col!("y", fires, |f| f.y),
        col!("z", fires, |f| f.z),
    ])
}

fn smokes_to_frame(smokes: &[Smoke]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("start_tick", smokes, |s| s.start_tick),
        col!("end_tick", smokes, |s| s.end_tick),
        col!("thrower_name", smokes, |s| s.thrower_name.clone()),
        col!("thrower_steamid", smokes, |s| s.thrower_steamid),
        col!("thrower_side", smokes, |s| s.thrower_side.clone()),
        col!("entity_id", smokes, |s| s.entity_id),
        col!("x", smokes, |s| s.x),
        col!("y", smokes, |s| s.y),
        col!("z", smokes, |s| s.z),
    ])
}

fn shots_to_frame(shots: &[Shot]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", shots, |s| s.tick),
        col!("steamid", shots, |s| s.steamid),
        col!("name", shots, |s| s.name.clone()),
        col!("side", shots, |s| s.side.clone()),
        col!("x", shots, |s| s.x),
        col!("y", shots, |s| s.y),
        col!("z", shots, |s| s.z),
        col!("pitch", shots, |s| s.pitch),
        col!("yaw", shots, |s| s.yaw),
        col!("weapon", shots, |s| s.weapon.clone()),
        col!("scoped", shots, |s| s.scoped),
        col!("inaccuracy", shots, |s| s.inaccuracy),
        col!("num_bullets_remaining", shots, |s| s.num_bullets_remaining),
    ])
}

fn players_to_frame(players: &[Player]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("steamid", players, |p| p.steamid),
        col!("name", players, |p| p.name.clone()),
        col!("side", players, |p| p.side.clone()),
        col!("team_clan_name", players, |p| p.team_clan_name.clone()),
    ])
}

fn states_to_frame(states: &[PlayerState]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", states, |s| s.tick),
        col!("steamid", states, |s| s.steamid),
        col!("name", states, |s| s.name.clone()),
        col!("side", states, |s| s.side),
        col!("x", states, |s| s.x),
        col!("y", states, |s| s.y),
        col!("z", states, |s| s.z),
        col!("pitch", states, |s| s.pitch),
        col!("yaw", states, |s| s.yaw),
        col!("health", states, |s| s.health),
        col!("armor", states, |s| s.armor),
        col!("has_helmet", states, |s| s.has_helmet),
        col!("has_defuser", states, |s| s.has_defuser),
        col!("has_bomb", states, |s| s.has_bomb),
        col!("active_weapon", states, |s| s.active_weapon),
        col!("primary_weapon", states, |s| s.primary_weapon),
        col!("secondary_weapon", states, |s| s.secondary_weapon),
        col!("fire_grenades", states, |s| s.fire_grenades),
        col!("smoke_grenades", states, |s| s.smoke_grenades),
        col!("he_grenades", states, |s| s.he_grenades),
        col!("flashbangs", states, |s| s.flashbangs),
        col!("decoy_grenades", states, |s| s.decoy_grenades),
        col!("equipment_value", states, |s| s.equipment_value),
        col!("equipment_value_round_start", states, |s| s
            .equipment_value_round_start),
        col!("money", states, |s| s.money),
        col!("is_crouched", states, |s| s.is_crouched),
        col!("is_walking", states, |s| s.is_walking),
        col!("is_jumping", states, |s| s.is_jumping),
        col!("is_in_bomb_zone", states, |s| s.is_in_bomb_zone),
        col!("is_scoped", states, |s| s.is_scoped),
        col!("is_defusing", states, |s| s.is_defusing),
        col!("flash_duration", states, |s| s.flash_duration),
        col!("inventory", states, |s| s.inventory.clone()),
    ])
}

fn item_events_to_frame(items: &[ItemEvent]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", items, |i| i.tick),
        col!("action", items, |i| i.action.clone()),
        col!("steamid", items, |i| i.steamid),
        col!("name", items, |i| i.name.clone()),
        col!("side", items, |i| i.side.clone()),
        col!("item", items, |i| i.item.clone()),
        col!("x", items, |i| i.x),
        col!("y", items, |i| i.y),
        col!("z", items, |i| i.z),
        col!("original_owner_steamid", items, |i| i
            .original_owner_steamid),
        col!("cost", items, |i| i.cost),
        col!("near_buy_zone", items, |i| i.near_buy_zone),
    ])
}

fn blinds_to_frame(blinds: &[Blind]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", blinds, |b| b.tick),
        col!("attacker_steamid", blinds, |b| b.attacker_steamid),
        col!("attacker_name", blinds, |b| b.attacker_name.clone()),
        col!("attacker_side", blinds, |b| b.attacker_side.clone()),
        col!("attacker_x", blinds, |b| b.attacker_x),
        col!("attacker_y", blinds, |b| b.attacker_y),
        col!("attacker_z", blinds, |b| b.attacker_z),
        col!("victim_steamid", blinds, |b| b.victim_steamid),
        col!("victim_name", blinds, |b| b.victim_name.clone()),
        col!("victim_side", blinds, |b| b.victim_side.clone()),
        col!("victim_x", blinds, |b| b.victim_x),
        col!("victim_y", blinds, |b| b.victim_y),
        col!("victim_z", blinds, |b| b.victim_z),
        col!("duration", blinds, |b| b.duration),
    ])
}

fn chat_to_frame(chat: &[ChatMessage]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("tick", chat, |c| c.tick),
        col!("entity_index", chat, |c| c.entity_index),
        col!("name", chat, |c| c.name.clone()),
        col!("message", chat, |c| c.message.clone()),
        col!("channel", chat, |c| c.channel.clone()),
    ])
}

fn stats_to_frame(stats: &[PlayerStats]) -> PolarsResult<DataFrame> {
    df_from_columns(vec![
        col!("steamid", stats, |s| s.steamid),
        col!("name", stats, |s| s.name.clone()),
        col!("rounds_played", stats, |s| s.rounds_played),
        col!("kills", stats, |s| s.kills),
        col!("deaths", stats, |s| s.deaths),
        col!("assists", stats, |s| s.assists),
        col!("flash_assists", stats, |s| s.flash_assists),
        col!("headshot_kills", stats, |s| s.headshot_kills),
        col!("headshot_pct", stats, |s| s.headshot_pct),
        col!("opening_kills", stats, |s| s.opening_kills),
        col!("opening_deaths", stats, |s| s.opening_deaths),
        col!("traded_deaths", stats, |s| s.traded_deaths),
        col!("multikill_2k", stats, |s| s.multikill_2k),
        col!("multikill_3k", stats, |s| s.multikill_3k),
        col!("multikill_4k", stats, |s| s.multikill_4k),
        col!("multikill_5k", stats, |s| s.multikill_5k),
        col!("kast", stats, |s| s.kast),
        col!("adr", stats, |s| s.adr),
        col!("clutches_played", stats, |s| s.clutches_played),
        col!("clutches_won", stats, |s| s.clutches_won),
        col!("clutch_1v1", stats, |s| s.clutch_1v1),
        col!("clutch_1v2", stats, |s| s.clutch_1v2),
        col!("clutch_1v3", stats, |s| s.clutch_1v3),
        col!("clutch_1v4", stats, |s| s.clutch_1v4),
        col!("clutch_1v5", stats, |s| s.clutch_1v5),
        col!("utility_damage", stats, |s| s.utility_damage),
        col!("flashes_thrown", stats, |s| s.flashes_thrown),
        col!("enemies_flashed", stats, |s| s.enemies_flashed),
        col!("flash_duration_dealt", stats, |s| s.flash_duration_dealt),
    ])
}

/// Resolve each prop name to a packed field key for a given serializer.
fn resolve_keys(serializer: &Serializer, props: &[String]) -> Vec<Option<u64>> {
    props
        .iter()
        .map(|p| serializer.resolve_field_key(p))
        .collect()
}

/// Read a resolved field from an entity (borrowed; not formatted).
fn read_field(entity: &Entity, key: Option<u64>) -> Option<&FieldValue> {
    key.and_then(|k| entity.fields.get(&k))
}

/// Extract a `u64` from an integer-typed field value, regardless of the concrete
/// integer variant (used for `m_steamID`).
fn field_u64(v: &FieldValue) -> Option<u64> {
    match v {
        FieldValue::U64(n) => Some(*n),
        FieldValue::U32(n) => Some(*n as u64),
        FieldValue::I64(n) => Some(*n as u64),
        FieldValue::I32(n) => Some(*n as u64),
        _ => None,
    }
}

/// Field-path prefix of a pawn's networked origin (cell index + in-cell offset).
const ORIGIN_PATH: &str = "CBodyComponent.m_skeletonInstance.m_vecOrigin";

/// Default player properties for `ticks()` when none are given: world position
/// plus the common scalar state.
fn default_tick_props() -> Vec<String> {
    ["X", "Y", "Z", "health", "armor", "team_num"]
        .into_iter()
        .map(String::from)
        .collect()
}

/// A resolved `ticks` property: either a computed world-position axis or a raw
/// field key on the pawn and/or controller serializer.
#[derive(Clone, Copy)]
enum ResolvedProp {
    /// World position axis (0 = X, 1 = Y, 2 = Z), computed from cell + offset.
    Position(usize),
    Field {
        pawn: Option<u64>,
        ctrl: Option<u64>,
    },
}

/// Map a (possibly friendly) property name to its raw network path, then resolve
/// it against the pawn and controller serializers. `X`/`Y`/`Z` are computed
/// world position; unrecognized names pass through as raw field paths.
fn resolve_prop(
    name: &str,
    pawn_ser: Option<&Serializer>,
    ctrl_ser: Option<&Serializer>,
) -> ResolvedProp {
    match name {
        "X" | "x" => return ResolvedProp::Position(0),
        "Y" | "y" => return ResolvedProp::Position(1),
        "Z" | "z" => return ResolvedProp::Position(2),
        _ => {}
    }
    let path = match name {
        "health" | "hp" => "m_iHealth",
        "armor" => "m_ArmorValue",
        "team" | "team_num" => "m_iTeamNum",
        "name" => "m_iszPlayerName",
        "money" => "m_pInGameMoneyServices.m_iAccount",
        other => other,
    };
    ResolvedProp::Field {
        pawn: pawn_ser.and_then(|s| s.resolve_field_key(path)),
        ctrl: ctrl_ser.and_then(|s| s.resolve_field_key(path)),
    }
}

/// Player field keys and resolved props for one `ticks` pass, resolved once (the
/// pawn/controller serializers are stable across the demo).
struct PlayerTickKeys {
    pawn_id: i32,
    /// Pawn's `m_hController` handle and the controller's `m_steamID`.
    controller: Option<u64>,
    steamid: Option<u64>,
    /// Cell index and in-cell offset keys per axis, for computed position.
    cell: [Option<u64>; 3],
    offset: [Option<u64>; 3],
    props: Vec<ResolvedProp>,
}

impl PlayerTickKeys {
    fn resolve(ctx: &Context, props: &[String]) -> Self {
        let pawn_ser = ctx.serializers.get(PLAYER_CLASSES[0]);
        let ctrl_ser = ctx.serializers.get(PLAYER_CLASSES[1]);
        let axis = |name: &str| {
            pawn_ser.and_then(|s| s.resolve_field_key(&format!("{ORIGIN_PATH}.{name}")))
        };
        PlayerTickKeys {
            pawn_id: ctx.class_info.id_of(PLAYER_CLASSES[0]).unwrap_or(-1),
            controller: pawn_ser.and_then(|s| s.resolve_field_key("m_hController")),
            steamid: ctrl_ser.and_then(|s| s.resolve_field_key("m_steamID")),
            cell: [axis("m_cellX"), axis("m_cellY"), axis("m_cellZ")],
            offset: [axis("m_vecX"), axis("m_vecY"), axis("m_vecZ")],
            props: props
                .iter()
                .map(|p| resolve_prop(p, pawn_ser, ctrl_ser))
                .collect(),
        }
    }
}

/// Compute a pawn's world position on one axis from its cell index and in-cell
/// offset, or `None` if either is absent this tick.
fn read_position(pawn: &Entity, cell_key: Option<u64>, off_key: Option<u64>) -> Option<f32> {
    let cell = field_as_int(read_field(pawn, cell_key)?)? as i32;
    let off = field_as_float(read_field(pawn, off_key)?)? as f32;
    Some(cell_to_world(cell, off))
}

/// One keyframe segment's accumulated tick rows, merged with its peers afterward.
struct TickSegment {
    ticks: Vec<i64>,
    /// Pawn slot index per row. A cold-restarted segment lacks the sticky
    /// pawn→controller link at its first ticks, so `steamid` is resolved after
    /// the merge from a global slot→steamid map (a player's steamid is constant),
    /// keeping the identity column complete and segment-count-independent.
    pawn_idx: Vec<i32>,
    /// Steamid seen for each pawn slot anywhere in this segment.
    slot_steamid: HashMap<i32, u64>,
    cols: Vec<TickColumn>,
}

/// Decode one keyframe segment and accumulate one row per player per tick.
///
/// A pawn's `m_hController` link is a sticky field CS2 does not re-send every
/// tick, so when the live lookup misses, the last resolved controller slot is
/// reused — keeping steamid / name / money populated. Because each segment
/// cold-restarts at a full packet where players are fully re-keyframed, this is
/// exact per segment (see [`Parser::decode_segment`]).
fn run_tick_segment(
    parser: &Parser,
    filter: &HashSet<&str>,
    props: &[String],
    start: Option<usize>,
    end_tick: i32,
) -> Result<TickSegment, awpy::Error> {
    let mut seg = TickSegment {
        ticks: Vec::new(),
        pawn_idx: Vec::new(),
        slot_steamid: HashMap::new(),
        cols: (0..props.len()).map(|_| TickColumn::new()).collect(),
    };
    let mut keys: Option<PlayerTickKeys> = None;
    let mut pawn_to_ctrl: HashMap<i32, i32> = HashMap::new();

    parser.decode_segment(start, end_tick, filter, |ctx| {
        let k = keys.get_or_insert_with(|| PlayerTickKeys::resolve(ctx, props));
        for (_, pawn) in ctx.entities.iter() {
            if !pawn.active || pawn.class_id != k.pawn_id {
                continue;
            }
            let controller = match pawn
                .get_handle(k.controller)
                .and_then(|h| ctx.entities.get_by_handle(h))
            {
                Some(c) => {
                    pawn_to_ctrl.insert(pawn.index, c.index);
                    Some(c)
                }
                None => pawn_to_ctrl
                    .get(&pawn.index)
                    .and_then(|&i| ctx.entities.get(i)),
            };
            seg.ticks.push(ctx.tick as i64);
            seg.pawn_idx.push(pawn.index);
            if let Some(sid) = controller
                .and_then(|c| read_field(c, k.steamid))
                .and_then(field_u64)
            {
                seg.slot_steamid.insert(pawn.index, sid);
            }
            for (i, prop) in k.props.iter().enumerate() {
                match *prop {
                    ResolvedProp::Position(axis) => {
                        match read_position(pawn, k.cell[axis], k.offset[axis]) {
                            Some(f) => seg.cols[i].push(Some(&FieldValue::F32(f))),
                            None => seg.cols[i].push(None),
                        }
                    }
                    ResolvedProp::Field { pawn: pk, ctrl: ck } => {
                        let val = read_field(pawn, pk)
                            .or_else(|| controller.and_then(|c| read_field(c, ck)));
                        seg.cols[i].push(val);
                    }
                }
            }
        }
    })?;

    Ok(seg)
}

/// Accumulates one [`Demo::ticks`] output column, picking a native Polars dtype
/// from the values it sees rather than stringifying everything: integer fields
/// become Int64, floats Float64, bools Boolean, and strings/vectors Utf8. A
/// column that mixes integers and floats widens to Float64; any other mix falls
/// back to Utf8 (best-effort — such a column is pathological). A column that is
/// only ever absent stays all-null Utf8, as before.
enum TickColumn {
    /// No concrete value yet — a run of `n` leading nulls.
    Empty(usize),
    Bool(Vec<Option<bool>>),
    Int(Vec<Option<i64>>),
    Float(Vec<Option<f64>>),
    Str(Vec<Option<String>>),
}

impl TickColumn {
    fn new() -> Self {
        TickColumn::Empty(0)
    }

    fn push(&mut self, value: Option<&FieldValue>) {
        match value {
            None => self.push_null(),
            Some(v) => self.push_value(v),
        }
    }

    fn push_null(&mut self) {
        match self {
            TickColumn::Empty(n) => *n += 1,
            TickColumn::Bool(v) => v.push(None),
            TickColumn::Int(v) => v.push(None),
            TickColumn::Float(v) => v.push(None),
            TickColumn::Str(v) => v.push(None),
        }
    }

    fn push_value(&mut self, v: &FieldValue) {
        // Establish the column's dtype from the first concrete value, back-filling
        // the leading nulls; thereafter coerce/promote to keep it consistent.
        if let TickColumn::Empty(n) = self {
            *self = TickColumn::seed(*n, v);
            return;
        }
        match (self, field_as_int(v), field_as_float(v), field_as_bool(v)) {
            (TickColumn::Int(col), Some(i), _, _) => col.push(Some(i)),
            (TickColumn::Float(col), _, Some(f), _) => col.push(Some(f)),
            // An integer arriving in a float column just widens to f64.
            (TickColumn::Float(col), Some(i), None, _) => col.push(Some(i as f64)),
            (TickColumn::Bool(col), _, _, Some(b)) => col.push(Some(b)),
            (this @ TickColumn::Int(_), None, Some(f), _) => {
                // A float arriving in an int column widens the whole column.
                this.widen_int_to_float();
                if let TickColumn::Float(col) = this {
                    col.push(Some(f));
                }
            }
            (this, ..) => {
                // Any other mix (e.g. string vs number) falls back to strings.
                this.widen_to_str();
                if let TickColumn::Str(col) = this {
                    col.push(Some(format!("{v}")));
                }
            }
        }
    }

    /// A fresh column seeded with `nulls` leading nulls then the first value.
    fn seed(nulls: usize, v: &FieldValue) -> TickColumn {
        if let Some(i) = field_as_int(v) {
            let mut col = vec![None; nulls];
            col.push(Some(i));
            TickColumn::Int(col)
        } else if let Some(f) = field_as_float(v) {
            let mut col = vec![None; nulls];
            col.push(Some(f));
            TickColumn::Float(col)
        } else if let FieldValue::Bool(b) = v {
            let mut col = vec![None; nulls];
            col.push(Some(*b));
            TickColumn::Bool(col)
        } else {
            let mut col = vec![None; nulls];
            col.push(Some(format!("{v}")));
            TickColumn::Str(col)
        }
    }

    fn widen_int_to_float(&mut self) {
        if let TickColumn::Int(col) = self {
            let floats = col.iter().map(|o| o.map(|i| i as f64)).collect();
            *self = TickColumn::Float(floats);
        }
    }

    fn widen_to_str(&mut self) {
        let strs: Vec<Option<String>> = match self {
            TickColumn::Empty(n) => vec![None; *n],
            TickColumn::Bool(v) => v.iter().map(|o| o.map(|b| b.to_string())).collect(),
            TickColumn::Int(v) => v.iter().map(|o| o.map(|i| i.to_string())).collect(),
            TickColumn::Float(v) => v.iter().map(|o| o.map(|f| f.to_string())).collect(),
            TickColumn::Str(_) => return,
        };
        *self = TickColumn::Str(strs);
    }

    fn into_column(self, name: &str) -> Column {
        match self {
            TickColumn::Empty(n) => Column::new(name.into(), vec![None::<String>; n]),
            TickColumn::Bool(v) => Column::new(name.into(), v),
            TickColumn::Int(v) => Column::new(name.into(), v),
            TickColumn::Float(v) => Column::new(name.into(), v),
            TickColumn::Str(v) => Column::new(name.into(), v),
        }
    }

    /// Concatenate per-segment columns into one (parallel `ticks` merges the
    /// segments' columns), reconciling dtypes exactly as `push` does: int + float
    /// widen to float, incompatible mixes fall back to strings, and an all-absent
    /// column stays null.
    fn concat(parts: Vec<TickColumn>) -> TickColumn {
        let mut it = parts.into_iter();
        let mut acc = it.next().unwrap_or(TickColumn::Empty(0));
        for part in it {
            acc = acc.append(part);
        }
        acc
    }

    fn append(self, other: TickColumn) -> TickColumn {
        use TickColumn::*;
        match (self, other) {
            (Empty(a), other) => other.pad_front(a),
            (this, Empty(b)) => this.pad_back(b),
            (Bool(mut a), Bool(b)) => {
                a.extend(b);
                Bool(a)
            }
            (Int(mut a), Int(b)) => {
                a.extend(b);
                Int(a)
            }
            (Float(mut a), Float(b)) => {
                a.extend(b);
                Float(a)
            }
            (Str(mut a), Str(b)) => {
                a.extend(b);
                Str(a)
            }
            // An int/float mix widens the whole column to float.
            (Int(a), Float(b)) => {
                let mut f = Int(a).into_floats();
                f.extend(b);
                Float(f)
            }
            (Float(mut a), Int(b)) => {
                a.extend(Int(b).into_floats());
                Float(a)
            }
            // Anything else falls back to strings.
            (a, b) => {
                let mut s = a.into_strs();
                s.extend(b.into_strs());
                Str(s)
            }
        }
    }

    /// Prepend `n` leading nulls, adopting this column's own dtype.
    fn pad_front(self, n: usize) -> TickColumn {
        use TickColumn::*;
        match self {
            Empty(m) => Empty(m + n),
            Bool(v) => Bool(std::iter::repeat_n(None, n).chain(v).collect()),
            Int(v) => Int(std::iter::repeat_n(None, n).chain(v).collect()),
            Float(v) => Float(std::iter::repeat_n(None, n).chain(v).collect()),
            Str(v) => Str(std::iter::repeat_n(None, n).chain(v).collect()),
        }
    }

    /// Append `n` trailing nulls.
    fn pad_back(mut self, n: usize) -> TickColumn {
        use TickColumn::*;
        match &mut self {
            Empty(m) => *m += n,
            Bool(v) => v.extend(std::iter::repeat_n(None, n)),
            Int(v) => v.extend(std::iter::repeat_n(None, n)),
            Float(v) => v.extend(std::iter::repeat_n(None, n)),
            Str(v) => v.extend(std::iter::repeat_n(None, n)),
        }
        self
    }

    fn into_floats(self) -> Vec<Option<f64>> {
        match self {
            TickColumn::Empty(n) => vec![None; n],
            TickColumn::Int(v) => v.into_iter().map(|o| o.map(|i| i as f64)).collect(),
            TickColumn::Float(v) => v,
            other => other.into_strs().iter().map(|_| None).collect(),
        }
    }

    fn into_strs(self) -> Vec<Option<String>> {
        match self {
            TickColumn::Empty(n) => vec![None; n],
            TickColumn::Bool(v) => v.into_iter().map(|o| o.map(|b| b.to_string())).collect(),
            TickColumn::Int(v) => v.into_iter().map(|o| o.map(|i| i.to_string())).collect(),
            TickColumn::Float(v) => v.into_iter().map(|o| o.map(|f| f.to_string())).collect(),
            TickColumn::Str(v) => v,
        }
    }
}

/// Integer field values, widened to `i64` (the whole numeric family, since a
/// `ticks` column can mix classes with slightly different integer widths).
fn field_as_int(v: &FieldValue) -> Option<i64> {
    match v {
        FieldValue::I32(x) => Some(*x as i64),
        FieldValue::I64(x) => Some(*x),
        FieldValue::U32(x) => Some(*x as i64),
        FieldValue::U64(x) => Some(*x as i64),
        _ => None,
    }
}

fn field_as_float(v: &FieldValue) -> Option<f64> {
    match v {
        FieldValue::F32(x) => Some(*x as f64),
        _ => None,
    }
}

fn field_as_bool(v: &FieldValue) -> Option<bool> {
    match v {
        FieldValue::Bool(x) => Some(*x),
        _ => None,
    }
}

/// Build a `tick` + per-key DataFrame from a set of game events.
fn events_to_frame(events: &[&GameEvent]) -> PolarsResult<DataFrame> {
    // Collect the union of key names, preserving first-seen order.
    let mut key_order: Vec<String> = Vec::new();
    for e in events {
        for (k, _) in &e.keys {
            if !key_order.iter().any(|existing| existing == k) {
                key_order.push(k.clone());
            }
        }
    }

    let ticks: Vec<i64> = events.iter().map(|e| e.tick as i64).collect();
    let mut columns: Vec<Column> = vec![Column::new("tick".into(), ticks)];

    for key in &key_order {
        let values: Vec<Option<String>> = events
            .iter()
            .map(|e| {
                e.keys
                    .iter()
                    .find(|(k, _)| k == key)
                    .map(|(_, v)| v.clone())
            })
            .collect();
        columns.push(Column::new(key.as_str().into(), values));
    }

    df_from_columns(columns)
}

fn polars_err(e: PolarsError) -> PyErr {
    InvalidDemoError::new_err(format!("dataframe error: {e}"))
}

#[pymodule]
fn _awpy(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Demo>()?;
    m.add_class::<Events>()?;
    m.add_class::<VisibilityChecker>()?;
    m.add_class::<NavMesh>()?;
    m.add_function(wrap_pyfunction!(compute_map_control, m)?)?;
    m.add("InvalidDemoError", m.py().get_type::<InvalidDemoError>())?;
    Ok(())
}
