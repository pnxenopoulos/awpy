"""Enum used for event types."""

from enum import Enum


class GameEvent(Enum):
    """GameEvents as defined by demoparser2."""

    # Bomb-related Events
    BOMB_PLANTED = "bomb_planted"
    BOMB_DEFUSED = "bomb_defused"
    BOMB_DROPPED = "bomb_dropped"
    BOMB_BEGINPLANT = "bomb_beginplant"
    BOMB_EXPLODED = "bomb_exploded"
    BOMB_PICKUP = "bomb_pickup"
    BOMB_BEGINDEFUSE = "bomb_begindefuse"
    # Round-related Events
    ROUND_PRESTART = "round_prestart"
    ROUND_START = "round_start"
    ROUND_FREEZE_END = "round_freeze_end"
    ROUND_POSTSTART = "round_poststart"
    BUYTIME_ENDED = "buytime_ended"
    ROUND_TIME_WARNING = "round_time_warning"
    ROUND_END = "round_end"
    ROUND_OFFICIALLY_ENDED = "round_officially_ended"
    # Grenades Events
    DECOY_STARTED = "decoy_started"
    DECOY_DETONATE = "decoy_detonate"
    FLASHBANG_DETONATE = "flashbang_detonate"
    HEGRENADE_DETONATE = "hegrenade_detonate"
    INFERNO_STARTBURN = "inferno_startburn"
    INFERNO_EXPIRE = "inferno_expire"
    SMOKEGRENADE_DETONATE = "smokegrenade_detonate"
    SMOKEGRENADE_EXPIRED = "smokegrenade_expired"
    # Player Activities
    PLAYER_HURT = "player_hurt"
    PLAYER_JUMP = "player_jump"
    PLAYER_FOOTSTEP = "player_footstep"
    PLAYER_CONNECT = "player_connect"
    PLAYER_DEATH = "player_death"
    PLAYER_DISCONNECT = "player_disconnect"
    ITEM_PICKUP = "item_pickup"
    PLAYER_TEAM = "player_team"
    WEAPON_ZOOM = "weapon_zoom"
    PLAYER_BLIND = "player_blind"
    PLAYER_SPAWN = "player_spawn"
    WEAPON_FIRE = "weapon_fire"
    WEAPON_RELOAD = "weapon_reload"
    PLAYER_CONNECT_FULL = "player_connect_full"
    ITEM_EQUIP = "item_equip"
    # HLTV Events
    HLTV_FIXED = "hltv_fixed"
    HLTV_CHASE = "hltv_chase"
    # Announcements
    ROUND_ANNOUNCE_LAST_ROUND_HALF = "round_announce_last_round_half"
    ANNOUNCE_PHASE_END = "announce_phase_end"
    ROUND_ANNOUNCE_MATCH_START = "round_announce_match_start"
    ROUND_ANNOUNCE_MATCH_POINT = "round_announce_match_point"
    # Miscellaneous Events
    BEGIN_NEW_MATCH = "begin_new_match"
    CS_WIN_PANEL_ROUND = "cs_win_panel_round"
    RANK_UPDATE = "rank_update"
    OTHER_DEATH = "other_death"
    ROUND_MVP = "round_mvp"
    CS_WIN_PANEL_MATCH = "cs_win_panel_match"
    CS_ROUND_START_BEEP = "cs_round_start_beep"
    CS_ROUND_FINAL_BEEP = "cs_round_final_beep"
    CS_PRE_RESTART = "cs_pre_restart"
