"""Defines the Round class, which stores a round's parsed data."""

from pydantic import BaseModel

from awpy.parser.enums import RoundEndReason, HitGroup


class Round(BaseModel):
    """Class to store a game round."""

    is_warmup: bool
    start_tick: int
    freeze_end_tick: int
    buy_time_end_tick: int
    end_tick: int
    end_official_tick: int
    bomb_plant_tick: int
    bomb_defuse_tick: int
    round_end_reason: RoundEndReason
    ct_score_start: int
    t_score_start: int
    ct_eq_val: int
    ct_spend: int
    t_eq_val: int
    t_spend: int


class PlayerFrame(BaseModel):
    """Class to store player information for a game frame."""

    name: str
    steam_id: int
    x: float
    y: float
    z: float
    last_place_name: str
    pitch: float
    yaw: float
    is_alive: bool
    health: int
    armor: int
    has_helmet: bool
    has_defuser: bool
    ping: int
    current_eq_val: int
    active_weapon: str
    inventory: list[str]  # should probably be a weapon enum
    rank: int


class TeamFrame(BaseModel):
    """Class to store team information for a game frame."""

    players_alive: int
    eq_val: int
    he: int
    flash: int
    smoke: int
    fire: int
    players: list[PlayerFrame]


class GameFrame(BaseModel):
    """Class to store game frame information."""

    tick: int
    seconds_since_phase_start: float
    seconds_since_round_start: float
    clockTime: str
    t: TeamFrame
    ct: TeamFrame


class Kill(BaseModel):
    """Class to store kill information."""

    tick: int
    flash_assist: bool
    assister_name: str
    assister_steam_id: int
    attacker_name: str
    attacker_steam_id: int
    attacker_blind: bool
    victim_name: str
    victim_steam_id: int
    distance: float
    dmg_armor: int
    dmg_health: int
    domination: bool
    headshot: bool
    hitgroup: HitGroup
    noreplay: bool
    noscope: bool
    penetrated: bool
    revenge: bool
    thrusmoke: bool
    weapon: str


class Damage(BaseModel):
    """Class to store damage information."""

    tick: int
    attacker_name: str
    attacker_steam_id: int
    victim_name: str
    victim_steam_id: int
    dmg_armor: int
    dmg_health: int
    health: int
    armor: int
    weapon: str
