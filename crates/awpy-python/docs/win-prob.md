# Predict CS2 round outcomes with Awpy

```python
from awpy import Demo, win_prob

demo = Demo("match.dem")
tick = demo.rounds["freeze_end_tick"].drop_nulls()[0]
model = win_prob.load_model("kumo-round-end/v1.0.0")
scores = model.predict(demo, ticks=tick)
print(scores.select("predicted_round_end_reason", "ct_win_probability", "t_win_probability"))
```

## Install Kumo inference for Awpy

```sh
uv add 'awpy[win-prob]'
# Or
pip install 'awpy[win-prob]'
```

Awpy reads the player snapshots of a CS2 demo into Polars. NVIDIA KumoTabular
and PyTorch then score the snapshots. The model context is an asset of the
[cs2-win-prob release](https://github.com/pnxenopoulos/cs2-win-prob/releases/tag/model%2Fkumo-round-end%2Fv1.0.0).

## Download a versioned Awpy win probability model

```sh
awpy models get kumo-round-end/v1.0.0
```

Awpy verifies the checksum of the context and keeps the context in
`~/.awpy/models/`. To change the cache root, set `AWPY_DATA_DIR`.

If the context is not in the cache, `load_model()` downloads it. If the
pretrained Kumo checkpoint is not in the Hugging Face cache, `load_model()`
also downloads the checkpoint.

## Score exact CS2 replay ticks with Awpy

Give one tick, a sequence of ticks, or a Polars Series. Each tick must be from
freeze end to the round decision. A tick without a CT or T player snapshot
causes an error. For a multipart demo, set `part` to the zero-based recording
index.

The result has one row for each requested tick, in input order. It has the
columns `tick`, `round_num`, and `predicted_round_end_reason`, and one
probability for each reason:

- `bomb_defusal`
- `ct_eliminated`
- `t_eliminated`
- `bomb_exploded`
- `time_ran_out`

`ct_win_probability` is the sum of `bomb_defusal`, `t_eliminated`, and
`time_ran_out`. `t_win_probability` is the sum of `ct_eliminated` and
`bomb_exploded`.

`load_model()` fits the context, and this takes time. Keep the model and use it
again for all your queries. To use only the CPU, set `device="cpu"`.

## Plot CT win probability through a CS2 round

```python
from awpy import Demo, plot

demo = Demo("match.dem")
fig, ax = plot.round_win_probability(
    demo, 1, model="kumo-round-end/v1.0.0", title="Pistol Round"
)
fig.savefig("round-win.png")
```

Install `awpy[win-prob,plot]` for this plot. The line is CT blue above 50% and
T gold below 50%. The default title is `Round <round_num> | <file name>`.

Awpy scores the round one time each second, and at each kill, plant, and the
round decision. To change the interval, set `step_seconds`. A solid red line
shows each completed plant. A dot shows each enemy kill in the color of the
victim's team. If both teams lose a player on the same tick, the dot is half
blue and half gold. For a multipart demo, set `part`.

If you give a model ID, Awpy loads the model for each plot. To make more than
one plot, load the model one time and give the loaded model.

## Calculate player Win Probability Added with Awpy

```python
from awpy import Demo, win_prob

demo = Demo("match.dem")
model = win_prob.load_model("kumo-round-end/v1.0.0")
print(model.wpa(demo, round_num=1))
```

WPA is the sum of the gains and losses of a player, in percentage points. For
example, the CT win probability goes from 40% to 50% on a tick. On that tick,
one CT player damages one T player. The attacker gets +10 and the victim gets
−10.

To score all completed rounds, do not set `round_num`. For a multipart demo,
set `part`. To add WPA to a scoreboard, join on `steamid`.

Awpy compares the predictions at the end of each attack tick and at the end of
the tick before it. A hit and a kill by the same pair on the same tick count
one time. If more than one pair attacks for the side that gains, the pairs
share the change equally. The pairs that attack for the other side get zero
for that tick.

Both players in a pair must have a Steam ID. The attack tick and the tick
before it must have player snapshots in the same live round. Awpy ignores team
damage and events without an attacker or a victim. WPA uses the change for the
full tick, so other events on the same tick also have an effect on it.
