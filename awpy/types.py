"""This module contains the type definitions for the parsed json structure"""

from typing import Optional, TypedDict, Literal


class Token(TypedDict):
    """TypedDict for token object collection information about player positions
    into tokenized strings."""

    tToken: str
    ctToken: str
    token: str


class Area(TypedDict):
    """TypedDict for area entries in NAV"""

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
    """MatchPhases holds lists of when match events occurred"""

    announcementLastRoundHalf: Optional[list[int]]
    announcementFinalRound: Optional[list[int]]
    announcementMatchStarted: Optional[list[int]]
    roundStarted: Optional[list[int]]
    roundEnded: Optional[list[int]]
    roundFreezetimeEnded: Optional[list[int]]
    roundEndedOfficial: Optional[list[int]]
    gameHalfEnded: Optional[list[int]]
    matchStart: Optional[list[int]]
    matchStartedChanged: Optional[list[int]]
    warmupChanged: Optional[list[int]]
    teamSwitch: Optional[list[int]]


class ServerConVar(TypedDict):
    """ServerConVar holds server convars, like round timers and timeouts, etc. Not always accurate."""

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
    """ParserOpts holds the parameters passed to the parser"""

    parseRate: int
    parseFrames: bool
    parseKillFrames: bool
    tradeTime: int
    roundBuyStyle: str
    damagesRolledUp: bool


class MMRank(TypedDict):
    """MMRank holds the matchmaking ranks. Only for MM demos."""

    steamID: int
    rankChange: float
    rankOld: str
    rankNew: str
    winCount: int


class ConnectAction(TypedDict):
    """ConnectAction is the act of connecting or disconnecting to the server"""

    tick: int
    action: str
    steamID: int


class Players(TypedDict):
    """Players"""

    playerName: str
    steamID: int


class PlayerTeams(TypedDict):
    """PlayerTeam"""

    teamName: str
    players: Optional[list[Players]]


class GrenadeAction(TypedDict):
    """GrenadeAction events"""

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
    """BombAction events"""

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
    bombSite: Optional[str]


class DamageAction(TypedDict):
    """DamageAction events"""

    tick: int
    seconds: float
    clockTime: str
    attackerSteamID: Optional[int]
    attackerName: Optional[str]
    attackerTeam: Optional[str]
    attackerSide: Optional[str]
    attackerX: Optional[float]
    attackerY: Optional[float]
    attackerZ: Optional[float]
    attackerViewX: Optional[float]
    attackerViewY: Optional[float]
    attackerStrafe: Optional[bool]
    victimSteamID: Optional[int]
    victimName: Optional[str]
    victimTeam: Optional[str]
    victimSide: Optional[str]
    victimX: Optional[float]
    victimY: Optional[float]
    victimZ: Optional[float]
    victimViewX: Optional[float]
    victimViewY: Optional[float]
    weapon: str
    weaponClass: str
    hpDamage: int
    hpDamageTaken: int
    armorDamage: int
    armorDamageTaken: int
    hitGroup: str
    isFriendlyFire: bool
    distance: float
    zoomLevel: Optional[int]


class KillAction(TypedDict):
    """KillAction events"""

    tick: int
    seconds: float
    clockTime: str
    attackerSteamID: Optional[int]
    attackerName: Optional[str]
    attackerTeam: Optional[str]
    attackerSide: Optional[str]
    attackerX: Optional[float]
    attackerY: Optional[float]
    attackerZ: Optional[float]
    attackerViewX: Optional[float]
    attackerViewY: Optional[float]
    victimSteamID: Optional[int]
    victimName: Optional[str]
    victimTeam: Optional[str]
    victimSide: Optional[str]
    victimX: Optional[float]
    victimY: Optional[float]
    victimZ: Optional[float]
    victimViewX: Optional[float]
    victimViewY: Optional[float]
    assisterSteamID: Optional[int]
    assisterName: Optional[str]
    assisterTeam: Optional[str]
    assisterSide: Optional[str]
    isSuicide: bool
    isTeamkill: bool
    isWallbang: bool
    penetratedObjects: int
    isFirstKill: bool
    isHeadshot: bool
    victimBlinded: bool
    attackerBlinded: bool
    flashThrowerSteamID: Optional[int]
    flashThrowerName: Optional[str]
    flashThrowerTeam: Optional[str]
    flashThrowerSide: Optional[str]
    noScope: bool
    thruSmoke: bool
    distance: float
    isTrade: bool
    playerTradedName: Optional[str]
    playerTradedTeam: Optional[str]
    playerTradedSteamID: Optional[int]
    playerTradedSide: Optional[str]
    weapon: str
    weaponClass: str


class WeaponFireAction(TypedDict):
    """WeaponFireAction events"""

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
    """FlashAction events"""

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
    playerSteamID: Optional[int]
    playerName: Optional[str]
    playerTeam: Optional[str]
    playerSide: Optional[str]
    playerX: Optional[float]
    playerY: Optional[float]
    playerZ: Optional[float]
    playerViewX: Optional[float]
    playerViewY: Optional[float]
    flashDuration: Optional[float]


class BombInfo(TypedDict):
    """Bomb location"""

    x: float
    y: float
    z: float


class GrenadeInfo(TypedDict):
    """Projectile"""

    projectileType: str
    x: float
    y: float
    z: float


class Fire(TypedDict):
    """Inferno from molly or incend. grenade"""

    uniqueID: int
    x: float
    y: float
    z: float


class WeaponInfo(TypedDict):
    """WeaponInfo contains data on an inventory weapon"""

    weaponName: str
    weaponClass: str
    ammoInMagazine: int
    ammoInReserve: int


class PlayerInfo(TypedDict):
    """PlayerInfo at time t"""

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
    inventory: Optional[list[WeaponInfo]]
    spotters: Optional[list[int]]
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
    """TeamFrameInfo at time t"""

    side: str
    teamName: str
    teamEqVal: int
    alivePlayers: int
    totalUtility: int
    players: Optional[list[PlayerInfo]]


class Smoke(TypedDict):
    """Smoke holds current smoke info"""

    grenadeEntityID: int
    startTick: int
    x: float
    y: float
    z: float


class GameFrame(TypedDict):
    """GameFrame (game state at time t)"""

    isKillFrame: bool
    tick: int
    seconds: float
    clockTime: str
    t: TeamFrameInfo
    ct: TeamFrameInfo
    bombPlanted: bool
    bombsite: str
    bomb: BombInfo
    projectiles: Optional[list[GrenadeInfo]]
    smokes: Optional[list[Smoke]]
    fires: Optional[list[Fire]]


class GameRound(TypedDict):
    """GameRound contains round info and events"""

    roundNum: int
    isWarmup: bool
    startTick: int
    freezeTimeEndTick: int
    endTick: int
    endOfficialTick: int
    bombPlantTick: Optional[int]
    tScore: int
    ctScore: int
    endTScore: int
    endCTScore: int
    ctTeam: Optional[str]
    tTeam: Optional[str]
    winningSide: str
    winningTeam: Optional[str]
    losingTeam: Optional[str]
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
    kills: Optional[list[KillAction]]
    damages: Optional[list[DamageAction]]
    grenades: Optional[list[GrenadeAction]]
    bombEvents: Optional[list[BombAction]]
    weaponFires: Optional[list[WeaponFireAction]]
    flashes: Optional[list[FlashAction]]
    frames: Optional[list[GameFrame]]


class Game(TypedDict):
    """Game is the overall struct that holds the parsed demo data"""

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
    matchmakingRanks: Optional[list[MMRank]]
    playerConnections: Optional[list[ConnectAction]]
    gameRounds: Optional[list[GameRound]]


class PlayerStatistics(TypedDict):
    """Type for the result of awpy.analytics.stats.player_stats"""

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
