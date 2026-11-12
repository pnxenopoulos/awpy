"""Predict CS2 round outcomes with the optional ``awpy[win-prob]`` extra."""

import json
import re
from collections.abc import Callable, Sequence
from hashlib import file_digest
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from urllib.parse import quote

import polars as pl

from awpy import data
from awpy._awpy import Demo
from awpy._win_prob_features import (
    BASE_FEATURE_COLUMNS,
    ENEMY_ATTACK,
    FEATURE_COLUMNS,
    SIDES,
    features_at,
    recording_for,
    round_windows,
)

__all__ = ["DEFAULT_MODEL", "ROUND_END_REASONS", "RoundEndModel", "get_model", "load_model"]

DEFAULT_MODEL = "kumo-round-end/v1.0.0"
#: The round-end reasons that the model predicts.
ROUND_END_REASONS = (
    "bomb_defusal",
    "ct_eliminated",
    "t_eliminated",
    "bomb_exploded",
    "time_ran_out",
)
_CT_REASONS = ("bomb_defusal", "t_eliminated", "time_ran_out")
_T_REASONS = ("ct_eliminated", "bomb_exploded")
_REPO = "pnxenopoulos/cs2-win-prob"
_MODEL_ID = re.compile(
    r"kumo-round-end/v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
)
_CONTEXT = "round-end-reason-context.parquet"
_CONTEXT_METADATA = "cs_win_prob.kumo.v1"
_TARGET = "round_end_reason"
_CATEGORICAL = {"map", "phase", "bombsite", _TARGET}
_OUTPUT_SCHEMA = {
    "tick": pl.Int32,
    "round_num": pl.Int32,
    "predicted_round_end_reason": pl.String,
    **dict.fromkeys(ROUND_END_REASONS, pl.Float64),
    "ct_win_probability": pl.Float64,
    "t_win_probability": pl.Float64,
}


def get_model(model: str = DEFAULT_MODEL, *, force: bool = False) -> Path:
    """Download a versioned Kumo context and verify its release checksum.

    Args:
        model: Model ID, for example ``kumo-round-end/v1.0.0``.
        force: If ``True``, download the context also when it is in the cache.

    Returns:
        The path of the context Parquet file in the Awpy cache.

    Raises:
        ValueError: If the ID, manifest, or checksum is not valid.
        FileNotFoundError: If the release or context does not exist.
        OSError: If the download or the cache write fails.
    """
    if not _MODEL_ID.fullmatch(model):
        raise ValueError("expected a model ID such as kumo-round-end/v1.0.0")
    target = data.AWPY_DATA_DIR / "models" / model / _CONTEXT
    if target.is_file() and not force:
        return target
    tag = f"model/{model}"
    url = f"https://github.com/{_REPO}/releases/download/{quote(tag, safe='')}"
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as temp:
        directory = Path(temp)
        try:
            manifest_file = data._download(
                f"{url}/model-manifest.json", directory / "manifest.json"
            )
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            expected = {"schema_version": 1, "tag": tag, "target": _TARGET}
            if not isinstance(manifest, dict) or {k: manifest.get(k) for k in expected} != expected:
                raise ValueError(f"invalid model manifest for {model}")
            assets = manifest.get("assets")
            checksum = assets.get(_CONTEXT) if isinstance(assets, dict) else None
            if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValueError(f"missing context checksum for {model}")
            context = data._download(f"{url}/{_CONTEXT}", directory / _CONTEXT)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"model {model} is unavailable from {_REPO}") from exc
        with context.open("rb") as file:
            if file_digest(file, "sha256").hexdigest() != checksum:
                raise ValueError(f"context checksum mismatch for {model}")
        context.replace(target)
    return target


def _load_scorer(model_id: str, device: str | None) -> Callable[[pl.DataFrame], pl.DataFrame]:
    try:
        torch = import_module("torch")
        sdm = import_module("sdm")
        kumo = import_module("sdm.models").KumoTabular
    except ImportError as exc:
        raise ImportError("install 'awpy[win-prob]' to use Kumo round predictions") from exc

    path = get_model(model_id)
    with path.open("rb") as file:
        metadata = pl.read_parquet_metadata(file)
        if _CONTEXT_METADATA not in metadata:
            raise ValueError(f"missing Kumo context settings in {path}")
        settings = json.loads(metadata[_CONTEXT_METADATA])
        file.seek(0)
        context = pl.read_parquet(file)
    required = {*BASE_FEATURE_COLUMNS, _TARGET}
    if settings.get("target", _TARGET) != _TARGET or not required <= set(context.columns):
        raise ValueError(f"incompatible round-end context in {path}")

    features = [name for name in FEATURE_COLUMNS if name in context.columns]
    model_device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    def to_table(frame: pl.DataFrame) -> Any:
        types = {
            name: "categorical" if name in _CATEGORICAL else "numerical" for name in frame.columns
        }
        return sdm.TableTensor.from_arrow(frame.to_arrow(), stypes=types, device=model_device)

    table = to_table(context.select(*features, _TARGET))
    model = kumo(task="classification", size="small", device=model_device)
    model.fit(
        x=table.drop_columns(_TARGET),
        y=table[_TARGET],
        num_estimators=settings["num_estimators"],
        generator=torch.Generator(device=model_device).manual_seed(settings["seed"] % (1 << 64)),
    )

    def score(states: pl.DataFrame) -> pl.DataFrame:
        query = to_table(states.select(features))
        return cast(pl.DataFrame, pl.from_arrow(model.predict(query).to_arrow()))

    return score


class RoundEndModel:
    """A fitted Kumo context that scores ticks from one or more demos.

    Use :func:`load_model` to load a released context.
    """

    def __init__(self, model_id: str, score: Callable[[pl.DataFrame], pl.DataFrame]) -> None:
        self.model_id = model_id
        self._score = score

    def predict(
        self, demo: Demo, *, ticks: int | Sequence[int] | pl.Series, part: int | None = None
    ) -> pl.DataFrame:
        """Predict the round-end reason and the winning side at exact demo ticks.

        Args:
            demo: CS2 demo to score.
            ticks: One tick or a sequence of ticks in the recording. Each tick
                must be from freeze end to the round decision, inclusive.
            part: Zero-based recording index. Necessary for a multipart demo.

        Returns:
            One row for each requested tick, in input order. The columns are
            ``tick``, ``round_num``, ``predicted_round_end_reason``, one
            probability for each reason in :data:`ROUND_END_REASONS`,
            ``ct_win_probability``, and ``t_win_probability``. Probabilities
            are from 0 to 1.

        Raises:
            ValueError: If a tick is not valid, is not in live play, or has no
                player snapshot.
        """
        recording = recording_for(demo, part)
        requested = [ticks] if isinstance(ticks, int) else list(ticks)
        if any(type(tick) is not int or not 0 <= tick < 2**31 for tick in requested):
            raise ValueError("ticks must be nonnegative 32-bit integers")
        return self._predict(recording, requested)

    def wpa(
        self, demo: Demo, *, round_num: int | None = None, part: int | None = None
    ) -> pl.DataFrame:
        """Calculate player Win Probability Added (WPA) from damage and kills.

        Args:
            demo: CS2 demo to score.
            round_num: Completed round to score. If ``None``, score all
                completed rounds in the recording.
            part: Zero-based recording index. Necessary for a multipart demo.

        Returns:
            The columns ``steamid`` (UInt64) and ``wpa`` (Float64), sorted by
            WPA. WPA is the sum of a player's gains and losses in percentage
            points.

        Raises:
            ValueError: If the recording or the round is not available.

        Notes:
            Compare the predictions at the end of each attack tick and of the
            tick before it. Count each enemy attacker and victim pair one time
            for each tick, also when a hit kills. The pairs that attack for the
            side that gains share the change equally. Add each share to the
            attacker and subtract it from the victim. Both players must have
            Steam IDs. Ignore a tick if one of the two ticks has no player
            snapshot.
        """
        recording = recording_for(demo, part)
        windows = round_windows(recording, round_num)
        recording.load("damages", "kills")
        attacker, victim = pl.col("attacker_steamid"), pl.col("victim_steamid")
        # One row for each enemy attacker and victim pair on each live attack tick.
        # Keep a fixed row order, so that the float sums are the same on each run.
        attacks = (
            pl.concat(
                frame.select("tick", attacker, victim, "attacker_side", "victim_side")
                for frame in (recording.damages, recording.kills)
            )
            .filter(ENEMY_ATTACK, attacker > 0, victim > 0, attacker != victim)
            .unique(maintain_order=True)
            .sort("tick", maintain_order=True)
            .join_asof(windows, left_on="tick", right_on="freeze_end_tick")
            .filter(pl.col("tick").is_between("freeze_end_tick", "end_tick", closed="right"))
        )
        ticks = set(attacks["tick"])
        scores = self._predict(
            recording, sorted(ticks | {tick - 1 for tick in ticks}), allow_missing=True
        )
        # The change in CT win probability from the tick before each attack tick.
        ct_win, swing = pl.col("ct_win_probability"), pl.col("swing")
        swings = scores.join(scores.select(pl.col("tick") + 1, before=ct_win), on="tick").select(
            "tick", swing=ct_win - pl.col("before")
        )
        gains = pl.when(pl.col("attacker_side") == SIDES[0]).then(swing > 0).otherwise(swing < 0)
        credits = attacks.join(swings, on="tick", maintain_order="left").with_columns(
            wpa=pl.when(gains).then(swing.abs() * 100 / gains.sum().over("tick")).otherwise(0.0)
        )
        return (
            pl.concat(
                [
                    credits.select(steamid=attacker, wpa=pl.col("wpa")),
                    credits.select(steamid=victim, wpa=-pl.col("wpa")),
                ]
            )
            .group_by("steamid", maintain_order=True)
            .agg(pl.col("wpa").sum())
            .sort(["wpa", "steamid"], descending=[True, False])
        )

    def _predict(
        self, recording: Demo, ticks: list[int], *, allow_missing: bool = False
    ) -> pl.DataFrame:
        """Score the ticks in input order.

        If ``allow_missing``, omit ticks without a player snapshot. If not, raise
        ``ValueError`` for them.
        """
        if not ticks:
            return pl.DataFrame(schema=_OUTPUT_SCHEMA)
        states = features_at(recording, sorted(set(ticks)))
        if not allow_missing and (missing := set(ticks) - set(states["tick"])):
            raise ValueError(f"no CT or T player snapshot at tick {min(missing)}")
        if states.is_empty():
            return pl.DataFrame(schema=_OUTPUT_SCHEMA)
        scores = pl.concat([self._score(batch) for batch in states.iter_slices(n_rows=256)])
        if scores.height != states.height or not set(scores.columns) <= set(ROUND_END_REASONS):
            raise ValueError("Kumo returned an unexpected round-end probability table")
        # Kumo omits the reasons that are not in the context.
        reasons = scores.select(
            pl.col(name).cast(pl.Float64) if name in scores.columns else pl.lit(0.0).alias(name)
            for name in ROUND_END_REASONS
        )
        predictions = (
            states.select("tick", "round_num")
            .hstack(reasons)
            .with_columns(
                predicted_round_end_reason=pl.concat_list(ROUND_END_REASONS)
                .list.arg_max()
                .replace_strict(dict(enumerate(ROUND_END_REASONS)), return_dtype=pl.String),
                ct_win_probability=pl.sum_horizontal(_CT_REASONS),
                t_win_probability=pl.sum_horizontal(_T_REASONS),
            )
        )
        return (
            pl.DataFrame({"tick": ticks}, schema={"tick": pl.Int32})
            .join(predictions, on="tick", maintain_order="left")
            .select(*_OUTPUT_SCHEMA)
        )


def load_model(model: str = DEFAULT_MODEL, *, device: str | None = None) -> RoundEndModel:
    """Load a round-end model. Download its context if it is not in the cache.

    Args:
        model: Model ID, for example ``kumo-round-end/v1.0.0``.
        device: PyTorch device. The default is CUDA if it is available, or CPU.

    Returns:
        A model that is ready to score ticks. Keep it to use the fitted context
        again.

    Raises:
        ImportError: If the ``awpy[win-prob]`` dependencies are not installed.

    Notes:
        If the pretrained Kumo checkpoint is not in the Hugging Face cache, also
        download the checkpoint.
    """
    return RoundEndModel(model, _load_scorer(model, device))
