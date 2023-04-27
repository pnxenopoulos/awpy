"""Functions to calculate statistics for a player or team from a demofile.

    Typical usage example:

    from awpy.parser import DemoParser
    from awpy.analytics.stats import player_stats

    # Create the parser object.
    parser = DemoParser(
        demofile = "astralis-vs-liquid-m2-nuke.dem",
        demo_id = "AST-TL-BLAST2019-nuke",
        parse_frames=False,
    )

    # Parse the demofile, output results to a dictionary of dataframes.
    data = parser.parse()
    player_stats_json = player_stats(data["gameRounds"])
    player_stats_json[76561197999004010]

    https://github.com/pnxenopoulos/awpy/blob/main/examples/01_Basic_CSGO_Analysis.ipynb
"""
from typing import Literal, cast

import pandas as pd

from awpy.types import (
    KAST,
    BombAction,
    DamageAction,
    FlashAction,
    GameRound,
    GrenadeAction,
    KillAction,
    PlayerStatistics,
    RoundStatistics,
    WeaponFireAction,
)


# accuracy
# kast
# adr
# kill stats
# flash stats
# econ stats
def other_side(side: Literal["CT", "T"]) -> Literal["T", "CT"]:
    """Takes a csgo side as input and returns the opposite side in the same formatting.

    Args:
        side (string): A csgo team side (t or ct all upper or all lower case)

    Returns:
        A string of the opposite team side in the same formatting as the input

    Raises:
        ValueError: Raises a ValueError if side not neither 'CT' nor 'T'
    """
    if side == "CT":
        return "T"
    if side == "T":
        return "CT"
    raise ValueError("side has to be either 'CT' or 'T'")


def initialize_round(
    cur_round: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    active_sides: set[Literal["CT", "T"]],
) -> RoundStatistics:
    """Initialize players and statistics for the given round.

    Args:
        cur_round (GameRound): Current CSGO round to initialize for.
        player_statistics (dict[str, PlayerStatistics]):
            Dict storing player statistics for a given match.
        active_sides (set[Literal["CT", "T"]]): Set of the currently active sides.

    Returns:
        dict[str, KAST]: Initialized KAST dict for each player.
        dict[str, int]: Number of kills in the round for each player.
        set[str]]: Players to track for the given round.

    """
    kast: dict[str, KAST] = {}
    round_kills: dict[str, int] = {}
    active_players: set[str] = set()
    for side in [team.lower() + "Side" for team in active_sides]:
        side = cast(Literal["ctSide", "tSide"], side)
        for p in cur_round[side]["players"] or []:
            player_key = p["playerName"] if p["steamID"] == 0 else str(p["steamID"])
            active_players.add(player_key)
            if player_key not in player_statistics:
                player_statistics[player_key] = {
                    "steamID": p["steamID"],
                    "playerName": p["playerName"],
                    "teamName": cur_round[side]["teamName"],
                    "isBot": p["steamID"] == 0,
                    "totalRounds": 0,
                    "kills": 0,
                    "deaths": 0,
                    "kdr": 0,
                    "assists": 0,
                    "tradeKills": 0,
                    "tradedDeaths": 0,
                    "teamKills": 0,
                    "suicides": 0,
                    "flashAssists": 0,
                    "totalDamageGiven": 0,
                    "totalDamageTaken": 0,
                    "totalTeamDamageGiven": 0,
                    "adr": 0,
                    "totalShots": 0,
                    "shotsHit": 0,
                    "accuracy": 0,
                    "rating": 0,
                    "kast": 0,
                    "hs": 0,
                    "hsPercent": 0,
                    "firstKills": 0,
                    "firstDeaths": 0,
                    "utilityDamage": 0,
                    "smokesThrown": 0,
                    "flashesThrown": 0,
                    "heThrown": 0,
                    "fireThrown": 0,
                    "enemiesFlashed": 0,
                    "teammatesFlashed": 0,
                    "blindTime": 0,
                    "plants": 0,
                    "defuses": 0,
                    "kills0": 0,
                    "kills1": 0,
                    "kills2": 0,
                    "kills3": 0,
                    "kills4": 0,
                    "kills5": 0,
                    "attempts1v1": 0,
                    "success1v1": 0,
                    "attempts1v2": 0,
                    "success1v2": 0,
                    "attempts1v3": 0,
                    "success1v3": 0,
                    "attempts1v4": 0,
                    "success1v4": 0,
                    "attempts1v5": 0,
                    "success1v5": 0,
                }
            player_statistics[player_key]["totalRounds"] += 1
    for player_key in active_players:
        kast[player_key] = {"k": False, "a": False, "s": True, "t": False}
        round_kills[player_key] = 0

    # Calculate kills
    players_killed: dict[Literal["CT", "T"], set[str]] = {
        "T": set(),
        "CT": set(),
    }
    is_clutching: set[str | None] = set()
    round_statistics: RoundStatistics = {
        "kast": kast,
        "round_kills": round_kills,
        "is_clutching": is_clutching,
        "active_players": active_players,
        "players_killed": players_killed,
    }
    return round_statistics


def _finalize_statistics(player_statistics: dict[str, PlayerStatistics]) -> None:
    """Finalize player statistics.

    Round some statistics and calculate relative and per round
    based statistics.

    Args:
        player_statistics (dict[str, PlayerStatistics]): Dictionary of player statistics
    """
    for player in player_statistics.values():
        player["kast"] = round(
            100 * player["kast"] / player["totalRounds"],
            1,
        )
        player["blindTime"] = round(player["blindTime"], 2)
        player["kdr"] = round(
            player["kills"] / player["deaths"]
            if player["deaths"] != 0
            else player["kills"],
            2,
        )
        player["adr"] = round(
            player["totalDamageGiven"] / player["totalRounds"],
            1,
        )
        player["accuracy"] = round(
            player["shotsHit"] / player["totalShots"]
            if player["totalShots"] != 0
            else 0,
            2,
        )
        player["hsPercent"] = round(
            player["hs"] / player["kills"] if player["kills"] != 0 else 0,
            2,
        )
        impact = (
            2.13 * (player["kills"] / player["totalRounds"])
            + 0.42 * (player["assists"] / player["totalRounds"])
            - 0.41
        )
        player["rating"] = (
            0.0073 * player["kast"]
            + 0.3591 * (player["kills"] / player["totalRounds"])
            - 0.5329 * (player["deaths"] / player["totalRounds"])
            + 0.2372 * (impact)
            + 0.0032 * (player["adr"])
            + 0.1587
        )
        player["rating"] = round(player["rating"], 2)


def _get_actor_key(
    actor: str,
    game_action: KillAction
    | DamageAction
    | WeaponFireAction
    | FlashAction
    | GrenadeAction
    | BombAction,
) -> str:
    # Mypy can not handle dynamic keys for TypedDicts
    return (
        str(game_action[f"{actor}Name"])  # type: ignore[literal-required]
        if game_action[f"{actor}SteamID"] == 0  # type: ignore[literal-required]
        else str(game_action[f"{actor}SteamID"])  # type: ignore[literal-required]
    )


def _handle_pure_killer_stats(
    killer_key: str,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
    kill_action: KillAction,
) -> None:
    # Purely attacker related stats
    if (
        killer_key in round_statistics["active_players"]
        and kill_action["attackerSteamID"]
    ):
        if not kill_action["isSuicide"] and not kill_action["isTeamkill"]:
            player_statistics[killer_key]["kills"] += 1
            round_statistics["round_kills"][killer_key] += 1
            round_statistics["kast"][killer_key]["k"] = True
        if kill_action["isTeamkill"]:
            player_statistics[killer_key]["teamKills"] += 1
        if kill_action["isHeadshot"]:
            player_statistics[killer_key]["hs"] += 1


def _handle_pure_victim_stats(
    victim_key: str,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
    kill_action: KillAction,
    game_round: GameRound,
) -> None:
    # Purely victim related stats:
    if victim_key in round_statistics["active_players"]:
        player_statistics[victim_key]["deaths"] += 1
        round_statistics["kast"][victim_key]["s"] = False
        if kill_action["isSuicide"]:
            player_statistics[victim_key]["suicides"] += 1
        if (
            # mypy does not understand that after the first part k["victimSide"]
            # is Literal["CT", "T"]
            # and that `k["victimSide"].lower() + "Side"`
            # leads to a Literal["ctSide", "tSide"]
            kill_action["victimSide"]
            and len(
                game_round[kill_action["victimSide"].lower() + "Side"]["players"] or []  # type: ignore[literal-required] # noqa: E501
            )
            - len(round_statistics["players_killed"][kill_action["victimSide"]])  # type: ignore[index] # noqa: E501
            == 1
        ):
            for player in game_round[kill_action["victimSide"].lower() + "Side"]["players"]:  # type: ignore[literal-required] # noqa: E501
                clutcher_key = (
                    str(player["playermName"])
                    if player["steamID"] == 0
                    else str(player["steamID"])
                )
                if (
                    clutcher_key not in round_statistics["players_killed"][kill_action["victimSide"]]  # type: ignore[index] # noqa: E501
                    and clutcher_key not in round_statistics["is_clutching"]
                    and clutcher_key in round_statistics["active_players"]
                ):
                    round_statistics["is_clutching"].add(clutcher_key)
                    enemies_alive = len(
                        game_round[other_side(kill_action["victimSide"]).lower() + "Side"]["players"] or []  # type: ignore[arg-type, literal-required] # noqa: E501
                    ) - len(
                        round_statistics["players_killed"][other_side(kill_action["victimSide"])]  # type: ignore[arg-type] # noqa: E501
                    )
                    if enemies_alive > 0:
                        player_statistics[clutcher_key][
                            f"attempts1v{enemies_alive}"  # type: ignore[literal-required] # noqa: E501
                        ] += 1
                        if game_round["winningSide"] == kill_action["victimSide"]:
                            player_statistics[clutcher_key][
                                f"success1v{enemies_alive}"  # type: ignore[literal-required] # noqa: E501
                            ] += 1


def _handle_trade_stats(
    killer_key: str,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
    kill_action: KillAction,
) -> None:
    if kill_action["isTrade"]:
        # A trade is always onto an enemy
        # If your teammate kills someone and then you kill them
        # -> that is not a trade kill for you
        # If you kill someone and then yourself
        # -> that is not a trade kill for you
        if (
            kill_action["attackerSide"] != kill_action["victimSide"]
            and killer_key in round_statistics["active_players"]
            and kill_action["attackerSteamID"]
        ):
            player_statistics[killer_key]["tradeKills"] += 1
        # Enemies CAN trade your own death
        # If you force an enemy to teamkill their mate after your death
        # -> thats a traded death for you
        # If you force your killer to kill themselves
        # (in their own molo/nade/fall)
        # -> that is a traded death for you
        traded_key = _get_actor_key("playerTraded", kill_action)
        # In most cases the traded player is on the same team as the trader
        # However in the above scenarios the opposite can be the case
        # So it is not enough to know that the trading player and
        # their side is initialized
        if (
            traded_key in round_statistics["active_players"]
            and kill_action["playerTradedSteamID"]
        ):
            round_statistics["kast"][traded_key]["t"] = True
            player_statistics[traded_key]["tradedDeaths"] += 1


def _handle_assists(
    assister_key: str,
    flashthrower_key: str,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
    kill_action: KillAction,
) -> None:
    if (
        kill_action["assisterSteamID"]
        and kill_action["assisterSide"] != kill_action["victimSide"]
        and assister_key in round_statistics["active_players"]
    ):
        player_statistics[assister_key]["assists"] += 1
        round_statistics["kast"][assister_key]["a"] = True
    if (
        kill_action["flashThrowerSteamID"]
        and kill_action["flashThrowerSide"] != kill_action["victimSide"]
        and flashthrower_key in round_statistics["active_players"]
    ):
        player_statistics[flashthrower_key]["flashAssists"] += 1
        round_statistics["kast"][flashthrower_key]["a"] = True


def _handle_first_kill(
    killer_key: str,
    victim_key: str,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
    kill_action: KillAction,
) -> None:
    if kill_action["isFirstKill"] and kill_action["attackerSteamID"]:
        if killer_key in round_statistics["active_players"]:
            player_statistics[killer_key]["firstKills"] += 1
        if victim_key in round_statistics["active_players"]:
            player_statistics[victim_key]["firstDeaths"] += 1


def _handle_kills(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for k in r["kills"] or []:
        killer_key = _get_actor_key("attacker", k)
        victim_key = _get_actor_key("victim", k)
        assister_key = _get_actor_key("assister", k)
        flashthrower_key = _get_actor_key("flashThrower", k)
        if k["victimSide"] in round_statistics["players_killed"]:
            round_statistics["players_killed"][k["victimSide"]].add(victim_key)  # type: ignore[index]  # noqa: E501
        _handle_pure_killer_stats(
            killer_key, player_statistics, round_statistics, kill_action=k
        )
        _handle_pure_victim_stats(
            victim_key, player_statistics, round_statistics, kill_action=k, game_round=r
        )
        _handle_trade_stats(
            killer_key, player_statistics, round_statistics, kill_action=k
        )
        _handle_assists(
            assister_key,
            flashthrower_key,
            player_statistics,
            round_statistics,
            kill_action=k,
        )
        _handle_first_kill(
            killer_key, victim_key, player_statistics, round_statistics, kill_action=k
        )


def _handle_damages(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for d in r["damages"] or []:
        attacker_key = _get_actor_key("attacker", d)
        victim_key = _get_actor_key("victim", d)
        # Purely attacker related stats
        if attacker_key in round_statistics["active_players"] and d["attackerSteamID"]:
            if not d["isFriendlyFire"]:
                player_statistics[attacker_key]["totalDamageGiven"] += d[
                    "hpDamageTaken"
                ]
            else:  # d["isFriendlyFire"]:
                player_statistics[attacker_key]["totalTeamDamageGiven"] += d[
                    "hpDamageTaken"
                ]
            if d["weaponClass"] not in ["Unknown", "Grenade", "Equipment"]:
                player_statistics[attacker_key]["shotsHit"] += 1
            if d["weaponClass"] == "Grenade":
                player_statistics[attacker_key]["utilityDamage"] += d["hpDamageTaken"]
        if d["victimSteamID"] and victim_key in round_statistics["active_players"]:
            player_statistics[victim_key]["totalDamageTaken"] += d["hpDamageTaken"]


def _handle_weapon_fires(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for w in r["weaponFires"] or []:
        fire_key = (
            w["playerName"] if w["playerSteamID"] == 0 else str(w["playerSteamID"])
        )
        if fire_key in round_statistics["active_players"]:
            player_statistics[fire_key]["totalShots"] += 1


def _handle_flashes(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for f in r["flashes"] or []:
        flasher_key = _get_actor_key("attacker", f)
        if f["attackerSteamID"] and flasher_key in round_statistics["active_players"]:
            if f["attackerSide"] == f["playerSide"]:
                player_statistics[flasher_key]["teammatesFlashed"] += 1
            else:
                player_statistics[flasher_key]["enemiesFlashed"] += 1
                player_statistics[flasher_key]["blindTime"] += (
                    0 if f["flashDuration"] is None else f["flashDuration"]
                )


def _handle_grenades(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for g in r["grenades"] or []:
        thrower_key = _get_actor_key("thrower", g)
        if g["throwerSteamID"] and thrower_key in round_statistics["active_players"]:
            if g["grenadeType"] == "Smoke Grenade":
                player_statistics[thrower_key]["smokesThrown"] += 1
            if g["grenadeType"] == "Flashbang":
                player_statistics[thrower_key]["flashesThrown"] += 1
            if g["grenadeType"] == "HE Grenade":
                player_statistics[thrower_key]["heThrown"] += 1
            if g["grenadeType"] in ["Incendiary Grenade", "Molotov"]:
                player_statistics[thrower_key]["fireThrown"] += 1


def _handle_bomb(
    r: GameRound,
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for b in r["bombEvents"] or []:
        player_key = (
            b["playerName"] if b["playerSteamID"] == 0 else str(b["playerSteamID"])
        )
        if b["playerSteamID"] and player_key in round_statistics["active_players"]:
            if b["bombAction"] == "plant":
                player_statistics[player_key]["plants"] += 1
            if b["bombAction"] == "defuse":
                player_statistics[player_key]["defuses"] += 1


def _handle_kast(
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for player, components in round_statistics["kast"].items():
        if player in round_statistics["active_players"] and any(components.values()):
            player_statistics[player]["kast"] += 1


def _handle_multi_kills(
    player_statistics: dict[str, PlayerStatistics],
    round_statistics: RoundStatistics,
) -> None:
    for player, n_kills in round_statistics["round_kills"].items():
        if (
            n_kills in range(6) and player in round_statistics["active_players"]
        ):  # 0, 1, 2, 3, 4, 5
            player_statistics[player][f"kills{n_kills}"] += 1  # type: ignore[literal-required] # noqa: E501


def player_stats(
    game_rounds: list[GameRound], return_type: str = "json", selected_side: str = "all"
) -> dict[str, PlayerStatistics] | pd.DataFrame:
    """Generate a stats summary for a list of game rounds as produced by the DemoParser.

    Args:
        game_rounds (list[GameRound]): List of game rounds as produced by the DemoParser
        return_type (str, optional): Return format ("json" or "df"). Defaults to "json".
        selected_side (str, optional): Which side(s) to consider. Defaults to "all".
            Other options are "CT" and "T"

    Returns:
        Union[dict[str, PlayerStatistics],pd.Dataframe]:
            Dictionary or Dataframe containing player information
    """
    player_statistics: dict[str, PlayerStatistics] = {}

    selected_side = selected_side.upper()
    if selected_side in {"CT", "T"}:
        selected_side = cast(Literal["CT", "T"], selected_side)
        active_sides: set[Literal["CT", "T"]] = {selected_side}
    else:
        active_sides = {"CT", "T"}

    for r in game_rounds:
        # Add players
        round_statistics = initialize_round(r, player_statistics, active_sides)

        _handle_kills(r, player_statistics, round_statistics)
        _handle_damages(r, player_statistics, round_statistics)
        _handle_weapon_fires(r, player_statistics, round_statistics)
        _handle_flashes(r, player_statistics, round_statistics)
        _handle_grenades(r, player_statistics, round_statistics)
        _handle_bomb(r, player_statistics, round_statistics)
        _handle_kast(player_statistics, round_statistics)
        _handle_multi_kills(player_statistics, round_statistics)

    _finalize_statistics(player_statistics)

    if return_type == "df":
        return (
            pd.DataFrame()
            .from_dict(player_statistics, orient="index")
            .reset_index(drop=True)
        )
    return player_statistics
