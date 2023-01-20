"""This module contains the type definitions for the parsed json structure."""

from typing import Literal, NotRequired, TypedDict

ColsType = Literal[
    "roundNum",
    "startTick",
    "freezeTimeEndTick",
    "endTick",
    "endOfficialTick",
    "tScore",
    "ctScore",
    "endTScore",
    "endCTScore",
    "tTeam",
    "ctTeam",
    "winningSide",
    "winningTeam",
    "losingTeam",
    "roundEndReason",
    "ctFreezeTimeEndEqVal",
    "ctRoundStartEqVal",
    "ctRoundSpendMoney",
    "ctBuyType",
    "tFreezeTimeEndEqVal",
    "tRoundStartEqVal",
    "tRoundSpendMoney",
    "tBuyType",
]


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
    type: str  # noqa: A003


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
    roundBuyStyle: str
    damagesRolledUp: bool
    parseChat: bool


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
    playerSteamID: int
    playerName: str
    playerTeam: str
    playerX: float
    playerY: float
    playerZ: float
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
    isDuck: bool
    isDuckInProgress: bool
    isUnDuckInProgress: bool
    isDefus: bool
    isPlant: bool
    isReload: bool
    isInBombZone: bool
    isInBuyZone: bool
    isStand: bool
    isScoped: bool
    isWalk: bool
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
    p: int
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