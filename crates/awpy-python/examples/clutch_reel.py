"""Find the match's clutch rounds and render each one as an animated GIF.

Chains three parts of Awpy together:

1. ``demo.stats`` says who played clutches, but not *when* — so the rounds are
   located by replaying each round's kills and finding the moment one side drops
   to a single living player.
2. ``demo.snapshots`` reconstructs everyone's position and health across that
   window.
3. ``awpy.plot.gif`` draws it on the map's radar.

Requires the plot extra: ``pip install 'awpy[plot]'``.

Usage:
    python clutch_reel.py match.dem --out clutches/
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import polars as pl
from awpy import Demo
from awpy.plot import Player, gif

SIDES = ("terrorist", "counter-terrorist")
# One frame per this many ticks. 32 is ~2 frames/second on a 64-tick demo — enough
# to follow a fight without producing a huge GIF.
FRAME_STRIDE = 32


@dataclass
class Clutch:
    """A 1-vs-many situation located in the demo."""

    round_num: int
    tick: int
    """The tick the player was left alone."""
    name: str
    side: str
    opponents: int
    won: bool

    @property
    def label(self) -> str:
        outcome = "won" if self.won else "lost"
        return f"r{self.round_num:02d}-{self.name}-1v{self.opponents}-{outcome}"


def find_clutches(demo: Demo) -> list[Clutch]:
    """Locate every clutch, with the tick it began.

    Walks each round's kills and tracks who is still alive per side. The roster is
    taken from the players who appear anywhere in the round's events plus the
    match roster, so a player who never fires a shot still counts as alive.
    """
    rounds = demo.rounds.filter(~pl.col("is_knife_round")).sort("round_num")
    kills = demo.kills.sort("tick")
    roster = demo.players.filter(pl.col("steamid") > 0)
    names = dict(zip(roster["steamid"], roster["name"], strict=True))

    found: list[Clutch] = []
    for row in rounds.iter_rows(named=True):
        start = row["freeze_end_tick"] or row["start_tick"]
        end = row["official_end_tick"] or row["end_tick"]
        if start is None:
            continue
        in_round = kills.filter((pl.col("tick") >= start) & (pl.col("tick") <= end))

        # Alive per side at the round's start: everyone seen on that side this
        # round, whether they killed, died, or were merely shot at.
        alive: dict[str, set[int]] = {}
        for side in SIDES:
            members = set(
                in_round.filter(pl.col("attacker_side") == side)["attacker_steamid"]
            ) | set(in_round.filter(pl.col("victim_side") == side)["victim_steamid"])
            alive[side] = {m for m in members if m}

        recorded: set[str] = set()
        for kill in in_round.iter_rows(named=True):
            side, victim = kill["victim_side"], kill["victim_steamid"]
            if side not in alive or victim not in alive[side]:
                continue
            alive[side].discard(victim)
            if side in recorded:
                continue
            other = SIDES[1 - SIDES.index(side)]
            # Exactly one left, with enemies still up: a clutch begins here.
            if len(alive[side]) == 1 and alive[other]:
                survivor = next(iter(alive[side]))
                recorded.add(side)
                found.append(
                    Clutch(
                        round_num=row["round_num"],
                        tick=kill["tick"],
                        name=names.get(survivor, str(survivor)),
                        side=side,
                        opponents=len(alive[other]),
                        won=row["winner_side"] == side,
                    )
                )
    return found


def render(demo: Demo, clutch: Clutch, out_dir: Path) -> Path:
    """Draw one clutch from the moment it began to the end of the round."""
    round_row = demo.rounds.filter(pl.col("round_num") == clutch.round_num).row(0, named=True)
    end = round_row["end_tick"]
    snaps = demo.snapshots(every=FRAME_STRIDE, start_tick=clutch.tick, end_tick=end)

    frames = []
    for _, group in snaps.sort("tick").group_by("tick", maintain_order=True):
        frames.append(
            [
                Player(
                    x=r["x"],
                    y=r["y"],
                    z=r["z"],
                    yaw=r["yaw"],
                    hp=r["health"],
                    armor=r["armor"],
                    side=r["side"],
                    label=r["name"],
                    has_bomb=r["has_bomb"],
                )
                for r in group.iter_rows(named=True)
            ]
        )

    path = out_dir / f"{clutch.label}.gif"
    gif(demo.header["map_name"], frames, str(path))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("demo", type=Path, help="path to a .dem file")
    parser.add_argument("--out", type=Path, default=Path("clutches"), help="output directory")
    parser.add_argument(
        "--won-only", action="store_true", help="only render clutches that were won"
    )
    parser.add_argument("--limit", type=int, default=None, help="render at most N clutches")
    args = parser.parse_args()

    demo = Demo(args.demo)
    clutches = find_clutches(demo)
    if args.won_only:
        clutches = [c for c in clutches if c.won]
    if args.limit is not None:
        clutches = clutches[: args.limit]

    print(f"{demo.header['map_name']}: {len(clutches)} clutch situation(s)")
    for c in clutches:
        outcome = "won " if c.won else "lost"
        print(f"  round {c.round_num:>2}  {c.name:<14} 1v{c.opponents}  {outcome}  tick {c.tick}")

    # Cross-check against the aggregate, which counts these independently.
    tallied = int(demo.stats["clutches_played"].sum())
    if not args.won_only and args.limit is None and tallied != len(clutches):
        print(f"  note: demo.stats reports {tallied} — see reference docs on rosters")

    if not clutches:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"\nRendering to {args.out}/ ...")
    for c in clutches:
        print(f"  {render(demo, c, args.out).name}")


if __name__ == "__main__":
    main()
