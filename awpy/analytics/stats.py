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
def player_stats(game_rounds, return_type="json"):
    player_statistics = {}
    for r in game_rounds:
        # Add players
        kast = {}
        for side in ["ctSide", "tSide"]:
            for p in r[side]["players"]:
                if (
                    p["playerName"] if p["steamID"] == 0 else str(p["steamID"])
                ) not in player_statistics:
                    player_statistics[
                        p["playerName"] if p["steamID"] == 0 else str(p["steamID"])
                    ] = {
                        "steamID": p["steamID"],
                        "playerName": p["playerName"],
                        "teamName": r[side]["teamName"],
                        "isBot": True if p["steamID"] == 0 else False,
                        "totalRounds": 0,
                        "kills": 0,
                        "deaths": 0,
                        "kdr": 0,
                        "assists": 0,
                        "tradeKills": 0,
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
                    }
                player_statistics[
                    p["playerName"] if p["steamID"] == 0 else str(p["steamID"])
                ]["totalRounds"] += 1
                kast[p["playerName"] if p["steamID"] == 0 else str(p["steamID"])] = {}
                kast[p["playerName"] if p["steamID"] == 0 else str(p["steamID"])][
                    "k"
                ] = False
                kast[p["playerName"] if p["steamID"] == 0 else str(p["steamID"])][
                    "a"
                ] = False
                kast[p["playerName"] if p["steamID"] == 0 else str(p["steamID"])][
                    "s"
                ] = True
                kast[p["playerName"] if p["steamID"] == 0 else str(p["steamID"])][
                    "t"
                ] = False
        # Calculate kills
        for i, k in enumerate(r["kills"]):
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
            if (
                k["attackerSteamID"]
                and not k["isSuicide"]
                and not k["isTeamkill"]
                and killer_key in player_statistics.keys()
            ):
                player_statistics[killer_key]["kills"] += 1
                kast[killer_key]["k"] = True
            if victim_key in player_statistics.keys():
                player_statistics[victim_key]["deaths"] += 1
                kast[victim_key]["s"] = False
            if (
                k["assisterSteamID"]
                and k["assisterTeam"] != k["victimTeam"]
                and assister_key in player_statistics.keys()
            ):
                player_statistics[assister_key]["assists"] += 1
                kast[assister_key]["a"] = True
            if (
                k["flashThrowerSteamID"]
                and k["flashThrowerTeam"] != k["victimTeam"]
                and flashthrower_key in player_statistics.keys()
            ):
                player_statistics[flashthrower_key]["flashAssists"] += 1
                kast[flashthrower_key]["a"] = True
            if (
                k["isTrade"]
                and k["attackerSteamID"]
                and killer_key in player_statistics.keys()
                and victim_key in player_statistics.keys()
            ):
                player_statistics[killer_key]["tradeKills"] += 1
                kast[
                    str(r["kills"][i - 1]["victimName"])
                    if str(r["kills"][i - 1]["victimSteamID"]) == 0
                    else str(r["kills"][i - 1]["victimSteamID"])
                ]["t"] = True
            if (
                k["isFirstKill"]
                and k["attackerSteamID"]
                and killer_key in player_statistics.keys()
                and victim_key in player_statistics.keys()
            ):
                player_statistics[killer_key]["firstKills"] += 1
                player_statistics[victim_key]["firstDeaths"] += 1
            if (
                k["isTeamkill"]
                and k["attackerSteamID"]
                and killer_key in player_statistics.keys()
            ):
                player_statistics[killer_key]["teamKills"] += 1
            if (
                k["isHeadshot"]
                and k["attackerSteamID"]
                and killer_key in player_statistics.keys()
            ):
                player_statistics[killer_key]["hs"] += 1
            if k["isSuicide"] and victim_key in player_statistics.keys():
                player_statistics[victim_key]["suicides"] += 1
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

            if (
                d["attackerSteamID"]
                and not d["isFriendlyFire"]
                and attacker_key in player_statistics.keys()
            ):
                player_statistics[attacker_key]["totalDamageGiven"] += d[
                    "hpDamageTaken"
                ]
            if d["victimSteamID"] and victim_key in player_statistics.keys():
                player_statistics[victim_key]["totalDamageTaken"] += d["hpDamageTaken"]
            if d["isFriendlyFire"] and attacker_key in player_statistics.keys():
                player_statistics[attacker_key]["totalTeamDamageGiven"] += d[
                    "hpDamageTaken"
                ]
            if (
                d["weaponClass"] not in ["Unknown", "Grenade", "Equipment"]
                and attacker_key in player_statistics.keys()
            ):
                player_statistics[attacker_key]["shotsHit"] += 1
            if (
                d["weaponClass"] == "Grenade"
                and attacker_key in player_statistics.keys()
            ):
                player_statistics[attacker_key]["utilityDamage"] += d["hpDamageTaken"]
        for w in r["weaponFires"]:
            if (
                w["playerName"]
                if w["playerSteamID"] == 0
                else str(w["playerSteamID"]) in player_statistics.keys()
            ):
                player_statistics[
                    w["playerName"]
                    if w["playerSteamID"] == 0
                    else str(w["playerSteamID"])
                ]["totalShots"] += 1
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
            if f["attackerSteamID"] and flasher_key in player_statistics.keys():
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
            if g["throwerSteamID"] and thrower_key in player_statistics.keys():
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
            if b["playerSteamID"] and player_key in player_statistics.keys():
                if b["bombAction"] == "plant":
                    player_statistics[player_key]["plants"] += 1
                if b["bombAction"] == "defuse":
                    player_statistics[player_key]["defuses"] += 1
        for player in kast:
            all_true = False
            for component in kast[player]:
                if kast[player][component]:
                    all_true = True
            if all_true:
                player_statistics[player]["kast"] += 1
    for player in kast:
        player_statistics[player]["kast"] = round(
            100
            * player_statistics[player]["kast"]
            / player_statistics[player]["totalRounds"],
            1,
        )
    for player in player_statistics:
        player_statistics[player]["blindTime"] = round(
            player_statistics[player]["blindTime"], 2
        )
    for player in player_statistics:
        player_statistics[player]["kdr"] = round(
            player_statistics[player]["kills"] / player_statistics[player]["deaths"]
            if player_statistics[player]["deaths"] != 0
            else player_statistics[player]["kills"],
            2,
        )
    for player in player_statistics:
        player_statistics[player]["adr"] = round(
            player_statistics[player]["totalDamageGiven"]
            / player_statistics[player]["totalRounds"],
            1,
        )
    for player in player_statistics:
        player_statistics[player]["accuracy"] = round(
            player_statistics[player]["shotsHit"]
            / player_statistics[player]["totalShots"]
            if player_statistics[player]["totalShots"] != 0
            else 0,
            2,
        )
    for player in player_statistics:
        player_statistics[player]["hsPercent"] = round(
            player_statistics[player]["hs"] / player_statistics[player]["kills"]
            if player_statistics[player]["kills"] != 0
            else 0,
            2,
        )
    for player in player_statistics:
        impact = (
            2.13
            * (
                player_statistics[player]["kills"]
                / player_statistics[player]["totalRounds"]
            )
            + 0.42
            * (
                player_statistics[player]["assists"]
                / player_statistics[player]["totalRounds"]
            )
            - 0.41
        )
        player_statistics[player]["rating"] = (
            0.0073 * player_statistics[player]["kast"]
            + 0.3591
            * (
                player_statistics[player]["kills"]
                / player_statistics[player]["totalRounds"]
            )
            - 0.5329
            * (
                player_statistics[player]["deaths"]
                / player_statistics[player]["totalRounds"]
            )
            + 0.2372 * (impact)
            + 0.0032 * (player_statistics[player]["adr"])
            + 0.1587
        )
        player_statistics[player]["rating"] = round(
            player_statistics[player]["rating"], 2
        )
    if return_type == "df":
        return (
            pd.DataFrame()
            .from_dict(player_statistics, orient="index")
            .reset_index(drop=True)
        )
    else:
        return player_statistics
