"""Reference tables for what a demo exposes.

Two lookups, so you can discover what to ask for without parsing first:

- :data:`SNAPSHOT_PROPERTIES` — the per-player features returned by
  :meth:`Demo.snapshots`, each mapped to the CS2 network property (or derivation)
  it comes from.
- :data:`GAME_EVENTS` — common CS2 game events and what they mean. The actual
  events in a given demo are ``demo.events.names`` (and ``demo.events.counts``).
"""

from __future__ import annotations

__all__ = ["GAME_EVENTS", "SNAPSHOT_PROPERTIES"]

SNAPSHOT_PROPERTIES: dict[str, str] = {
    # ── Identity ──
    "steamid": "m_steamID",
    "name": "m_iszPlayerName",
    "side": "m_iTeamNum",  # 2 = terrorist, 3 = counter-terrorist
    # ── Position & aim (world coordinates, Hammer units) ──
    "x": "CBodyComponent.m_cellX + m_vecX (computed)",
    "y": "CBodyComponent.m_cellY + m_vecY (computed)",
    "z": "CBodyComponent.m_cellZ + m_vecZ (computed)",
    "pitch": "m_angEyeAngles[0]",
    "yaw": "m_angEyeAngles[1]",
    # ── Health & armor ──
    "health": "m_iHealth",
    "armor": "m_ArmorValue",
    "has_helmet": "m_pItemServices.m_bHasHelmet",
    "has_defuser": "m_pItemServices.m_bHasDefuser",
    "has_bomb": "m_pWeaponServices.m_hMyWeapons (holds a CC4)",
    # ── Weapons & utility held ──
    "active_weapon": "m_pWeaponServices.m_hActiveWeapon",
    "primary_weapon": "m_pWeaponServices.m_hMyWeapons (primary slot)",
    "secondary_weapon": "m_pWeaponServices.m_hMyWeapons (pistol slot)",
    "fire_grenades": "m_pWeaponServices.m_hMyWeapons (molotov / incendiary)",
    "smoke_grenades": "m_pWeaponServices.m_hMyWeapons (smoke)",
    "he_grenades": "m_pWeaponServices.m_hMyWeapons (HE)",
    "flashbangs": "m_pWeaponServices.m_hMyWeapons (flashbang)",
    "decoy_grenades": "m_pWeaponServices.m_hMyWeapons (decoy)",
    "inventory": "m_pWeaponServices.m_hMyWeapons (full loadout, slot order)",
    # ── Economy ──
    "equipment_value": "m_unCurrentEquipmentValue",
    "equipment_value_round_start": "m_unRoundStartEquipmentValue",
    "money": "m_pInGameMoneyServices.m_iAccount",
    # ── Status ──
    "is_crouched": "m_pMovementServices.m_bDucked",
    "is_walking": "m_bIsWalking",
    "is_jumping": "m_fFlags (FL_ONGROUND clear)",
    "is_in_bomb_zone": "m_bInBombZone",
    "is_scoped": "m_bIsScoped",
    "is_defusing": "m_bIsDefusing",
    "flash_duration": "m_flFlashDuration",
}
"""Per-player snapshot feature name -> the CS2 network property it is read from.

Every key is a column of :meth:`Demo.snapshots` (besides ``tick``), and the value
is the engine property — or the derivation, for computed ones like world
position. The direct fields (``health``, ``money``, the ``is_*`` flags, ...) can
also be passed to :meth:`Demo.ticks`, either by these readable names or by their
raw network names.
"""

GAME_EVENTS: dict[str, str] = {
    # ── Rounds & match ──
    "round_start": "A round begins.",
    "round_freeze_end": "Freeze time ends; players can move.",
    "round_end": "A round is decided (carries winner + reason).",
    "round_officially_ended": "The round is fully wrapped up (post-round).",
    "announce_phase_end": "A phase (e.g. the first half) ends — halftime.",
    "begin_new_match": "A new match starts.",
    "cs_win_panel_match": "The match-end scoreboard is shown.",
    # ── Players ──
    "player_death": "A player is killed (attacker, victim, assister, weapon).",
    "player_hurt": "A player takes damage (health/armor before & after).",
    "player_blind": "A player is blinded by a flashbang.",
    "player_spawn": "A player spawns.",
    "player_team": "A player joins or switches team.",
    "player_connect_full": "A player finishes connecting.",
    "player_disconnect": "A player disconnects.",
    "player_footstep": "A player footstep.",
    "player_jump": "A player jumps.",
    "player_ping": "A player pings a location.",
    # ── Weapons ──
    "weapon_fire": "A weapon is fired (or a grenade thrown).",
    "weapon_reload": "A weapon is reloaded.",
    "weapon_zoom": "A scoped weapon is zoomed.",
    "item_pickup": "A player picks up an item.",
    "item_purchase": "A player buys an item.",
    "item_equip": "A player equips an item.",
    # ── Bomb ──
    "bomb_beginplant": "A player starts planting the bomb.",
    "bomb_planted": "The bomb is planted.",
    "bomb_begindefuse": "A player starts defusing.",
    "bomb_defused": "The bomb is defused.",
    "bomb_exploded": "The bomb explodes.",
    "bomb_dropped": "The bomb is dropped.",
    "bomb_pickup": "The bomb is picked up.",
    # ── Grenades ──
    "flashbang_detonate": "A flashbang detonates.",
    "hegrenade_detonate": "An HE grenade detonates.",
    "smokegrenade_detonate": "A smoke grenade starts its cloud.",
    "smokegrenade_expired": "A smoke cloud dissipates.",
    "decoy_started": "A decoy grenade starts.",
    "decoy_detonate": "A decoy grenade finishes.",
    "inferno_startburn": "A molotov / incendiary fire starts.",
    "inferno_expire": "A fire burns out.",
}
"""Common CS2 game event name -> a one-line description of what it means.

Not exhaustive: a demo may carry events that are not listed here. For what a
*particular* demo contains, use ``demo.events.names`` (or ``demo.events.counts``),
and ``demo.events[name]`` to pull any of them as a DataFrame.
"""
