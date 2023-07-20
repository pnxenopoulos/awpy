"""This module contains the type definitions for the parsed json structure."""

from dataclasses import dataclass
from typing import Literal, NotRequired, TypeAlias, TypeGuard, final, overload

from typing_extensions import TypedDict


@dataclass
class PlotPosition:
    """Class to store information needed for plotting a position."""

    position: tuple[float, float]
    color: str
    marker: str
    alpha: float | None = None
    size: float | None = None


class MapData(TypedDict):
    """TypedDict that hold information about a map."""

    pos_x: float
    pos_y: float
    scale: float
    z_cutoff: NotRequired[float]


class Chat(TypedDict):
    """Chat holds the matchmaking ranks. Only for MM demos."""

    steamID: int | None
    text: str
    tick: int
    params: list[str] | None  # params for SayText2
    isChat: bool  # true for Chat and variable for SayText(2)
    # Unclear: Seems true for ChatMessages to allchat
    # but false for SayText admin commands to all chat
    isChatAll: bool
    type: str


class Token(TypedDict):
    """TypedDict for token object collection.

    Holding information about player positions in tokenized strings.
    """

    tToken: str
    ctToken: str
    token: str


class Area(TypedDict):
    """TypedDict for area entries in NAV."""

    areaName: str
    northWestX: float
    northWestY: float
    northWestZ: float
    southEastX: float
    southEastY: float
    southEastZ: float


DistanceType = Literal["graph", "geodesic", "euclidean"]
AreaMatrix = dict[str, dict[str, dict[DistanceType, float]]]
PlaceMatrix = dict[
    str,
    dict[
        str,
        dict[
            DistanceType,
            dict[Literal["centroid", "representative_point", "median_dist"], float],
        ],
    ],
]


class MatchPhases(TypedDict):
    """MatchPhases holds lists of when match events occurred."""

    announcementLastRoundHalf: list[int] | None
    announcementFinalRound: list[int] | None
    announcementMatchStarted: list[int] | None
    roundStarted: list[int] | None
    roundEnded: list[int] | None
    roundFreezetimeEnded: list[int] | None
    roundEndedOfficial: list[int] | None
    gameHalfEnded: list[int] | None
    matchStart: list[int] | None
    matchStartedChanged: list[int] | None
    warmupChanged: list[int] | None
    teamSwitch: list[int] | None


class ServerConVar(TypedDict):
    """ServerConVar holds server convars, like round timers and timeouts, etc.

    Not always accurate.
    """

    cashBombDefused: int  # cash_player_bomb_defused
    cashBombPlanted: int  # cash_player_bomb_planted
    cashTeamTWinBomb: int  # cash_team_terrorist_win_bomb
    cashWinDefuse: int  # cash_team_win_by_defusing_bomb
    cashWinTimeRunOut: int  # cash_team_win_by_time_running_out_bomb
    cashWinElimination: int  # cash_team_elimination_bomb_map
    cashPlayerKilledDefault: int  # cash_player_killed_enemy_default
    cashTeamLoserBonus: int  # cash_team_loser_bonus
    cashTeamLoserBonusConsecutive: int  # cash_team_loser_bonus_consecutive_rounds
    roundTime: int  # mp_roundtime
    roundTimeDefuse: int  # mp_roundtime_defuse
    roundRestartDelay: int  # mp_round_restart_delay
    freezeTime: int  # mp_freezetime
    buyTime: int  # mp_buytime
    bombTimer: int  # mp_c4timer
    maxRounds: int  # mp_maxrounds
    timeoutsAllowed: int  # mp_team_timeout_max
    coachingAllowed: int  # sv_coaching_enabled


class ParserOpts(TypedDict):
    """ParserOpts holds the parameters passed to the parser."""

    parseRate: int
    parseFrames: bool
    parseKillFrames: bool
    tradeTime: int
    roundBuyStyle: Literal["hltv", "csgo"]
    damagesRolledUp: bool
    parseChat: bool


ParseRate = Literal[128, 64, 32, 16, 8, 4, 2, 1]

BuyStyle = Literal["hltv", "csgo"]

RoundReturnType = Literal["json", "df"]


@final
class FullParserArgs(TypedDict):
    """TypedDict for total parser **kwargs."""

    parse_rate: ParseRate
    parse_frames: bool
    parse_kill_frames: bool
    trade_time: int
    dmg_rolled: bool
    parse_chat: bool
    buy_style: BuyStyle
    json_indentation: bool


@final
class ParserArgs(TypedDict, total=False):
    """Non total parser **kwargs."""

    parse_rate: ParseRate
    parse_frames: bool
    parse_kill_frames: bool
    trade_time: int
    dmg_rolled: bool
    parse_chat: bool
    buy_style: BuyStyle
    json_indentation: bool


class MMRank(TypedDict):
    """MMRank holds the matchmaking ranks. Only for MM demos."""

    steamID: int
    rankChange: float
    rankOld: str
    rankNew: str
    winCount: int


class ConnectAction(TypedDict):
    """ConnectAction is the act of connecting or disconnecting to the server."""

    tick: int
    action: str
    steamID: int


class Players(TypedDict):
    """Players."""

    playerName: str
    steamID: int


class PlayerTeams(TypedDict):
    """PlayerTeam."""

    teamName: str
    players: list[Players] | None


class GrenadeAction(TypedDict):
    """GrenadeAction events."""

    throwTick: int
    destroyTick: int
    throwSeconds: float
    throwClockTime: str
    destroySeconds: float
    destroyClockTime: str
    throwerSteamID: int
    throwerName: str
    throwerTeam: str
    throwerSide: str
    throwerX: float
    throwerY: float
    throwerZ: float
    grenadeType: str
    grenadeX: float
    grenadeY: float
    grenadeZ: float
    entityId: int


class BombAction(TypedDict):
    """BombAction events."""

    tick: int
    seconds: float
    clockTime: str
    playerSteamID: int | None
    playerName: str | None
    playerTeam: str | None
    playerX: float | None
    playerY: float | None
    playerZ: float | None
    bombAction: str
    bombSite: str | None


class DamageAction(TypedDict):
    """DamageAction events."""

    tick: int
    seconds: float
    clockTime: str
    attackerSteamID: int | None
    attackerName: str | None
    attackerTeam: str | None
    attackerSide: str | None
    attackerX: float | None
    attackerY: float | None
    attackerZ: float | None
    attackerViewX: float | None
    attackerViewY: float | None
    attackerStrafe: bool | None
    victimSteamID: int | None
    victimName: str | None
    victimTeam: str | None
    victimSide: str | None
    victimX: float | None
    victimY: float | None
    victimZ: float | None
    victimViewX: float | None
    victimViewY: float | None
    weapon: str
    weaponClass: str
    hpDamage: int
    hpDamageTaken: int
    armorDamage: int
    armorDamageTaken: int
    hitGroup: str
    isFriendlyFire: bool
    distance: float
    zoomLevel: int | None


class KillAction(TypedDict):
    """KillAction events."""

    tick: int
    seconds: float
    clockTime: str
    attackerSteamID: int | None
    attackerName: str | None
    attackerTeam: str | None
    attackerSide: str | None
    attackerX: float | None
    attackerY: float | None
    attackerZ: float | None
    attackerViewX: float | None
    attackerViewY: float | None
    victimSteamID: int | None
    victimName: str | None
    victimTeam: str | None
    victimSide: str | None
    victimX: float | None
    victimY: float | None
    victimZ: float | None
    victimViewX: float | None
    victimViewY: float | None
    assisterSteamID: int | None
    assisterName: str | None
    assisterTeam: str | None
    assisterSide: str | None
    isSuicide: bool
    isTeamkill: bool
    isWallbang: bool
    penetratedObjects: int
    isFirstKill: bool
    isHeadshot: bool
    victimBlinded: bool
    attackerBlinded: bool
    flashThrowerSteamID: int | None
    flashThrowerName: str | None
    flashThrowerTeam: str | None
    flashThrowerSide: str | None
    noScope: bool
    thruSmoke: bool
    distance: float
    isTrade: bool
    playerTradedName: str | None
    playerTradedTeam: str | None
    playerTradedSteamID: int | None
    playerTradedSide: str | None
    weapon: str
    weaponClass: str


class WeaponFireAction(TypedDict):
    """WeaponFireAction events."""

    tick: int
    seconds: float
    clockTime: str
    playerSteamID: int
    playerName: str
    playerTeam: str
    playerSide: str
    playerX: float
    playerY: float
    playerZ: float
    playerViewX: float
    playerViewY: float
    playerStrafe: bool
    weapon: str
    weaponClass: str
    ammoInMagazine: int
    ammoInReserve: int
    zoomLevel: int


class FlashAction(TypedDict):
    """FlashAction events."""

    tick: int
    seconds: float
    clockTime: str
    attackerSteamID: int
    attackerName: str
    attackerTeam: str
    attackerSide: str
    attackerX: float
    attackerY: float
    attackerZ: float
    attackerViewX: float
    attackerViewY: float
    playerSteamID: int | None
    playerName: str | None
    playerTeam: str | None
    playerSide: str | None
    playerX: float | None
    playerY: float | None
    playerZ: float | None
    playerViewX: float | None
    playerViewY: float | None
    flashDuration: float | None


GameAction = (
    KillAction
    | DamageAction
    | GrenadeAction
    | BombAction
    | WeaponFireAction
    | FlashAction
)

GameActionPlayers = Literal[
    "attacker",
    "victim",
    "assister",
    "flashThrower",
    "playerTraded",
    "player",
    "thrower",
]


class BombInfo(TypedDict):
    """Bomb location."""

    x: float
    y: float
    z: float


class GrenadeInfo(TypedDict):
    """Projectile."""

    projectileType: str
    x: float
    y: float
    z: float


class Fire(TypedDict):
    """Inferno from molly or incend. grenade."""

    uniqueID: int
    x: float
    y: float
    z: float


class WeaponInfo(TypedDict):
    """WeaponInfo contains data on an inventory weapon."""

    weaponName: str
    weaponClass: str
    ammoInMagazine: int
    ammoInReserve: int


class PlayerInfo(TypedDict):
    """PlayerInfo at time t."""

    steamID: int
    name: str
    team: str
    side: str
    x: float
    y: float
    z: float
    eyeX: float
    eyeY: float
    eyeZ: float
    velocityX: float
    velocityY: float
    velocityZ: float
    viewX: float
    viewY: float
    hp: int
    armor: int
    activeWeapon: str
    flashGrenades: int
    smokeGrenades: int
    heGrenades: int
    fireGrenades: int
    totalUtility: int
    lastPlaceName: str
    isAlive: bool
    isBot: bool
    isBlinded: bool
    isAirborne: bool
    isDucking: bool
    isDuckingInProgress: bool
    isUnDuckingInProgress: bool
    isDefusing: bool
    isPlanting: bool
    isReloading: bool
    isInBombZone: bool
    isInBuyZone: bool
    isStanding: bool
    isScoped: bool
    isWalking: bool
    isUnknown: bool
    inventory: list[WeaponInfo] | None
    spotters: list[int] | None
    equipmentValue: int
    equipmentValueFreezetimeEnd: int
    equipmentValueRoundStart: int
    cash: int
    cashSpendThisRound: int
    cashSpendTotal: int
    hasHelmet: bool
    hasDefuse: bool
    hasBomb: bool
    ping: int
    zoomLevel: int


class TeamFrameInfo(TypedDict):
    """TeamFrameInfo at time t."""

    side: str
    teamName: str
    teamEqVal: int
    alivePlayers: int
    totalUtility: int
    players: list[PlayerInfo] | None


class Smoke(TypedDict):
    """Smoke holds current smoke info."""

    grenadeEntityID: int
    startTick: int
    x: float
    y: float
    z: float


class GameFrame(TypedDict):
    """GameFrame (game state at time t)."""

    frameID: int
    globalFrameID: int
    isKillFrame: bool
    tick: int
    seconds: float
    clockTime: str
    t: TeamFrameInfo
    ct: TeamFrameInfo
    bombPlanted: bool
    bombsite: str
    bomb: BombInfo
    projectiles: list[GrenadeInfo] | None
    smokes: list[Smoke] | None
    fires: list[Fire] | None


class GameRound(TypedDict):
    """GameRound contains round info and events."""

    roundNum: int
    isWarmup: bool
    startTick: int
    freezeTimeEndTick: int
    endTick: int
    endOfficialTick: int
    bombPlantTick: int | None
    tScore: int
    ctScore: int
    endTScore: int
    endCTScore: int
    ctTeam: str | None
    tTeam: str | None
    winningSide: str
    winningTeam: str | None
    losingTeam: str | None
    roundEndReason: str
    ctFreezeTimeEndEqVal: int
    ctRoundStartEqVal: int
    ctRoundSpendMoney: int
    ctBuyType: str
    tFreezeTimeEndEqVal: int
    tRoundStartEqVal: int
    tRoundSpendMoney: int
    tBuyType: str
    ctSide: PlayerTeams
    tSide: PlayerTeams
    kills: list[KillAction] | None
    damages: list[DamageAction] | None
    grenades: list[GrenadeAction] | None
    bombEvents: list[BombAction] | None
    weaponFires: list[WeaponFireAction] | None
    flashes: list[FlashAction] | None
    frames: list[GameFrame] | None


GameAction = (
    KillAction
    | DamageAction
    | GrenadeAction
    | BombAction
    | WeaponFireAction
    | FlashAction
    | BombAction
)
GameActionKey = Literal[
    "kills", "damages", "grenades", "bombEvents", "weaponFires", "flashes"
]


class Game(TypedDict):
    """Game is the overall struct that holds the parsed demo data."""

    matchID: str
    clientName: str
    mapName: str
    tickRate: int
    playbackTicks: int
    playbackFramesCount: int
    parsedToFrameIdx: int
    parserParameters: ParserOpts
    serverVars: ServerConVar
    matchPhases: MatchPhases
    matchmakingRanks: list[MMRank] | None
    chatMessages: list[Chat] | None
    playerConnections: list[ConnectAction] | None
    gameRounds: list[GameRound] | None


class PlayerStatistics(TypedDict):
    """Type for the result of awpy.analytics.stats.player_stats."""

    steamID: int
    playerName: str
    teamName: str
    isBot: bool
    totalRounds: int
    kills: int
    deaths: int
    kdr: float
    assists: int
    tradeKills: int
    tradedDeaths: int
    teamKills: int
    suicides: int
    flashAssists: int
    totalDamageGiven: float
    totalDamageTaken: float
    totalTeamDamageGiven: float
    adr: float
    totalShots: int
    shotsHit: int
    accuracy: float
    rating: float
    kast: float
    hs: int
    hsPercent: float
    firstKills: int
    firstDeaths: int
    utilityDamage: float
    smokesThrown: int
    flashesThrown: int
    heThrown: int
    fireThrown: int
    enemiesFlashed: int
    teammatesFlashed: int
    blindTime: float
    plants: int
    defuses: int
    kills0: int
    kills1: int
    kills2: int
    kills3: int
    kills4: int
    kills5: int
    attempts1v1: int
    success1v1: int
    attempts1v2: int
    success1v2: int
    attempts1v3: int
    success1v3: int
    attempts1v4: int
    success1v4: int
    attempts1v5: int
    success1v5: int


class KAST(TypedDict):
    """Type for storing kast information."""

    k: bool
    a: bool
    s: bool
    t: bool


class ClosestArea(TypedDict):
    """TypedDict for closest area object.

    Holding information about the map, the closest area and the distance to that area.
    """

    mapName: str
    areaId: int
    distance: float


class DistanceObject(TypedDict):
    """TypedDict for distance object.

    Holding information about distance type,
    distance and the areas in the path between two points/areas.
    """

    distanceType: str
    distance: float
    areas: list[int]


class RoundStatistics(TypedDict):
    """TypedDict for per round statistics."""

    kast: dict[str, KAST]
    round_kills: dict[str, int]
    is_clutching: set[str | None]
    active_players: set[str]
    players_killed: dict[Literal["CT", "T"], set[str]]


# Type to represent different options for map control minimap plot
MapControlPlotType = Literal["default", "players"]

# Type to represent tile id for navigation tiles.
TileId: TypeAlias = int

# Type to represent player position (list of floats [x, y, z])
PlayerPosition: TypeAlias = list[float]

# Return type for awpy.analytics.map_control._bfs_helper.
# Contains map control values for one team.
# Maps TileId to list of tile map control values.
TeamMapControlValues: TypeAlias = dict[TileId, list[float]]

# Return type for awpy.analytics.map_control.graph_to_tile_neighbors
# Maps TileId to set of neighboring tiles.
TileNeighbors: TypeAlias = dict[TileId, set[int]]


@dataclass
class TileDistanceObject:
    """Dataclass with data for map control tile distance calculations.

    Holds information for distance to source tile and tile_id
    distance is associated with.
    """

    tile_id: TileId
    distance: float


@dataclass
class BFSTileData:
    """Dataclass containing data for tiles during bfs algorithm.

    Holds information for tile_id for tile, current map control
    value, and steps remaining for bfs algorithm
    """

    tile_id: TileId
    map_control_value: float
    steps_left: int


@dataclass
class TeamMetadata:
    """Dataclass containing metadata for one team.

    Holds information for aliver player locations. Can include
    more metadata (utility, bomb location, etc.) in the future
    """

    alive_player_locations: list[PlayerPosition]


@dataclass
class FrameTeamMetadata:
    """Dataclass with metadata on both teams in frame.

    Return type for awpy.analytics.map_control.extract_teams_metadata.
    Holds parsed metadata object (TeamMetadata) for both teams
    """

    t_metadata: TeamMetadata
    ct_metadata: TeamMetadata


@dataclass
class FrameMapControlValues:
    """Dataclass with map control values for both teams in frame.

    Return type for awpy.analytics.map_control.calc_map_control.
    Holds TeamMapControlValues for each team for a certain frame.
    """

    t_values: TeamMapControlValues
    ct_values: TeamMapControlValues


@overload
def other_side(side: Literal["CT"]) -> Literal["T"]:
    ...


@overload
def other_side(side: Literal["T"]) -> Literal["CT"]:
    ...


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
    msg = "side has to be either 'CT' or 'T'"
    raise ValueError(msg)


@overload
def lower_side(side: Literal["CT"]) -> Literal["ct"]:
    ...


@overload
def lower_side(side: Literal["T"]) -> Literal["t"]:
    ...


def lower_side(side: Literal["CT", "T"]) -> Literal["ct", "t"]:
    """Takes a csgo side as input and returns lower cased version.

    Args:
        side (string): A csgo team side (T or CT )

    Returns:
        The lower cased string.

    Raises:
        ValueError: Raises a ValueError if side not neither 'CT' nor 'T'
    """
    if side == "CT":
        return "ct"
    if side == "T":
        return "t"
    msg = "side has to be either 'CT' or 'T'"
    raise ValueError(msg)


@overload
def upper_side(side: Literal["ct"]) -> Literal["CT"]:
    ...


@overload
def upper_side(side: Literal["t"]) -> Literal["T"]:
    ...


def upper_side(side: Literal["ct", "t"]) -> Literal["CT", "T"]:
    """Takes a csgo side as input and returns upper cased version.

    Args:
        side (string): A csgo team side (t or ct )

    Returns:
        The upper cased string.

    Raises:
        ValueError: Raises a ValueError if side not neither 'ct' nor 't'
    """
    if side == "ct":
        return "CT"
    if side == "t":
        return "T"
    msg = "side has to be either 'ct' or 't'"
    raise ValueError(msg)


def is_valid_side(side: str) -> TypeGuard[Literal["CT", "T"]]:
    """TypeGuard for string being CT or T.

    Args:
        side (str): String to type guard

    Returns:
        Whether it is CT or T
    """
    return side in {"CT", "T"}


def proper_player_number(n_players: int, /) -> TypeGuard[Literal[0, 1, 2, 3, 4, 5]]:
    """TypeGuard for int being in range(6).

    Args:
        n_players (int): Int to type guard

    Returns:
        Whether the int is in range(6)
    """
    return n_players in range(6)


@overload
def int_to_string_n_players(n_players: Literal[0]) -> Literal["0"]:
    ...


@overload
def int_to_string_n_players(n_players: Literal[1]) -> Literal["1"]:
    ...


@overload
def int_to_string_n_players(n_players: Literal[2]) -> Literal["2"]:
    ...


@overload
def int_to_string_n_players(n_players: Literal[3]) -> Literal["3"]:
    ...


@overload
def int_to_string_n_players(n_players: Literal[4]) -> Literal["4"]:
    ...


@overload
def int_to_string_n_players(n_players: Literal[5]) -> Literal["5"]:
    ...


def int_to_string_n_players(
    n_players: Literal[0, 1, 2, 3, 4, 5]
) -> Literal["0", "1", "2", "3", "4", "5"]:
    """_Typeguarded conversion from int in range(6) to str.

    Args:
        n_players (Literal[0, 1, 2, 3, 4, 5]): Int to convert to string.

    Raises:
        ValueError: If the int is not in range(6)

    Returns:
        str(n_players)
    """
    if n_players == 0:
        return "0"
    if n_players == 1:
        return "1"
    if n_players == 2:  # noqa: Ruff(PLR2004)
        return "2"
    if n_players == 3:  # noqa: Ruff(PLR2004)
        return "3"
    if n_players == 4:  # noqa: Ruff(PLR2004)
        return "4"
    if n_players == 5:  # noqa: Ruff(PLR2004)
        return "5"
    msg = "n_players has to be in range(6)"
    raise ValueError(msg)
