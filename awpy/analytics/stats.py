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
import pandas as pd

# accuracy
# kast
# adr
# kill stats
# flash stats
# econ stats
def other_side(side):
    """Takes a csgo side as input and returns the opposite side in the same formatting

    Args:
        side (string): A csgo team side (t or ct all upper or all lower case)

    Returns:
        A string of the opposite team side in the same formatting as the input"""
    other_side_dict = {"CT": "T", "ct": "t", "T": "CT", "t": "ct"}
    return other_side_dict[side]


def player_stats(game_rounds, return_type="json", selected_side="all"):
    player_statistics = {}
    if selected_side.upper() in {"CT", "T"}:
        active_sides = {selected_side.upper()}
    else:
        active_sides = {"CT", "T"}
    for r in game_rounds:
        # Add players
        kast = {}
        round_kills = {}
        for side in [team.lower() + "Side" for team in active_sides]:
            for p in r[side]["players"]:
                player_key = p["playerName"] if p["steamID"] == 0 else str(p["steamID"])
                if player_key not in player_statistics:
                    player_statistics[player_key] = {
                        "steamID": p["steamID"],
                        "playerName": p["playerName"],
                        "teamName": r[side]["teamName"],
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
                        "0kills": 0,
                        "1kills": 0,
                        "2kills": 0,
                        "3kills": 0,
                        "4kills": 0,
                        "5kills": 0,
                        "1v1attempts": 0,
                        "1v1success": 0,
                        "1v2attempts": 0,
                        "1v2success": 0,
                        "1v3attempts": 0,
                        "1v3success": 0,
                        "1v4attempts": 0,
                        "1v4success": 0,
                        "1v5attempts": 0,
                        "1v5success": 0,
                    }
                player_statistics[player_key]["totalRounds"] += 1
                kast[player_key] = {}
                kast[player_key]["k"] = False
                kast[player_key]["a"] = False
                kast[player_key]["s"] = True
                kast[player_key]["t"] = False
                round_kills[player_key] = 0
        # Calculate kills
        players_killed = {"T": set(), "CT": set()}
        is_clutching = set()
        for k in r["kills"]:
            killer_key = (
                str(k["attackerName"])
                if str(k["attackerSteamID"]) == 0
                else str(k["attackerSteamID"])
            )
            victim_key = (
                str(k["victimName"])
                if str(k["victimSteamID"]) == 0
                else str(k["victimSteamID"])
            )
            assister_key = (
                str(k["assisterName"])
                if str(k["assisterSteamID"]) == 0
                else str(k["assisterSteamID"])
            )
            flashthrower_key = (
                str(k["flashThrowerName"])
                if str(k["flashThrowerSteamID"]) == 0
                else str(k["flashThrowerSteamID"])
            )
            players_killed[k["victimSide"]].add(victim_key)
            # Purely attacker related stats
            if (
                k["attackerSide"] in active_sides
                and killer_key in player_statistics
                and k["attackerSteamID"]
            ):
                if not k["isSuicide"] and not k["isTeamkill"]:
                    player_statistics[killer_key]["kills"] += 1
                    round_kills[killer_key] += 1
                    kast[killer_key]["k"] = True
                if k["isTeamkill"]:
                    player_statistics[killer_key]["teamKills"] += 1
                if k["isHeadshot"]:
                    player_statistics[killer_key]["hs"] += 1
            # Purely victim related stats:
            if victim_key in player_statistics and k["victimSide"] in active_sides:
                player_statistics[victim_key]["deaths"] += 1
                kast[victim_key]["s"] = False
                if k["isSuicide"]:
                    player_statistics[victim_key]["suicides"] += 1
            if (
                len(r[k["victimSide"].lower() + "Side"]["players"])
                - len(players_killed[k["victimSide"]])
                == 1
                and k["victimSide"] in active_sides
            ):
                for player in r[k["victimSide"].lower() + "Side"]["players"]:
                    clutcher_key = (
                        str(player["playermName"])
                        if str(player["steamID"]) == 0
                        else str(player["steamID"])
                    )
                    if (
                        clutcher_key not in players_killed[k["victimSide"]]
                        and clutcher_key not in is_clutching
                        and clutcher_key in player_statistics
                    ):
                        is_clutching.add(clutcher_key)
                        enemies_alive = len(
                            r[other_side(k["victimSide"].lower()) + "Side"]["players"]
                        ) - len(players_killed[other_side(k["victimSide"])])
                        if enemies_alive > 0:
                            player_statistics[clutcher_key][
                                f"1v{enemies_alive}attempts"
                            ] += 1
                            if r["winningSide"] == k["victimSide"]:
                                player_statistics[clutcher_key][
                                    f"1v{enemies_alive}success"
                                ] += 1
            if k["isTrade"]:
                # A trade is always onto an enemy
                # If your teammate kills someone and then you kill them
                # -> that is not a trade kill for you
                # If you kill someone and then yourself
                # -> that is not a trade kill for you
                if (
                    k["attackerSide"] != k["victimSide"]
                    and k["attackerSide"] in active_sides
                    and killer_key in player_statistics
                    and k["attackerSteamID"]
                ):
                    player_statistics[killer_key]["tradeKills"] += 1
                # Enemies CAN trade your own death
                # If you force an enemy to teamkill their mate after your death
                # -> thats a traded death for you
                # If you force your killer to kill themselves (in their own molo/nade/fall)
                # -> that is a traded death for you
                traded_key = (
                    k["playerTradedName"]
                    if str(k["playerTradedSteamID"]) == 0
                    else str(k["playerTradedSteamID"])
                )
                # In most cases the traded player is on the same team as the trader
                # However in the above scenarios the opposite can be the case
                # So it is not enough to know that the trading player and
                # their side is initialized
                if (
                    k["playerTradedSide"] in active_sides
                    and traded_key in player_statistics
                    and k["playerTradedSteamID"]
                ):
                    kast[traded_key]["t"] = True
                    player_statistics[traded_key]["tradedDeaths"] += 1
            if (
                k["assisterSteamID"]
                and k["assisterTeam"] != k["victimTeam"]
                and assister_key in player_statistics
                and k["assisterSide"] in active_sides
            ):
                player_statistics[assister_key]["assists"] += 1
                kast[assister_key]["a"] = True
            if (
                k["flashThrowerSteamID"]
                and k["flashThrowerTeam"] != k["victimTeam"]
                and flashthrower_key in player_statistics
                and k["flashThrowerSide"] in active_sides
            ):
                player_statistics[flashthrower_key]["flashAssists"] += 1
                kast[flashthrower_key]["a"] = True

            if k["isFirstKill"] and k["attackerSteamID"]:
                if (
                    k["attackerSide"] in active_sides
                    and killer_key in player_statistics
                ):
                    player_statistics[killer_key]["firstKills"] += 1
                if k["victimSide"] in active_sides and victim_key in player_statistics:
                    player_statistics[victim_key]["firstDeaths"] += 1

        for d in r["damages"]:
            attacker_key = (
                str(d["attackerName"])
                if str(d["attackerSteamID"]) == 0
                else str(d["attackerSteamID"])
            )
            victim_key = (
                str(d["victimName"])
                if str(d["victimSteamID"]) == 0
                else str(d["victimSteamID"])
            )
            # Purely attacker related stats
            if (
                d["attackerSide"] in active_sides
                and attacker_key in player_statistics
                and d["attackerSteamID"]
            ):
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
                    player_statistics[attacker_key]["utilityDamage"] += d[
                        "hpDamageTaken"
                    ]
            if (
                d["victimSteamID"]
                and victim_key in player_statistics
                and d["victimSide"] in active_sides
            ):
                player_statistics[victim_key]["totalDamageTaken"] += d["hpDamageTaken"]

        for w in r["weaponFires"]:
            fire_key = (
                w["playerName"] if w["playerSteamID"] == 0 else str(w["playerSteamID"])
            )
            if fire_key in player_statistics and w["playerSide"] in active_sides:
                player_statistics[fire_key]["totalShots"] += 1
        for f in r["flashes"]:
            flasher_key = (
                str(f["attackerName"])
                if str(f["attackerSteamID"]) == 0
                else str(f["attackerSteamID"])
            )
            player_key = (
                str(f["playerName"])
                if str(f["playerSteamID"]) == 0
                else str(f["playerSteamID"])
            )
            if (
                f["attackerSteamID"]
                and flasher_key in player_statistics
                and f["attackerSide"] in active_sides
            ):
                if f["attackerSide"] == f["playerSide"]:
                    player_statistics[flasher_key]["teammatesFlashed"] += 1
                else:
                    player_statistics[flasher_key]["enemiesFlashed"] += 1
                    player_statistics[flasher_key]["blindTime"] += f["flashDuration"]
        for g in r["grenades"]:
            thrower_key = (
                g["throwerName"]
                if g["throwerSteamID"] == 0
                else str(g["throwerSteamID"])
            )
            if (
                g["throwerSteamID"]
                and thrower_key in player_statistics
                and g["throwerSide"] in active_sides
            ):
                if g["grenadeType"] == "Smoke Grenade":
                    player_statistics[thrower_key]["smokesThrown"] += 1
                if g["grenadeType"] == "Flashbang":
                    player_statistics[thrower_key]["flashesThrown"] += 1
                if g["grenadeType"] == "HE Grenade":
                    player_statistics[thrower_key]["heThrown"] += 1
                if g["grenadeType"] in ["Incendiary Grenade", "Molotov"]:
                    player_statistics[thrower_key]["fireThrown"] += 1
        for b in r["bombEvents"]:
            player_key = (
                b["playerName"] if b["playerSteamID"] == 0 else str(b["playerSteamID"])
            )
            if b["playerSteamID"] and player_key in player_statistics:
                if b["bombAction"] == "plant" and "T" in active_sides:
                    player_statistics[player_key]["plants"] += 1
                if b["bombAction"] == "defuse" and "CT" in active_sides:
                    player_statistics[player_key]["defuses"] += 1
        for player, components in kast.items():
            if any(components.values()):
                player_statistics[player]["kast"] += 1
        for player, n_kills in round_kills.items():
            player_statistics[player][f"{n_kills}kills"] += 1

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

    if return_type == "df":
        return (
            pd.DataFrame()
            .from_dict(player_statistics, orient="index")
            .reset_index(drop=True)
        )
    else:
        return player_statistics
