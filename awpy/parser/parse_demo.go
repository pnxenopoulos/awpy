package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"math"
	"os"
	"strconv"
	"strings"

	dem "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs"
	common "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/common"
	events "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/events"
)

// Game is the overall struct that holds the parsed demo data
type Game struct {
	MatchName      string          `json:"matchID"`
	ClientName     string          `json:"clientName"`
	Map            string          `json:"mapName"`
	TickRate       int64           `json:"tickRate"`
	PlaybackTicks  int64           `json:"playbackTicks"`
	PlaybackFrames int64           `json:"playbackFramesCount"`
	ParsedToFrame  int64           `json:"parsedToFrameIdx"`
	ParsingOpts    ParserOpts      `json:"parserParameters"`
	ServerVars     ServerConVar    `json:"serverVars"`
	MatchPhases    MatchPhases     `json:"matchPhases"`
	MMRanks        []MMRank        `json:"matchmakingRanks"`
	Connections    []ConnectAction `json:"playerConnections"`
	Rounds         []GameRound     `json:"gameRounds"`
}

// ParserOpts holds the parameters passed to the parser
type ParserOpts struct {
	ParseRate       int    `json:"parseRate"`
	ParseFrames     bool   `json:"parseFrames"`
	ParseKillFrames bool   `json:"parseKillFrames"`
	TradeTime       int64  `json:"tradeTime"`
	RoundBuyStyle   string `json:"roundBuyStyle"`
	DamagesRolled   bool   `json:"damagesRolledUp"`
}

// MatchPhases holds lists of when match events occurred
type MatchPhases struct {
	AnnLastRoundHalf      []int64 `json:"announcementLastRoundHalf"`
	AnnFinalRound         []int64 `json:"announcementFinalRound"`
	AnnMatchStarted       []int64 `json:"announcementMatchStarted"`
	RoundStarted          []int64 `json:"roundStarted"`
	RoundEnded            []int64 `json:"roundEnded"`
	RoundFreezeEnded      []int64 `json:"roundFreezetimeEnded"`
	RoundEndedOfficial    []int64 `json:"roundEndedOfficial"`
	GameHalfEnded         []int64 `json:"gameHalfEnded"`
	MatchStart            []int64 `json:"matchStart"`
	MatchStartedChanged   []int64 `json:"matchStartedChanged"`
	WarmupChanged         []int64 `json:"warmupChanged"`
	TeamSwitch            []int64 `json:"teamSwitch"`
}

// ServerConVar holds server convars, like round timers and timeouts, etc. Not always accurate.
type ServerConVar struct {
	CashBombDefused               int64 `json:"cashBombDefused"`               // cash_player_bomb_defused
	CashBombPlanted               int64 `json:"cashBombPlanted"`               // cash_player_bomb_planted
	CashWinBomb                   int64 `json:"cashTeamTWinBomb"`              // cash_team_terrorist_win_bomb
	CashWinDefuse                 int64 `json:"cashWinDefuse"`                 // cash_team_win_by_defusing_bomb
	CashWinTimeRunOut             int64 `json:"cashWinTimeRunOut"`             // cash_team_win_by_time_running_out_bomb
	CashWinElimination            int64 `json:"cashWinElimination"`            // cash_team_elimination_bomb_map
	CashPlayerKilledDefault       int64 `json:"cashPlayerKilledDefault"`       // cash_player_killed_enemy_default
	CashTeamLoserBonus            int64 `json:"cashTeamLoserBonus"`            // cash_team_loser_bonus
	CashTeamLoserBonusConsecutive int64 `json:"cashTeamLoserBonusConsecutive"` // cash_team_loser_bonus_consecutive_rounds
	RoundTime                     int64 `json:"roundTime"`                     // mp_roundtime
	RoundTimeDefuse               int64 `json:"roundTimeDefuse"`               // mp_roundtime_defuse
	RoundRestartDelay             int64 `json:"roundRestartDelay"`             // mp_round_restart_delay
	FreezeTime                    int64 `json:"freezeTime"`                    // mp_freezetime
	BuyTime                       int64 `json:"buyTime"`                       // mp_buytime
	BombTimer                     int64 `json:"bombTimer"`                     // mp_c4timer
	MaxRounds                     int64 `json:"maxRounds"`                     // mp_maxrounds
	TimeoutsAllowed               int64 `json:"timeoutsAllowed"`               // mp_team_timeout_max
	CoachingAllowed               int64 `json:"coachingAllowed"`               // sv_coaching_enabled
}

// MMRank holds the matchmaking ranks. Only for MM demos.
type MMRank struct {
	SteamID    uint64  `json:"steamID"`
	RankChange float32 `json:"rankChange"`
	RankOld    string  `json:"rankOld"`
	RankNew    string  `json:"rankNew"`
	WinCount   int     `json:"winCount"`
}

// ConnectAction is the act of connecting or disconnecting to the server
type ConnectAction struct {
	Tick        int64  `json:"tick"`
	ConnectType string `json:"action"`
	SteamID     uint64 `json:"steamID"`
}

// GameRound contains round info and events
type GameRound struct {
	RoundNum             int64              `json:"roundNum"`
	IsWarmup             bool               `json:"isWarmup"`
	StartTick            int64              `json:"startTick"`
	FreezeTimeEndTick    int64              `json:"freezeTimeEndTick"`
	EndTick              int64              `json:"endTick"`
	EndOfficialTick      int64              `json:"endOfficialTick"`
	BombPlantTick        *int64             `json:"bombPlantTick"`
	TScore               int64              `json:"tScore"`
	CTScore              int64              `json:"ctScore"`
	EndTScore            int64              `json:"endTScore"`
	EndCTScore           int64              `json:"endCTScore"`
	CTTeam               *string            `json:"ctTeam"`
	TTeam                *string            `json:"tTeam"`
	WinningSide          string             `json:"winningSide"`
	WinningTeam          *string            `json:"winningTeam"`
	LosingTeam           *string            `json:"losingTeam"`
	Reason               string             `json:"roundEndReason"`
	CTFreezeTimeEndEqVal int64              `json:"ctFreezeTimeEndEqVal"`
	CTRoundStartEqVal    int64              `json:"ctRoundStartEqVal"`
	CTRoundMoneySpend    int64              `json:"ctRoundSpendMoney"`
	CTBuyType            string             `json:"ctBuyType"`
	TFreezeTimeEndEqVal  int64              `json:"tFreezeTimeEndEqVal"`
	TRoundStartEqVal     int64              `json:"tRoundStartEqVal"`
	TRoundMoneySpend     int64              `json:"tRoundSpendMoney"`
	TBuyType             string             `json:"tBuyType"`
	CTSide               PlayerTeams        `json:"ctSide"`
	TSide                PlayerTeams        `json:"tSide"`
	Kills                []KillAction       `json:"kills"`
	Damages              []DamageAction     `json:"damages"`
	Grenades             []GrenadeAction    `json:"grenades"`
	Bomb                 []BombAction       `json:"bombEvents"`
	WeaponFires          []WeaponFireAction `json:"weaponFires"`
	Flashes              []FlashAction      `json:"flashes"`
	Frames               []GameFrame        `json:"frames"`
}

// PlayerTeam
type PlayerTeams struct {
	TeamName string     `json:"teamName"`
	Players  []Players  `json:"players"`
}

// Players
type Players struct {
	PlayerName string `json:"playerName"`
	SteamID    int64  `json:"steamID"`
}

// GrenadeAction events
type GrenadeAction struct {
	ThrowTick         int64   `json:"throwTick"`
	DestroyTick       int64   `json:"destroyTick"`
	ThrowSecond       float64 `json:"throwSeconds"`
	ThrowClockTime    string  `json:"throwClockTime"`
	DestroySecond     float64 `json:"destroySeconds"`
	DestroyClockTime  string  `json:"destroyClockTime"`
	ThrowerSteamID    int64   `json:"throwerSteamID"`
	ThrowerName       string  `json:"throwerName"`
	ThrowerTeam       string  `json:"throwerTeam"`
	ThrowerSide       string  `json:"throwerSide"`
	ThrowerX          float64 `json:"throwerX"`
	ThrowerY          float64 `json:"throwerY"`
	ThrowerZ          float64 `json:"throwerZ"`
	Grenade           string  `json:"grenadeType"`
	GrenadeX          float64 `json:"grenadeX"`
	GrenadeY          float64 `json:"grenadeY"`
	GrenadeZ          float64 `json:"grenadeZ"`
	UniqueID          int64   `json:"entityId"`
}

// BombAction events
type BombAction struct {
	Tick          int64   `json:"tick"`
	Second        float64 `json:"seconds"`
	ClockTime     string  `json:"clockTime"`
	PlayerSteamID int64   `json:"playerSteamID"`
	PlayerName    string  `json:"playerName"`
	PlayerTeam    string  `json:"playerTeam"`
	PlayerX       float64 `json:"playerX"`
	PlayerY       float64 `json:"playerY"`
	PlayerZ       float64 `json:"playerZ"`
	BombAction    string  `json:"bombAction"`
	BombSite      *string `json:"bombSite"`
}

// DamageAction events
type DamageAction struct {
	Tick             int64    `json:"tick"`
	Second           float64  `json:"seconds"`
	ClockTime        string   `json:"clockTime"`
	AttackerSteamID  *int64   `json:"attackerSteamID"`
	AttackerName     *string  `json:"attackerName"`
	AttackerTeam     *string  `json:"attackerTeam"`
	AttackerSide     *string  `json:"attackerSide"`
	AttackerX        *float64 `json:"attackerX"`
	AttackerY        *float64 `json:"attackerY"`
	AttackerZ        *float64 `json:"attackerZ"`
	AttackerViewX    *float64 `json:"attackerViewX"`
	AttackerViewY    *float64 `json:"attackerViewY"`
	AttackerStrafe   *bool    `json:"attackerStrafe"`
	VictimSteamID    *int64   `json:"victimSteamID"`
	VictimName       *string  `json:"victimName"`
	VictimTeam       *string  `json:"victimTeam"`
	VictimSide       *string  `json:"victimSide"`
	VictimX          *float64 `json:"victimX"`
	VictimY          *float64 `json:"victimY"`
	VictimZ          *float64 `json:"victimZ"`
	VictimViewX      *float64 `json:"victimViewX"`
	VictimViewY      *float64 `json:"victimViewY"`
	Weapon           string   `json:"weapon"`
	WeaponClass      string   `json:"weaponClass"`
	HpDamage         int64    `json:"hpDamage"`
	HpDamageTaken    int64    `json:"hpDamageTaken"`
	ArmorDamage      int64    `json:"armorDamage"`
	ArmorDamageTaken int64    `json:"armorDamageTaken"`
	HitGroup         string   `json:"hitGroup"`
	IsTeamDmg        bool     `json:"isFriendlyFire"`
	Distance         float64  `json:"distance"`
	ZoomLevel        *int64   `json:"zoomLevel"`
}

// KillAction events
type KillAction struct {
	Tick                int64    `json:"tick"`
	Second              float64  `json:"seconds"`
	ClockTime           string   `json:"clockTime"`
	AttackerSteamID     *int64   `json:"attackerSteamID"`
	AttackerName        *string  `json:"attackerName"`
	AttackerTeam        *string  `json:"attackerTeam"`
	AttackerSide        *string  `json:"attackerSide"`
	AttackerX           *float64 `json:"attackerX"`
	AttackerY           *float64 `json:"attackerY"`
	AttackerZ           *float64 `json:"attackerZ"`
	AttackerViewX       *float64 `json:"attackerViewX"`
	AttackerViewY       *float64 `json:"attackerViewY"`
	VictimSteamID       *int64   `json:"victimSteamID"`
	VictimName          *string  `json:"victimName"`
	VictimTeam          *string  `json:"victimTeam"`
	VictimSide          *string  `json:"victimSide"`
	VictimX             *float64 `json:"victimX"`
	VictimY             *float64 `json:"victimY"`
	VictimZ             *float64 `json:"victimZ"`
	VictimViewX         *float64 `json:"victimViewX"`
	VictimViewY         *float64 `json:"victimViewY"`
	AssisterSteamID     *int64   `json:"assisterSteamID"`
	AssisterName        *string  `json:"assisterName"`
	AssisterTeam        *string  `json:"assisterTeam"`
	AssisterSide        *string  `json:"assisterSide"`
	IsSuicide           bool     `json:"isSuicide"`
	IsTeamkill          bool     `json:"isTeamkill"`
	IsWallbang          bool     `json:"isWallbang"`
	PenetratedObjects   int64    `json:"penetratedObjects"`
	IsFirstKill         bool     `json:"isFirstKill"`
	IsHeadshot          bool     `json:"isHeadshot"`
	VictimBlinded       bool     `json:"victimBlinded"`
	AttackerBlinded     bool     `json:"attackerBlinded"`
	FlashThrowerSteamID *int64   `json:"flashThrowerSteamID"`
	FlashThrowerName    *string  `json:"flashThrowerName"`
	FlashThrowerTeam    *string  `json:"flashThrowerTeam"`
	FlashThrowerSide    *string  `json:"flashThrowerSide"`
	NoScope             bool     `json:"noScope"`
	ThruSmoke           bool     `json:"thruSmoke"`
	Distance            float64  `json:"distance"`
	IsTrade             bool     `json:"isTrade"`
	PlayerTradedName    *string  `json:"playerTradedName"`
	PlayerTradedTeam    *string  `json:"playerTradedTeam"`
	PlayerTradedSteamID *int64   `json:"playerTradedSteamID"`
	Weapon              string   `json:"weapon"`
	WeaponClass         string   `json:"weaponClass"`
}

// WeaponFireAction events
type WeaponFireAction struct {
	Tick           int64   `json:"tick"`
	Second         float64 `json:"seconds"`
	ClockTime      string  `json:"clockTime"`
	PlayerSteamID  int64   `json:"playerSteamID"`
	PlayerName     string  `json:"playerName"`
	PlayerTeam     string  `json:"playerTeam"`
	PlayerSide     string  `json:"playerSide"`
	PlayerX        float64 `json:"playerX"`
	PlayerY        float64 `json:"playerY"`
	PlayerZ        float64 `json:"playerZ"`
	PlayerViewX    float64 `json:"playerViewX"`
	PlayerViewY    float64 `json:"playerViewY"`
	PlayerStrafe   bool    `json:"playerStrafe"`
	Weapon         string  `json:"weapon"`
	WeaponClass    string  `json:"weaponClass"`
	AmmoInMagazine int64   `json:"ammoInMagazine"`
	AmmoInReserve  int64   `json:"ammoInReserve"`
	ZoomLevel      int64   `json:"zoomLevel"`
}

// FlashAction events
type FlashAction struct {
	Tick             int64    `json:"tick"`
	Second           float64  `json:"seconds"`
	ClockTime        string   `json:"clockTime"`
	AttackerSteamID  int64    `json:"attackerSteamID"`
	AttackerName     string   `json:"attackerName"`
	AttackerTeam     string   `json:"attackerTeam"`
	AttackerSide     string   `json:"attackerSide"`
	AttackerX        float64  `json:"attackerX"`
	AttackerY        float64  `json:"attackerY"`
	AttackerZ        float64  `json:"attackerZ"`
	AttackerViewX    float64  `json:"attackerViewX"`
	AttackerViewY    float64  `json:"attackerViewY"`
	PlayerSteamID    *int64   `json:"playerSteamID"`
	PlayerName       *string  `json:"playerName"`
	PlayerTeam       *string  `json:"playerTeam"`
	PlayerSide       *string  `json:"playerSide"`
	PlayerX          *float64 `json:"playerX"`
	PlayerY          *float64 `json:"playerY"`
	PlayerZ          *float64 `json:"playerZ"`
	PlayerViewX      *float64 `json:"playerViewX"`
	PlayerViewY      *float64 `json:"playerViewY"`
	FlashDuration    *float64 `json:"flashDuration"`
}

// GameFrame (game state at time t)
type GameFrame struct {
	IsKillFrame bool          `json:"isKillFrame"`
	Tick        int64         `json:"tick"`
	Second      float64       `json:"seconds"`
	ClockTime   string        `json:"clockTime"`
	T           TeamFrameInfo `json:"t"`
	CT          TeamFrameInfo `json:"ct"`
	BombPlanted bool          `json:"bombPlanted"`
	BombSite    string        `json:"bombsite"`
	Bomb        BombInfo      `json:"bomb"`
	Projectiles []GrenadeInfo `json:"projectiles"`
	Smokes      []Smoke       `json:"smokes"`
	Fires       []Fire        `json:"fires"`
}

// Bomb location
type BombInfo struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	Z float64 `json:"z"`
}

// Projectile
type GrenadeInfo struct {
	ProjectileType  string  `json:"projectileType"`
	X               float64 `json:"x"`
	Y               float64 `json:"y"`
	Z               float64 `json:"z"`
}

// Inferno from molly or incend. grenade
type Fire struct {
	UniqueID      int64   `json:"uniqueID"`
	X             float64 `json:"x"`
	Y             float64 `json:"y"`
	Z             float64 `json:"z"`
}

// TeamFrameInfo at time t
type TeamFrameInfo struct {
	Side         string       `json:"side"`
	Team         string       `json:"teamName"`
	CurrentEqVal int64        `json:"teamEqVal"`
	AlivePlayers int64        `json:"alivePlayers"`
	TotalUtility int64        `json:"totalUtility"`
	Players      []PlayerInfo `json:"players"`
}

// PlayerInfo at time t
type PlayerInfo struct {
	PlayerSteamID   int64        `json:"steamID"`
	PlayerName      string       `json:"name"`
	PlayerTeam      string       `json:"team"`
	PlayerSide      string       `json:"side"`
	X               float64      `json:"x"`
	Y               float64      `json:"y"`
	Z               float64      `json:"z"`
	VelX            float64      `json:"velocityX"`
	VelY            float64      `json:"velocityY"`
	VelZ            float64      `json:"velocityZ"`
	ViewX           float64      `json:"viewX"`
	ViewY           float64      `json:"viewY"`
	Hp              int64        `json:"hp"`
	Armor           int64        `json:"armor"`
	ActiveWeapon    string       `json:"activeWeapon"`
	TotalUtility    int64        `json:"totalUtility"`
	IsAlive         bool         `json:"isAlive"`
	IsBlinded       bool         `json:"isBlinded"`
	IsAirborne      bool         `json:"isAirborne"`
	IsDucking       bool         `json:"isDucking"`
	IsDuckingInProg bool         `json:"isDuckingInProgress"`
	IsUnducking     bool         `json:"isUnDuckingInProgress"`
	IsDefusing      bool         `json:"isDefusing"`
	IsPlanting      bool         `json:"isPlanting"`
	IsReloading     bool         `json:"isReloading"`
	IsInBombZone    bool         `json:"isInBombZone"`
	IsInBuyZone     bool         `json:"isInBuyZone"`
	IsStanding      bool         `json:"isStanding"`
	IsScoped        bool         `json:"isScoped"`
	IsWalking       bool         `json:"isWalking"`
	IsUnknown       bool         `json:"isUnknown"`
	Inventory       []WeaponInfo `json:"inventory"`
	Spotters        []int64      `json:"spotters"`
	EqVal           int64        `json:"equipmentValue"`
	EqValFreeze     int64        `json:"equipmentValueFreezetimeEnd"`
	EqValStart      int64        `json:"equipmentValueRoundStart"`
	Money           int64        `json:"cash"`
	MoneySpentRound int64        `json:"cashSpendThisRound"`
	MoneySpentTotal int64        `json:"cashSpendTotal"`
	HasHelmet       bool         `json:"hasHelmet"`
	HasDefuse       bool         `json:"hasDefuse"`
	HasBomb         bool         `json:"hasBomb"`
	Ping            int64        `json:"ping"`
	ZoomLevel       int64        `json:"zoomLevel"`
}

// WeaponInfo contains data on an inventory weapon
type WeaponInfo struct {
	WeaponName     string `json:"weaponName"`
	WeaponClass    string `json:"weaponClass"`
	AmmoInMagazine int64  `json:"ammoInMagazine"`
	AmmoInReserve  int64  `json:"ammoInReserve"`
}

// Smoke holds current smoke info
type Smoke struct {
	GrenadeEntityID int64   `json:"grenadeEntityID"`
	StartTick       int64   `json:"startTick"`
	X               float64 `json:"x"`
	Y               float64 `json:"y"`
	Z               float64 `json:"z"`
}

func convertRank(r int) string {
	switch rank := r; rank {
	case -1:
		return "Expired"
	case 0:
		return "Unranked"
	case 1:
		return "Silver 1"
	case 2:
		return "Silver 2"
	case 3:
		return "Silver 3"
	case 4:
		return "Silver 4"
	case 5:
		return "Silver Elite"
	case 6:
		return "Silver Elite Master"
	case 7:
		return "Gold Nova 1"
	case 8:
		return "Gold Nova 2"
	case 9:
		return "Gold Nova 3"
	case 10:
		return "Gold Nova Master"
	case 11:
		return "Master Guardian 1"
	case 12:
		return "Master Guardian 2"
	case 13:
		return "Master Guardian Elite"
	case 14:
		return "Distinguished Master Guardian"
	case 15:
		return "Legendary Eagle"
	case 16:
		return "Legendary Eagle Master"
	case 17:
		return "Supreme Master First Class"
	case 18:
		return "The Global Elite"
	default:
		return "Unranked"
	}
}

func convertRoundEndReason(r events.RoundEndReason) string {
	switch reason := r; reason {
	case 1:
		return "TargetBombed"
	case 2:
		return "VIPEscaped"
	case 3:
		return "VIPKilled"
	case 4:
		return "TerroristsEscaped"
	case 5:
		return "CTStoppedEscape"
	case 6:
		return "TerroristsStopped"
	case 7:
		return "BombDefused"
	case 8:
		return "CTWin"
	case 9:
		return "TerroristsWin"
	case 10:
		return "Draw"
	case 11:
		return "HostagesRescued"
	case 12:
		return "TargetSaved"
	case 13:
		return "HostagesNotRescued"
	case 14:
		return "TerroristsNotEscaped"
	case 15:
		return "VIPNotEscaped"
	case 16:
		return "GameStart"
	case 17:
		return "TerroristsSurrender"
	case 18:
		return "CTSurrender"
	default:
		return "Unknown"
	}
}

func convertHitGroup(hg events.HitGroup) string {
	switch hitGroup := hg; hitGroup {
	case 0:
		return "Generic"
	case 1:
		return "Head"
	case 2:
		return "Chest"
	case 3:
		return "Stomach"
	case 4:
		return "LeftArm"
	case 5:
		return "RightArm"
	case 6:
		return "LeftLeg"
	case 7:
		return "RightLeg"
    case 8:
		return "Neck"   
	case 10:
		return "Gear"
	default:
		return "Unknown"
	}
}

func convertWeaponClass(wc common.EquipmentClass) string {
	switch weaponClass := wc; weaponClass {
	case 0:
		return "Unknown"
	case 1:
		return "Pistols"
	case 2:
		return "SMG"
	case 3:
		return "Heavy"
	case 4:
		return "Rifle"
	case 5:
		return "Equipment"
	case 6:
		return "Grenade"
	default:
		return "Unknown"
	}
}	

func determineSecond(tick int64, currentRound GameRound, currentGame Game) float64 {
	roundTime := currentGame.ServerVars.RoundTime

	if tick <= 0 {
		return float64(0)
	}

	if roundTime == 0 {
		roundTime = currentGame.ServerVars.RoundTimeDefuse
	}

	var phaseEndTick int64
	if currentRound.BombPlantTick == nil {
		phaseEndTick = currentRound.FreezeTimeEndTick
	} else {
		phaseEndTick = *currentRound.BombPlantTick
	}
	return float64((float64(tick) - float64(phaseEndTick)) / float64(currentGame.TickRate))
}

func formatTimeNumber(num int64) string {
	if num < 10 {
		return "0" + fmt.Sprint(num)
	} else {
		return fmt.Sprint(num)
	}
}

func calculateClocktime(tick int64, currentRound GameRound, currentGame Game) string {
	roundTime := currentGame.ServerVars.RoundTime

	if tick <= 0 {
		return "00:00"
	}

	if roundTime == 0 {
		roundTime = currentGame.ServerVars.RoundTimeDefuse
	}

	var seconds_remaining float64
	var phaseEndTick int64
	if currentRound.BombPlantTick == nil {
		phaseEndTick = currentRound.FreezeTimeEndTick
		seconds_remaining = 115 - (float64((float64(tick) - float64(phaseEndTick)) / float64(currentGame.TickRate)))
	} else {
		phaseEndTick = *currentRound.BombPlantTick
		seconds_remaining = 40 - (float64((float64(tick) - float64(phaseEndTick)) / float64(currentGame.TickRate)))
	}
	minutes := int64(math.Floor((seconds_remaining/60)))
	seconds := int64(math.Ceil((seconds_remaining - 60*float64(minutes))))
	
	if (minutes < 0) || (seconds < 0) {
		return "00:00"
	}

	return formatTimeNumber(minutes) + ":" + formatTimeNumber(seconds)
}

func playerInList(p *common.Player, players []PlayerInfo) bool {
	if len(players) > 0 {
		for _, i := range players {
			if int64(p.SteamID64) == i.PlayerSteamID {
				return true
			}
		}
	} else {
		return false
	}
	return false
}

func parsePlayer(gs dem.GameState, p *common.Player) PlayerInfo {
	currentPlayer := PlayerInfo{}
	currentPlayer.PlayerSteamID = int64(p.SteamID64)
	currentPlayer.PlayerName = p.Name
	if (p.TeamState != nil) {
		currentPlayer.PlayerTeam = p.TeamState.ClanName()
	}

	switch p.Team {
	case common.TeamTerrorists:
		currentPlayer.PlayerSide = "T"
	case common.TeamCounterTerrorists:
		currentPlayer.PlayerSide = "CT"
	default:
		currentPlayer.PlayerSide = "Unknown"
	}

	playerPos := p.LastAlivePosition
	playerVel := p.Velocity()

	// Calc other metrics
	currentPlayer.X = float64(playerPos.X)
	currentPlayer.Y = float64(playerPos.Y)
	currentPlayer.Z = float64(playerPos.Z)
	currentPlayer.VelX = float64(playerVel.X)
	currentPlayer.VelY = float64(playerVel.Y)
	currentPlayer.VelZ = float64(playerVel.Z)
	currentPlayer.ViewX = float64(p.ViewDirectionX())
	currentPlayer.ViewY = float64(p.ViewDirectionY())
	currentPlayer.Hp = int64(p.Health())
	currentPlayer.Armor = int64(p.Armor())
	currentPlayer.IsAlive = p.IsAlive()
	currentPlayer.IsBlinded = p.IsBlinded()
	currentPlayer.IsAirborne = p.IsAirborne()
	currentPlayer.IsDefusing = p.IsDefusing
	currentPlayer.IsPlanting = p.IsPlanting
	currentPlayer.IsReloading = p.IsReloading
	currentPlayer.IsDuckingInProg = p.IsDuckingInProgress()
	currentPlayer.IsUnducking = p.IsUnDuckingInProgress()
	currentPlayer.IsDucking = p.IsDucking()
	currentPlayer.IsInBombZone = p.IsInBombZone()
	currentPlayer.IsInBuyZone = p.IsInBuyZone()
	currentPlayer.IsStanding = p.IsStanding()
	currentPlayer.IsScoped = p.IsScoped()
	currentPlayer.IsWalking = p.IsWalking()
	currentPlayer.IsUnknown = p.IsUnknown
	currentPlayer.HasDefuse = p.HasDefuseKit()
	currentPlayer.HasHelmet = p.HasHelmet()
	currentPlayer.Money = int64(p.Money())
	currentPlayer.MoneySpentRound = int64(p.MoneySpentThisRound())
	currentPlayer.MoneySpentTotal = int64(p.MoneySpentTotal())
	currentPlayer.EqVal = int64(p.EquipmentValueCurrent())
	currentPlayer.EqValFreeze = int64(p.EquipmentValueFreezeTimeEnd())
	currentPlayer.EqValStart = int64(p.EquipmentValueRoundStart())
	currentPlayer.Ping = int64(p.Ping())
	currentPlayer.TotalUtility = int64(0)
	activeWeapon := ""

	if (p.IsAlive()) && (p.ActiveWeapon() != nil) {
		activeWeapon = p.ActiveWeapon().String()
		currentPlayer.ZoomLevel = int64(p.ActiveWeapon().ZoomLevel())
	}

	// Determine spotted players
	spottedPlayers := make([]int64, 0)
	spottedOtherPlayer := false
	for _, player := range gs.TeamCounterTerrorists().Members() {
		spottedOtherPlayer = p.HasSpotted(player)
		if spottedOtherPlayer {
			spottedPlayers = append(spottedPlayers, int64(player.SteamID64))
		}
		spottedOtherPlayer = false
	}
	for _, player := range gs.TeamTerrorists().Members() {
		spottedOtherPlayer = p.HasSpotted(player)
		if spottedOtherPlayer {
			spottedPlayers = append(spottedPlayers, int64(player.SteamID64))
		}
		spottedOtherPlayer = false
	}
	currentPlayer.Spotters = spottedPlayers

	currentPlayer.ActiveWeapon = activeWeapon
	currentPlayer.HasBomb = false
	for _, w := range p.Weapons() {
		if w != nil {
			if (w.String() != "Knife") && (w.String() != "C4") {
				// Can't drop the knife
				currentWeapon := WeaponInfo{}
	
				currentWeapon.WeaponName = w.String()
				currentWeapon.WeaponClass = convertWeaponClass(w.Class())
				currentWeapon.AmmoInMagazine = int64(w.AmmoInMagazine())
				currentWeapon.AmmoInReserve = int64(w.AmmoReserve())
	
				//currentPlayer.Inventory = append(currentPlayer.Inventory, w.String())
				currentPlayer.Inventory = append(currentPlayer.Inventory, currentWeapon)
				if w.Class() == 6 {
					currentPlayer.TotalUtility = currentPlayer.TotalUtility + 1
				}
			}
	
			if (w.String() == "C4") {
				currentPlayer.HasBomb = true
			}
		}
	}
	return currentPlayer
}

func parseTeamBuy(eqVal int64, Side string, Style string) string {
	if Style == "hltv" {
		// Taken from hltv economy tab
		if eqVal < 5000 {
			return "Full Eco"
		} else if (eqVal >= 5000) && (eqVal < 10000) {
			return "Semi Eco"
		} else if (eqVal >= 10000) && (eqVal < 20000) {
			return "Semi Buy"
		} else if eqVal >= 20000 {
			return "Full Buy"
		} else {
			return 	"Unknown"
		}
	} else if Style == "csgo" {
		// Created this using 4100 and 3700 as armor+gun for CT and T
		if Side == "CT" {
			if eqVal < 2000 {
				return "Full Eco"
			} else if (eqVal >= 2000) && (eqVal < 6000) {
				return "Eco"
			} else if (eqVal >= 6000) && (eqVal < 22000) {
				return "Half Buy"
			} else if eqVal >= 22000 {
				return "Full Buy"
			} else {
				return "Unknown"
			}
		} else {
			if eqVal < 2000 {
				return "Full Eco"
			} else if (eqVal >= 2000) && (eqVal < 6000) {
				return "Eco"
			} else if (eqVal >= 6000) && (eqVal < 18500) {
				return "Half Buy"
			} else if eqVal >= 18500 {
				return "Full Buy"
			} else {
				return "Unknown"
			}
		}
	} else {
		// Default to hltv style
		return parseTeamBuy(eqVal, Side, "hltv")
	}
}

func acceptableGamePhase(gs dem.GameState) bool {
	warmup := gs.IsWarmupPeriod()
	if warmup == false {
		return true
	}
	return false
}

func isTrade(killA KillAction, killB KillAction, tickRate int64, tradeTime int64) bool {
	// First, identify is killA has a killer. If there is no killer, there cannot be a trade
	if killA.AttackerSteamID == nil {
		return false
	} else {
		// If the the previous killer is not the person killed, it is not a trade
		if killB.VictimSteamID != nil {
			if *killB.VictimSteamID == *killA.AttackerSteamID {
				if (killB.Tick - killA.Tick) <= tradeTime*tickRate {
					return true
				}
				return false
			}
		}
		return false
	}
}

func countAlivePlayers(players []PlayerInfo) int64 {
	var alivePlayers int64
	alivePlayers = 0
	for _, p := range players {
		if p.IsAlive {
			alivePlayers = alivePlayers + 1
		}
	}
	return alivePlayers
}

func countUtility(players []PlayerInfo) int64 {
	var totalUtility int64
	totalUtility = 0
	for _, p := range players {
		if p.IsAlive {
			totalUtility = totalUtility + p.TotalUtility
		}
	}
	return totalUtility
}

func sumPlayerEqVal(players []PlayerInfo) int64 {
	var totalEqVal int64
	totalEqVal = 0
	for _, p := range players {
		if p.IsAlive {
			totalEqVal = totalEqVal + p.EqVal
		}
	}
	return totalEqVal
}

func findIdx(sl []string, val string) int {
	for p, v := range sl {
		if v == val {
			return p
		}
	}
	return -1
}

// Define cleaning functions
func cleanMapName(mapName string) string {
	lastSlash := strings.LastIndex(mapName, "/")
	if lastSlash == -1 {
		return mapName
	}
	return mapName[lastSlash+1 : len(mapName)]
}

func stringInSlice(a string, list []string) bool {
    for _, b := range list {
        if b == a {
            return true
        }
    }
    return false
}

func removeExpiredSmoke(s []Smoke, i int) []Smoke {
    s[i] = s[len(s)-1]
    return s[:len(s)-1]
}

// Main
func main() {
	/* Parse the arguments

	Run the parser as follows: go run parse_demo.go -demo /path/to/demo.dem -parserate 1/2/4/8/16/32/64/128 -demoID someDemoIDString

	The parserate should be one of 2^0 to 2^7. The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks.
	*/

	fl := new(flag.FlagSet)
	demoPathPtr := fl.String("demo", "", "Demo file `path`")
	parseRatePtr := fl.Int("parserate", 128, "Parse rate, indicates spacing between ticks")
	parseFramesPtr := fl.Bool("parseframes", false, "Parse frames")
	parseKillFramesPtr := fl.Bool("parsekillframes", false, "Parse kill frames")
	tradeTimePtr := fl.Int("tradetime", 5, "Trade time frame (in seconds)")
	roundBuyPtr := fl.String("buystyle", "hltv", "Round buy style")
	damagesRolledPtr := fl.Bool("dmgrolled", false, "Roll up damages")
	demoIDPtr := fl.String("demoid", "", "Demo string ID")
	jsonIndentationPtr := fl.Bool("jsonindentation", false, "Indent JSON file")
	outpathPtr := fl.String("out", "", "Path to write output JSON")

	err := fl.Parse(os.Args[1:])
	checkError(err)

	demPath := *demoPathPtr
	parseRate := *parseRatePtr
	parseFrames := *parseFramesPtr
	parseKillFrames := *parseKillFramesPtr
	tradeTime := int64(*tradeTimePtr)
	roundBuyStyle := *roundBuyPtr
	damagesRolled := *damagesRolledPtr
	jsonIndentation := *jsonIndentationPtr
	outpath := *outpathPtr

	// Read in demofile
	f, err := os.Open(demPath)
	defer f.Close()
	checkError(err)

	// Create new demoparser
	p := dem.NewParser(f)
	defer p.Close()

	// Parse demofile header
	header, err := p.ParseHeader()
	checkError(err)

	// Parse nav mesh given the map name
	currentMap := header.MapName
	currentMap = cleanMapName(currentMap)

	// Create flags to guide parsing
	roundStarted := 0
	roundInEndTime := 0
	roundInFreezetime := 0
	currentFrameIdx := 0
	convParsed := 0

	// Create game object, then initial round object
	currentGame := Game{}
	currentGame.MatchName = *demoIDPtr
	currentGame.Map = cleanMapName(currentMap)
	if p.TickRate() == 0 {
		currentGame.TickRate = 128
	} else {
		currentGame.TickRate = int64(p.TickRate())
	}
	currentGame.PlaybackTicks = int64(header.PlaybackTicks)
	currentGame.PlaybackFrames = int64(header.PlaybackFrames)
	currentGame.ClientName = header.ClientName

	// Create empty smoke tracking list
	smokes := []Smoke{}

	// Set parsing options
	parsingOpts := ParserOpts{}
	parsingOpts.ParseRate = int(parseRate)
	parsingOpts.TradeTime = tradeTime
	parsingOpts.RoundBuyStyle = roundBuyStyle
	parsingOpts.DamagesRolled = damagesRolled
	currentGame.ParsingOpts = parsingOpts

	currentRound := GameRound{}

	// Create empty action lists for first round
	currentRound.Bomb = []BombAction{}
	currentRound.Damages = []DamageAction{}
	currentRound.Flashes = []FlashAction{}
	currentRound.Frames = []GameFrame{}
	currentRound.Grenades = []GrenadeAction{}
	currentRound.Kills = []KillAction{}
	currentRound.WeaponFires = []WeaponFireAction{}

	RoundRestartDelay := int64(5)

	// Create empty lists
	currentGame.MMRanks = []MMRank{}
	currentGame.MatchPhases.AnnFinalRound = []int64{}
	currentGame.MatchPhases.AnnLastRoundHalf = []int64{}
	currentGame.MatchPhases.AnnMatchStarted = []int64{}
	currentGame.MatchPhases.GameHalfEnded = []int64{}
	currentGame.MatchPhases.MatchStart = []int64{}
	currentGame.MatchPhases.MatchStartedChanged = []int64{}
	currentGame.MatchPhases.WarmupChanged = []int64{}
	currentGame.MatchPhases.TeamSwitch = []int64{}
	currentGame.MatchPhases.RoundStarted = []int64{}
	currentGame.MatchPhases.RoundFreezeEnded = []int64{}
	currentGame.MatchPhases.RoundEnded = []int64{}
	currentGame.MatchPhases.RoundEndedOfficial = []int64{}

	// Parse rank updates
	p.RegisterEventHandler(func(e events.RankUpdate) {
		rankUpdate := MMRank{}

		rankUpdate.SteamID = e.SteamID64()
		rankUpdate.RankChange = e.RankChange
		rankUpdate.RankOld = convertRank(e.RankOld)
		rankUpdate.RankNew = convertRank(e.RankNew)
		rankUpdate.WinCount = e.WinCount

		currentGame.MMRanks = append(currentGame.MMRanks, rankUpdate)
	})

	// Parse player connects
	p.RegisterEventHandler(func(e events.PlayerConnect) {
		if e.Player != nil {
			gs := p.GameState()
			playerConnected := ConnectAction{}
			
			playerConnected.Tick = int64(gs.IngameTick())
			playerConnected.ConnectType = "connect"
			playerConnected.SteamID = e.Player.SteamID64

			currentGame.Connections = append(currentGame.Connections, playerConnected)
		}
	})

	// Parse player disconnects
	p.RegisterEventHandler(func(e events.PlayerDisconnected) {
		if e.Player != nil {
			gs := p.GameState()
			playerConnected := ConnectAction{}
			
			playerConnected.Tick = int64(gs.IngameTick())
			playerConnected.ConnectType = "disconnect"
			playerConnected.SteamID = e.Player.SteamID64

			currentGame.Connections = append(currentGame.Connections, playerConnected)
		}
	})

	// Parse the match phases
	p.RegisterEventHandler(func(e events.AnnouncementLastRoundHalf) {
		gs := p.GameState()

		currentGame.MatchPhases.AnnLastRoundHalf = append(currentGame.MatchPhases.AnnLastRoundHalf, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.AnnouncementFinalRound) {
		gs := p.GameState()

		currentGame.MatchPhases.AnnFinalRound = append(currentGame.MatchPhases.AnnFinalRound, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.AnnouncementMatchStarted) {
		gs := p.GameState()

		currentGame.MatchPhases.AnnMatchStarted = append(currentGame.MatchPhases.AnnMatchStarted, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.GameHalfEnded) {
		gs := p.GameState()

		currentGame.MatchPhases.GameHalfEnded = append(currentGame.MatchPhases.GameHalfEnded, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.MatchStart) {
		gs := p.GameState()

		currentGame.MatchPhases.MatchStart = append(currentGame.MatchPhases.MatchStart, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.MatchStartedChanged) {
		gs := p.GameState()

		currentGame.MatchPhases.MatchStartedChanged = append(currentGame.MatchPhases.MatchStartedChanged, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.IsWarmupPeriodChanged) {
		gs := p.GameState()

		currentGame.MatchPhases.WarmupChanged = append(currentGame.MatchPhases.WarmupChanged, int64(gs.IngameTick()))
	})

	p.RegisterEventHandler(func(e events.TeamSideSwitch) {
		gs := p.GameState()

		currentGame.MatchPhases.TeamSwitch = append(currentGame.MatchPhases.TeamSwitch, int64(gs.IngameTick()))
	})

	// Parse smokes
	p.RegisterEventHandler(func(e events.SmokeStart) {
		gs := p.GameState()
		s := Smoke{}
		s.GrenadeEntityID = e.Grenade.UniqueID() // GrenadeEntityID
		s.StartTick = int64(gs.IngameTick())
		s.X = float64(e.Position.X)
		s.Y = float64(e.Position.Y)
		s.Z = float64(e.Position.Z)
		foundNade := false
		for _, ele := range smokes {
			if ele.GrenadeEntityID == s.GrenadeEntityID {
				foundNade = true
			}
		}
		if !foundNade {
			smokes = append(smokes, s)
		}
		foundNade = false
	})

	p.RegisterEventHandler(func(e events.SmokeExpired) {
		removeID := e.Grenade.UniqueID() // e.GrenadeEntityID
		for i, ele := range smokes {
			if ele.GrenadeEntityID == removeID {
				smokes = removeExpiredSmoke(smokes, i)
			}
		}
	})

	// Parse round starts
	p.RegisterEventHandler(func(e events.RoundStart) {
		gs := p.GameState()
		currentGame.MatchPhases.RoundStarted = append(currentGame.MatchPhases.RoundStarted, int64(gs.IngameTick()))

		if roundStarted == 1 {
			currentGame.Rounds = append(currentGame.Rounds, currentRound)
		}

		roundStarted = 1
		roundInFreezetime = 1
		roundInEndTime = 0
		currentRound = GameRound{}

		// Reset smokes
		smokes = []Smoke{}

		// Create empty action lists
		currentRound.Bomb = []BombAction{}
		currentRound.Damages = []DamageAction{}
		currentRound.Flashes = []FlashAction{}
		currentRound.Frames = []GameFrame{}
		currentRound.Grenades = []GrenadeAction{}
		currentRound.Kills = []KillAction{}
		currentRound.WeaponFires = []WeaponFireAction{}

		// Parse flags
		currentRound.IsWarmup = gs.IsWarmupPeriod()
		currentRound.RoundNum = int64(len(currentGame.Rounds) + 1)
		currentRound.StartTick = int64(gs.IngameTick())
		currentRound.TScore = int64(gs.TeamTerrorists().Score())
		currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
		if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
			tTeam := gs.TeamTerrorists().ClanName()
			ctTeam := gs.TeamCounterTerrorists().ClanName()
			currentRound.TTeam = &tTeam
			currentRound.CTTeam = &ctTeam
		} 
		
		// Parse round money
		// tPlayers := gs.TeamTerrorists().Members()
		// currentRound.TBeginMoney = 0
		// ctPlayers := gs.TeamCounterTerrorists().Members()
		// currentRound.CTBeginMoney = 0
		// for _, p := range tPlayers {
		// 	if p != nil {
		// 		currentRound.TBeginMoney += int64(p.Money())
		// 	}

		// }
		// for _, p := range ctPlayers {
		// 	if p != nil {
		// 		currentRound.CTBeginMoney += int64(p.Money())
		// 	}
		// }

		// Parse the players
		teamCT := PlayerTeams{}
		teamCT.TeamName = gs.TeamCounterTerrorists().ClanName()
		for _, player := range gs.TeamCounterTerrorists().Members() {
			pl := Players{}
			pl.PlayerName = player.Name
			pl.SteamID = int64(player.SteamID64)
			foundPlayer := false
			for _, p := range teamCT.Players {
				if p.SteamID == pl.SteamID {
					foundPlayer = true
				}
			}
			if !foundPlayer {
				teamCT.Players = append(teamCT.Players, pl)
			}
		}
		currentRound.CTSide = teamCT

		teamT := PlayerTeams{}
		teamT.TeamName = gs.TeamTerrorists().ClanName()
		for _, player := range gs.TeamTerrorists().Members() {
			pl := Players{}
			pl.PlayerName = player.Name
			pl.SteamID = int64(player.SteamID64)
			foundPlayer := false
			for _, p := range teamT.Players {
				if p.SteamID == pl.SteamID {
					foundPlayer = true
				}
			}
			if !foundPlayer {
				teamT.Players = append(teamT.Players, pl)
			}
		}
		currentRound.TSide = teamT
	})

	// Parse round freezetime ends
	p.RegisterEventHandler(func(e events.RoundFreezetimeEnd) {
		gs := p.GameState()
		currentGame.MatchPhases.RoundFreezeEnded = append(currentGame.MatchPhases.RoundFreezeEnded, int64(gs.IngameTick()))

		// Reupdate the teams to make sure
		currentRound.TScore = int64(gs.TeamTerrorists().Score())
		currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
		if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
			tTeam := gs.TeamTerrorists().ClanName()
			ctTeam := gs.TeamCounterTerrorists().ClanName()
			currentRound.TTeam = &tTeam
			currentRound.CTTeam = &ctTeam
		}

		// Reset smokes
		smokes = []Smoke{}

		// Determine if round is still in warmup mode
		currentRound.IsWarmup = gs.IsWarmupPeriod()

		// If convars aren't parsed, do so
		if convParsed == 0 {
			// If convars are unparsed, record the convars of the server
			serverConfig := ServerConVar{}
			conv := gs.ConVars()
			serverConfig.CashBombDefused, _ = strconv.ParseInt(conv["cash_player_bomb_defused"], 10, 64)
			serverConfig.CashBombPlanted, _ = strconv.ParseInt(conv["cash_player_bomb_planted"], 10, 64)
			serverConfig.CashWinBomb, _ = strconv.ParseInt(conv["cash_team_terrorist_win_bomb"], 10, 64)
			serverConfig.CashWinDefuse, _ = strconv.ParseInt(conv["cash_team_win_by_defusing_bomb"], 10, 64)
			serverConfig.CashWinTimeRunOut, _ = strconv.ParseInt(conv["cash_team_win_by_time_running_out_bomb"], 10, 64)
			serverConfig.CashWinElimination, _ = strconv.ParseInt(conv["cash_team_elimination_bomb_map"], 10, 64)
			serverConfig.CashPlayerKilledDefault, _ = strconv.ParseInt(conv["cash_player_killed_enemy_default"], 10, 64)
			serverConfig.CashTeamLoserBonus, _ = strconv.ParseInt(conv["cash_team_loser_bonus"], 10, 64)
			serverConfig.CashTeamLoserBonusConsecutive, _ = strconv.ParseInt(conv["cash_team_loser_bonus_consecutive_rounds"], 10, 64)
			serverConfig.MaxRounds, _ = strconv.ParseInt(conv["mp_maxrounds"], 10, 64)
			serverConfig.RoundTime, _ = strconv.ParseInt(conv["mp_roundtime"], 10, 64)
			serverConfig.RoundTimeDefuse, _ = strconv.ParseInt(conv["mp_roundtime_defuse"], 10, 64)
			serverConfig.RoundRestartDelay, _ = strconv.ParseInt(conv["mp_round_restart_delay"], 10, 64)
			serverConfig.FreezeTime, _ = strconv.ParseInt(conv["mp_freezetime"], 10, 64)
			serverConfig.BuyTime, _ = strconv.ParseInt(conv["mp_buytime"], 10, 64)
			serverConfig.BombTimer, _ = strconv.ParseInt(conv["mp_c4timer"], 10, 64)
			serverConfig.TimeoutsAllowed, _ = strconv.ParseInt(conv["mp_team_timeout_max"], 10, 64)
			serverConfig.CoachingAllowed, _ = strconv.ParseInt(conv["sv_coaching_enabled"], 10, 64)
			currentGame.ServerVars = serverConfig
			convParsed = 1

			// Change so that round restarts are parsed using the server convar
			if serverConfig.RoundRestartDelay == 0 {
				RoundRestartDelay = 5 // This is default on many servers, I think
			} else {
				RoundRestartDelay = serverConfig.RoundRestartDelay
			}
		}

		if roundInFreezetime == 0 {
			// This means the RoundStart event did not fire, but the FreezeTimeEnd did
			currentGame.Rounds = append(currentGame.Rounds, currentRound)
			roundStarted = 1
			roundInEndTime = 0
			currentRound = GameRound{}

			// Create empty action lists
			currentRound.Bomb = []BombAction{}
			currentRound.Damages = []DamageAction{}
			currentRound.Flashes = []FlashAction{}
			currentRound.Frames = []GameFrame{}
			currentRound.Grenades = []GrenadeAction{}
			currentRound.Kills = []KillAction{}
			currentRound.WeaponFires = []WeaponFireAction{}

			currentRound.IsWarmup = gs.IsWarmupPeriod()
			currentRound.RoundNum = int64(len(currentGame.Rounds) + 1)
			currentRound.StartTick = int64(gs.IngameTick() - int(currentGame.TickRate)*int(currentGame.ServerVars.FreezeTime))
			currentRound.FreezeTimeEndTick = int64(gs.IngameTick())
			currentRound.TScore = int64(gs.TeamTerrorists().Score())
			currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
			if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
				tTeam := gs.TeamTerrorists().ClanName()
				ctTeam := gs.TeamCounterTerrorists().ClanName()
				currentRound.TTeam = &tTeam
				currentRound.CTTeam = &ctTeam
			}

			// See if start tick happened during a team switch. If so, then recalc scores.
			if len(currentGame.MatchPhases.TeamSwitch) > 0 {
				if (currentRound.StartTick) == currentGame.MatchPhases.TeamSwitch[len(currentGame.MatchPhases.TeamSwitch) - 1] {
					currentRound.TScore = int64(gs.TeamTerrorists().Score())
					currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
				}
			}
		}

		// Parse the players
		teamCT := PlayerTeams{}
		teamCT.TeamName = gs.TeamCounterTerrorists().ClanName()
		for _, player := range gs.TeamCounterTerrorists().Members() {
			pl := Players{}
			pl.PlayerName = player.Name
			pl.SteamID = int64(player.SteamID64)
			foundPlayer := false
			for _, p := range teamCT.Players {
				if p.SteamID == pl.SteamID {
					foundPlayer = true
				}
			}
			if !foundPlayer {
				teamCT.Players = append(teamCT.Players, pl)
			}
		}
		currentRound.CTSide = teamCT

		teamT := PlayerTeams{}
		teamT.TeamName = gs.TeamTerrorists().ClanName()
		for _, player := range gs.TeamTerrorists().Members() {
			pl := Players{}
			pl.PlayerName = player.Name
			pl.SteamID = int64(player.SteamID64)
			foundPlayer := false
			for _, p := range teamT.Players {
				if p.SteamID == pl.SteamID {
					foundPlayer = true
				}
			}
			if !foundPlayer {
				teamT.Players = append(teamT.Players, pl)
			}
		}
		currentRound.TSide = teamT

		roundInFreezetime = 0
		currentRound.FreezeTimeEndTick = int64(gs.IngameTick())
	})

	p.RegisterEventHandler(func(e events.RoundEndOfficial) {
		gs := p.GameState()
		currentGame.MatchPhases.RoundEndedOfficial = append(currentGame.MatchPhases.RoundEndedOfficial, int64(gs.IngameTick()))

		if roundInEndTime == 0 {
			currentRound.EndTick = int64(gs.IngameTick()) - (RoundRestartDelay * currentGame.TickRate)
			currentRound.EndOfficialTick = int64(gs.IngameTick())

			currentRound.CTBuyType = parseTeamBuy(currentRound.CTFreezeTimeEndEqVal, "CT", currentGame.ParsingOpts.RoundBuyStyle)
			currentRound.TBuyType = parseTeamBuy(currentRound.TFreezeTimeEndEqVal, "T", currentGame.ParsingOpts.RoundBuyStyle)
			// currentRound.CTBuyType = parseTeamBuy(currentRound.CTRoundStartEqVal+currentRound.CTSpend, "CT", currentGame.ParsingOpts.RoundBuyStyle)
			// currentRound.TBuyType = parseTeamBuy(currentRound.TRoundStartEqVal+currentRound.TSpend, "T", currentGame.ParsingOpts.RoundBuyStyle)

			// Parse who won the round, not great...but a stopgap measure
			tPlayers := gs.TeamTerrorists().Members()
			aliveT := 0
			ctPlayers := gs.TeamCounterTerrorists().Members()
			aliveCT := 0
			for _, p := range tPlayers {
				if p.IsAlive() && p != nil {
					aliveT = aliveT + 1
				}
			}
			for _, p := range ctPlayers {
				if p.IsAlive() && p != nil {
					aliveCT = aliveCT + 1
				}
			}
			if aliveCT == 0 {
				currentRound.Reason = "TerroristsWin"
				currentRound.EndTScore = currentRound.TScore + 1
				currentRound.EndCTScore = currentRound.CTScore
				if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
					tTeam := gs.TeamTerrorists().ClanName()
					ctTeam := gs.TeamCounterTerrorists().ClanName()
					currentRound.WinningTeam = &tTeam
					currentRound.LosingTeam = &ctTeam
				}
				currentRound.WinningSide = "T"
			} else {
				currentRound.Reason = "CTWin"
				currentRound.EndCTScore = currentRound.CTScore + 1
				currentRound.EndTScore = currentRound.TScore
				if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
					tTeam := gs.TeamTerrorists().ClanName()
					ctTeam := gs.TeamCounterTerrorists().ClanName()
					currentRound.WinningTeam = &ctTeam
					currentRound.LosingTeam = &tTeam
				}
				currentRound.WinningSide = "CT"
			}
		} else {
			currentRound.EndTick = int64(gs.IngameTick()) - (RoundRestartDelay * currentGame.TickRate)
			currentRound.EndOfficialTick = int64(gs.IngameTick())
		}
	})

	// Parse round ends
	p.RegisterEventHandler(func(e events.RoundEnd) {
		gs := p.GameState()
		
		if roundStarted == 1 {
			if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
				tTeam := gs.TeamTerrorists().ClanName()
				ctTeam := gs.TeamCounterTerrorists().ClanName()
				currentRound.TTeam = &tTeam
				currentRound.CTTeam = &ctTeam
			}
		}
		
		currentGame.MatchPhases.RoundEnded = append(currentGame.MatchPhases.RoundEnded, int64(gs.IngameTick()))

		if roundStarted == 0 {
			roundStarted = 1

			currentRound.RoundNum = 0
			currentRound.StartTick = 0
			currentRound.TScore = 0
			currentRound.CTScore = 0
			if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
				tTeam := gs.TeamTerrorists().ClanName()
				ctTeam := gs.TeamCounterTerrorists().ClanName()
				currentRound.TTeam = &tTeam
				currentRound.CTTeam = &ctTeam
			}
		}

		roundInEndTime = 1

		winningTeam := "CT"
		switch e.Winner {
		case common.TeamTerrorists:
			winningTeam = "T"
			currentRound.EndTScore = currentRound.TScore + 1
			currentRound.EndCTScore = currentRound.CTScore
		case common.TeamCounterTerrorists:
			winningTeam = "CT"
			currentRound.EndCTScore = currentRound.CTScore + 1
			currentRound.EndTScore = currentRound.TScore
		default:
			winningTeam = "Unknown"
		}

		currentRound.EndTick = int64(gs.IngameTick())
		currentRound.EndOfficialTick = int64(gs.IngameTick()) + (RoundRestartDelay * currentGame.TickRate)
		currentRound.Reason = convertRoundEndReason(e.Reason)
		currentRound.WinningSide = winningTeam

		if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
			tTeam := gs.TeamTerrorists().ClanName()
			ctTeam := gs.TeamCounterTerrorists().ClanName()

			if winningTeam == "CT" {
				currentRound.LosingTeam = &tTeam
				currentRound.WinningTeam = &ctTeam
			} else if winningTeam == "T" {
				currentRound.LosingTeam = &ctTeam
				currentRound.WinningTeam = &tTeam
			}
		}

		currentRound.CTBuyType = parseTeamBuy(currentRound.CTFreezeTimeEndEqVal, "CT", currentGame.ParsingOpts.RoundBuyStyle)
		currentRound.TBuyType = parseTeamBuy(currentRound.TFreezeTimeEndEqVal, "T", currentGame.ParsingOpts.RoundBuyStyle)
		// currentRound.CTBuyType = parseTeamBuy(currentRound.CTRoundStartEqVal+currentRound.CTSpend, "CT", currentGame.ParsingOpts.RoundBuyStyle)
		// currentRound.TBuyType = parseTeamBuy(currentRound.TRoundStartEqVal+currentRound.TSpend, "T", currentGame.ParsingOpts.RoundBuyStyle)

	})

	// Parse bomb defuses
	p.RegisterEventHandler(func(e events.BombDefused) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "defuse"
		bombSite := ""
		if e.Site == 65 {
			bombSite = "A"
		} else if e.Site == 66 {
			bombSite = "B"
		}
		currentBomb.BombSite = &bombSite

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// add bomb event
		currentRound.Bomb = append(currentRound.Bomb, currentBomb)
	})

	// Parse bomb defuses
	p.RegisterEventHandler(func(e events.BombDefuseStart) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "defuse_start"

		// Find bombsite where event is planted
		bombSite := ""
		bombPlantFound := false
		for _, b := range currentRound.Bomb {
			if b.BombAction == "plant" {
				bombSite = *b.BombSite
				bombPlantFound = true
			}
		}
		currentBomb.BombSite = &bombSite	

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// add
		if bombPlantFound {
			currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		}
	})

	// Parse bomb defuses
	p.RegisterEventHandler(func(e events.BombDefuseAborted) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "defuse_aborted"

		// Find bombsite where event is planted
		bombSite := ""
		bombPlantFound := false
		for _, b := range currentRound.Bomb {
			if b.BombAction == "plant" {
				bombSite = *b.BombSite
				bombPlantFound = true
			}
		}
		currentBomb.BombSite = &bombSite

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// Add Bomb Event
		if bombPlantFound {
			currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		}
	})

	// Parse weapon fires
	p.RegisterEventHandler(func(e events.WeaponFire) {
		gs := p.GameState()

		if (e.Weapon != nil) && (e.Weapon.String() != "Knife") && (e.Weapon.String() != "C4") && (e.Shooter != nil) {
			currentWeaponFire := WeaponFireAction{}
			currentWeaponFire.Tick = int64(gs.IngameTick())
			currentWeaponFire.Second = determineSecond(currentWeaponFire.Tick, currentRound, currentGame)
			currentWeaponFire.ClockTime = calculateClocktime(currentWeaponFire.Tick, currentRound, currentGame)
			currentWeaponFire.PlayerSteamID = int64(e.Shooter.SteamID64)
			currentWeaponFire.PlayerName = e.Shooter.Name
			if (e.Shooter.TeamState != nil) {
				currentWeaponFire.PlayerTeam = e.Shooter.TeamState.ClanName()
			}
			playerSide := "Unknown"
			switch e.Shooter.Team {
			case common.TeamTerrorists:
				playerSide = "T"
			case common.TeamCounterTerrorists:
				playerSide = "CT"
			case common.TeamSpectators:
				playerSide = "Spectator"
			case common.TeamUnassigned:
				playerSide = "Unassigned"
			default:
				playerSide = "Unknown"
			}
			currentWeaponFire.PlayerSide = playerSide

			// Player loc
			playerPos := e.Shooter.LastAlivePosition
			
			currentWeaponFire.PlayerX = float64(playerPos.X)
			currentWeaponFire.PlayerY = float64(playerPos.Y)
			currentWeaponFire.PlayerZ = float64(playerPos.Z)
			currentWeaponFire.Weapon = e.Weapon.String()
			currentWeaponFire.WeaponClass = convertWeaponClass(e.Weapon.Class())
			currentWeaponFire.AmmoInMagazine = int64(e.Weapon.AmmoInMagazine())
			currentWeaponFire.AmmoInReserve = int64(e.Weapon.AmmoReserve())
			currentWeaponFire.PlayerViewX = float64(e.Shooter.ViewDirectionX())
			currentWeaponFire.PlayerViewY = float64(e.Shooter.ViewDirectionY())
			currentWeaponFire.PlayerStrafe = e.Shooter.IsWalking()
			currentWeaponFire.ZoomLevel = int64(e.Weapon.ZoomLevel())

			// add
			currentRound.WeaponFires = append(currentRound.WeaponFires, currentWeaponFire)
		}
	})

	// Parse player flashes
	p.RegisterEventHandler(func(e events.PlayerFlashed) {
		gs := p.GameState()

		if e.Attacker != nil {
			currentFlash := FlashAction{}
			currentFlash.Tick = int64(gs.IngameTick())
			currentFlash.Second = determineSecond(currentFlash.Tick, currentRound, currentGame)
			currentFlash.ClockTime = calculateClocktime(currentFlash.Tick, currentRound, currentGame)

			// Attacker
			currentFlash.AttackerSteamID = int64(e.Attacker.SteamID64)
			currentFlash.AttackerName = e.Attacker.Name
			if (e.Attacker.TeamState != nil) {
				currentFlash.AttackerTeam = e.Attacker.TeamState.ClanName()
			}
			attackerSide := "Unknown"
			switch e.Attacker.Team {
			case common.TeamTerrorists:
				attackerSide = "T"
			case common.TeamCounterTerrorists:
				attackerSide = "CT"
			case common.TeamSpectators:
				attackerSide = "Spectator"
			case common.TeamUnassigned:
				attackerSide = "Unassigned"
			default:
				attackerSide = "Unknown"
			}
			currentFlash.AttackerSide = attackerSide

			// Attacker loc
			attackerPos := e.Attacker.LastAlivePosition
			
			currentFlash.AttackerX = float64(attackerPos.X)
			currentFlash.AttackerY = float64(attackerPos.Y)
			currentFlash.AttackerZ = float64(attackerPos.Z)
			currentFlash.AttackerViewX = float64(e.Attacker.ViewDirectionX())
			currentFlash.AttackerViewY = float64(e.Attacker.ViewDirectionY())

			// Player
			if e.Player != nil {
				if e.Player.IsAlive() {
					playerSteamID := int64(e.Player.SteamID64)
					currentFlash.PlayerSteamID = &playerSteamID
					currentFlash.PlayerName = &e.Player.Name
					playerClanName := ""

					if e.Player.TeamState != nil {
						playerClanName = e.Player.TeamState.ClanName()
					}

					currentFlash.PlayerTeam = &playerClanName
					playerSide := "Unknown"
					switch e.Player.Team {
					case common.TeamTerrorists:
						playerSide = "T"
					case common.TeamCounterTerrorists:
						playerSide = "CT"
					case common.TeamSpectators:
						playerSide = "Spectator"
					case common.TeamUnassigned:
						playerSide = "Unassigned"
					default:
						playerSide = "Unknown"
					}

					currentFlash.PlayerSide = &playerSide

					// Player loc
					playerPos := e.Player.LastAlivePosition
					
					playerX := float64(playerPos.X)
					playerY := float64(playerPos.Y)
					playerZ := float64(playerPos.Z)
					currentFlash.PlayerX = &playerX
					currentFlash.PlayerY = &playerY
					currentFlash.PlayerZ = &playerZ
					playerViewX := float64(e.Player.ViewDirectionX())
					playerViewY := float64(e.Player.ViewDirectionY())
					currentFlash.PlayerViewX = &playerViewX
					currentFlash.PlayerViewY = &playerViewY

					// Calculate flash duration in seconds
					flashDuration := float64(e.Player.FlashDurationTimeRemaining())/1000000000
					currentFlash.FlashDuration = &flashDuration

					// Add to list
					if *currentFlash.PlayerSide != "Spectator" && *currentFlash.PlayerSide != "Unassigned" && *currentFlash.PlayerSide != "Unknown" {
						currentRound.Flashes = append(currentRound.Flashes, currentFlash)
					}
				}
			}
		}

	})

	// Parse bomb plants
	p.RegisterEventHandler(func(e events.BombPlanted) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "plant"

		bombSite := ""
		if e.Site == 65 {
			bombSite = "A"
		} else if e.Site == 66 {
			bombSite = "B"
		}
		currentBomb.BombSite = &bombSite

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// Bomb event
		currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		plantTick := int64(gs.IngameTick())
		currentRound.BombPlantTick = &plantTick
	})

	// Parse bomb plants
	p.RegisterEventHandler(func(e events.BombPlantBegin) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "plant_begin"

		bombSite := ""
		if e.Site == 65 {
			bombSite = "A"
		} else if e.Site == 66 {
			bombSite = "B"
		}
		currentBomb.BombSite = &bombSite

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// Bomb event
		currentRound.Bomb = append(currentRound.Bomb, currentBomb)
	})

	// Parse bomb plants
	p.RegisterEventHandler(func(e events.BombPlantAborted) {
		gs := p.GameState()

		currentBomb := BombAction{}
		currentBomb.Tick = int64(gs.IngameTick())
		currentBomb.Second = determineSecond(currentBomb.Tick, currentRound, currentGame)
		currentBomb.ClockTime = calculateClocktime(currentBomb.Tick, currentRound, currentGame)
		currentBomb.BombAction = "plant_abort"

		// Find bombsite where event is planted
		bombSite := ""
		bombPlantFound := false
		for _, b := range currentRound.Bomb {
			if b.BombAction == "plant_begin" {
				bombSite = *b.BombSite
				bombPlantFound = true
			}
		}
		currentBomb.BombSite = &bombSite

		currentBomb.PlayerSteamID = int64(e.Player.SteamID64)
		currentBomb.PlayerName = e.Player.Name
		if (e.Player.TeamState != nil) {
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName()
		}

		// Player loc
		playerPos := e.Player.LastAlivePosition
		currentBomb.PlayerX = float64(playerPos.X)
		currentBomb.PlayerY = float64(playerPos.Y)
		currentBomb.PlayerZ = float64(playerPos.Z)

		// Add Bomb event
		if bombPlantFound {
			currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		}
	})

	// Parse grenade throws
	p.RegisterEventHandler(func(e events.GrenadeProjectileThrow) {
		gs := p.GameState()

		if e.Projectile.Thrower != nil {
			currentGrenade := GrenadeAction{}
			currentGrenade.UniqueID = e.Projectile.UniqueID()
			currentGrenade.ThrowTick = int64(gs.IngameTick())
			currentGrenade.ThrowSecond = determineSecond(currentGrenade.ThrowTick, currentRound, currentGame)
			currentGrenade.ThrowClockTime = calculateClocktime(currentGrenade.ThrowTick, currentRound, currentGame)

			currentGrenade.ThrowerSteamID = int64(e.Projectile.Thrower.SteamID64)
			currentGrenade.ThrowerName = e.Projectile.Thrower.Name
			currentGrenade.Grenade = e.Projectile.WeaponInstance.String()
			playerSide := "Unknown"

			tTeam := ""
			ctTeam := ""
			if (gs.TeamTerrorists() != nil) && (gs.TeamCounterTerrorists() != nil) {
				tTeam = gs.TeamTerrorists().ClanName()
				ctTeam = gs.TeamCounterTerrorists().ClanName()
			}
			
			switch e.Projectile.Thrower.Team {
			case common.TeamTerrorists:
				playerSide = "T"
				currentGrenade.ThrowerTeam = tTeam
			case common.TeamCounterTerrorists:
				playerSide = "CT"
				currentGrenade.ThrowerTeam = ctTeam
			case common.TeamSpectators:
				playerSide = "Spectator"
				currentGrenade.ThrowerTeam = ""
			case common.TeamUnassigned:
				playerSide = "Unassigned"
				currentGrenade.ThrowerTeam = ""
			default:
				playerSide = "Unknown"
				currentGrenade.ThrowerTeam = ""
			}
			currentGrenade.ThrowerSide = playerSide

			// Player location (use weaponfire event)
			playerPos := e.Projectile.Position()

			currentGrenade.ThrowerX = float64(playerPos.X)
			currentGrenade.ThrowerY = float64(playerPos.Y)
			currentGrenade.ThrowerZ = float64(playerPos.Z)

			// Add grenade event
			if playerSide == "CT" || playerSide == "T" {
				currentRound.Grenades = append(currentRound.Grenades, currentGrenade)
			}
		}
	})

	// Parse grenade destroys
	p.RegisterEventHandler(func(e events.GrenadeProjectileDestroy) {
		gs := p.GameState()

		if e.Projectile.Thrower != nil {
			for i, g := range currentRound.Grenades {
				if g.UniqueID == e.Projectile.UniqueID() {
					currentRound.Grenades[i].DestroyTick = int64(gs.IngameTick())
					currentRound.Grenades[i].DestroySecond = determineSecond(currentRound.Grenades[i].DestroyTick, currentRound, currentGame)
					currentRound.Grenades[i].DestroyClockTime = calculateClocktime(currentRound.Grenades[i].DestroyTick, currentRound, currentGame)
					// Grenade Location
					grenadePos := e.Projectile.Position()

					currentRound.Grenades[i].GrenadeX = float64(grenadePos.X)
					currentRound.Grenades[i].GrenadeY = float64(grenadePos.Y)
					currentRound.Grenades[i].GrenadeZ = float64(grenadePos.Z)
				}
			}
		}
	})

	// Parse kill events
	p.RegisterEventHandler(func(e events.Kill) {
		gs := p.GameState()

		if (roundInFreezetime == 0) && (parseKillFrames == true) {
			currentFrame := GameFrame{}
			currentFrame.IsKillFrame = true

			// Create empty player lists
			currentFrame.CT.Players = []PlayerInfo{}
			currentFrame.T.Players = []PlayerInfo{}

			currentFrame.Tick = int64(gs.IngameTick())
			currentFrame.Second = determineSecond(currentFrame.Tick, currentRound, currentGame)
			currentFrame.ClockTime = calculateClocktime(currentFrame.Tick, currentRound, currentGame)

			// Parse T
			currentFrame.T = TeamFrameInfo{}
			currentFrame.T.Side = "T"
			if (gs.TeamTerrorists() != nil) {
				currentFrame.T.Team = gs.TeamTerrorists().ClanName()
			}
			currentFrame.T.CurrentEqVal = int64(gs.TeamTerrorists().CurrentEquipmentValue())
			tPlayers := gs.TeamTerrorists().Members()

			for _, p := range tPlayers {
				if p != nil {
					if playerInList(p, currentFrame.T.Players) == false {
						currentFrame.T.Players = append(currentFrame.T.Players, parsePlayer(gs, p))
					}
				}
			}
			
			currentFrame.T.AlivePlayers = countAlivePlayers(currentFrame.T.Players)
			currentFrame.T.TotalUtility = countUtility(currentFrame.T.Players)
			// currentFrame.T.CurrentEqVal = sumPlayerEqVal(currentFrame.T.Players)

			// Parse CT
			currentFrame.CT = TeamFrameInfo{}
			currentFrame.CT.Side = "CT"
			if (gs.TeamCounterTerrorists() != nil) {
				currentFrame.CT.Team = gs.TeamCounterTerrorists().ClanName()
			}
			currentFrame.CT.CurrentEqVal = int64(gs.TeamCounterTerrorists().CurrentEquipmentValue())
			ctPlayers := gs.TeamCounterTerrorists().Members()

			for _, p := range ctPlayers {
				if p != nil {
					if playerInList(p, currentFrame.CT.Players) == false {
						currentFrame.CT.Players = append(currentFrame.CT.Players, parsePlayer(gs, p))
					}
				}
			}
			
			currentFrame.CT.AlivePlayers = countAlivePlayers(currentFrame.CT.Players)
			currentFrame.CT.TotalUtility = countUtility(currentFrame.CT.Players)
			// currentFrame.CT.CurrentEqVal = sumPlayerEqVal(currentFrame.CT.Players)
			
			// Parse projectiles objects
			allGrenades := gs.GrenadeProjectiles()
			currentFrame.Projectiles = []GrenadeInfo{}
			for _, ele := range allGrenades {
				currentProjectile := GrenadeInfo{}
				currentProjectile.ProjectileType = ele.WeaponInstance.String()
				objPos := ele.Trajectory[len(ele.Trajectory)-1]

				currentProjectile.X = float64(objPos.X)
				currentProjectile.Y = float64(objPos.Y)
				currentProjectile.Z = float64(objPos.Z)
				currentFrame.Projectiles = append(currentFrame.Projectiles, currentProjectile)
			}

			// Parse infernos
			allInfernos := gs.Infernos()
			currentFrame.Fires = []Fire{}
			for _, ele := range allInfernos {
				currentFire := Fire{}
				objPos := ele.Entity.Position()
				currentFire.UniqueID = ele.UniqueID()

				currentFire.X = float64(objPos.X)
				currentFire.Y = float64(objPos.Y)
				currentFire.Z = float64(objPos.Z)
				currentFrame.Fires = append(currentFrame.Fires, currentFire)
			}

			// Parse smokes
			currentFrame.Smokes = []Smoke{}
			currentFrame.Smokes = smokes

			// Parse bomb
			bombObj := gs.Bomb()
			currentBomb := BombInfo{}
			objPos := bombObj.Position()

			currentBomb.X = float64(objPos.X)
			currentBomb.Y = float64(objPos.Y)
			currentBomb.Z = float64(objPos.Z)
			currentFrame.Bomb = currentBomb
			if len(currentRound.Bomb) > 0 {
				for _, b := range currentRound.Bomb {
					if b.BombAction == "plant" {
						currentFrame.BombPlanted = true
						currentFrame.BombSite = *b.BombSite
					}
				}	
			} else {
				currentFrame.BombPlanted = false
			}

			currentRound.Frames = append(currentRound.Frames, currentFrame)
		}

		currentKill := KillAction{}
		currentKill.Tick = int64(gs.IngameTick())
		currentKill.Second = determineSecond(currentKill.Tick, currentRound, currentGame)
		currentKill.ClockTime = calculateClocktime(currentKill.Tick, currentRound, currentGame)
		if e.Weapon != nil {
			currentKill.Weapon = e.Weapon.String()
			currentKill.WeaponClass = convertWeaponClass(e.Weapon.Class())
		}
		currentKill.IsWallbang = e.IsWallBang()
		currentKill.PenetratedObjects = int64(e.PenetratedObjects)
		currentKill.IsHeadshot = e.IsHeadshot
		currentKill.AttackerBlinded = e.AttackerBlind
		currentKill.NoScope = e.NoScope
		currentKill.ThruSmoke = e.ThroughSmoke

		// Attacker
		if e.Killer != nil {
			attackerSteamID := int64(e.Killer.SteamID64)
			currentKill.AttackerSteamID = &attackerSteamID
			attackerName := e.Killer.Name
			currentKill.AttackerName = &attackerName
			if (e.Killer.TeamState != nil) {
				attackerTeamName := e.Killer.TeamState.ClanName()
				currentKill.AttackerTeam = &attackerTeamName
			}
			attackerSide := "Unknown"

			switch e.Killer.Team {
			case common.TeamTerrorists:
				attackerSide = "T"
			case common.TeamCounterTerrorists:
				attackerSide = "CT"
			case common.TeamSpectators:
				attackerSide = "Spectator"
			case common.TeamUnassigned:
				attackerSide = "Unassigned"
			default:
				attackerSide = "Unknown"
			}

			currentKill.AttackerSide = &attackerSide
			attackerPos := e.Killer.LastAlivePosition

			currentKill.AttackerX = &attackerPos.X
			currentKill.AttackerY = &attackerPos.Y
			currentKill.AttackerZ = &attackerPos.Z
			attackerViewX := float64(e.Killer.ViewDirectionX())
			attackerViewY := float64(e.Killer.ViewDirectionY())
			currentKill.AttackerViewX = &attackerViewX
			currentKill.AttackerViewY = &attackerViewY
		}

		// Victim
		if e.Victim != nil {
			victimSteamID := int64(e.Victim.SteamID64)
			currentKill.VictimSteamID = &victimSteamID
			victimName := e.Victim.Name
			currentKill.VictimName = &victimName
			if (e.Victim.TeamState != nil) {
				victimTeamName := e.Victim.TeamState.ClanName()
				currentKill.VictimTeam = &victimTeamName
			}
			victimSide := "Unknown"

			switch e.Victim.Team {
			case common.TeamTerrorists:
				victimSide = "T"
			case common.TeamCounterTerrorists:
				victimSide = "CT"
			case common.TeamSpectators:
				victimSide = "Spectator"
			case common.TeamUnassigned:
				victimSide = "Unassigned"
			default:
				victimSide = "Unknown"
			}

			currentKill.VictimSide = &victimSide
			victimPos := e.Victim.LastAlivePosition

			currentKill.VictimX = &victimPos.X
			currentKill.VictimY = &victimPos.Y
			currentKill.VictimZ = &victimPos.Z
			victimViewX := float64(e.Victim.ViewDirectionX())
			victimViewY := float64(e.Victim.ViewDirectionY())
			currentKill.VictimViewX = &victimViewX
			currentKill.VictimViewY = &victimViewY

			if currentKill.IsSuicide == false && e.Killer != nil && e.Victim != nil {
				X := math.Pow((*currentKill.AttackerX - *currentKill.VictimX), 2)
				Y := math.Pow((*currentKill.AttackerY - *currentKill.VictimY), 2)
				Z := math.Pow((*currentKill.AttackerZ - *currentKill.VictimZ), 2)
				currentKill.Distance = math.Sqrt(X + Y + Z)
			} else {
				currentKill.Distance = 0.0
			}

			// Parse teamkill
			currentKill.IsTeamkill = false
			currentKill.IsSuicide = false
			
			if e.Killer != nil {
				// Parse TKs
				if *currentKill.AttackerSide == *currentKill.VictimSide {
					currentKill.IsTeamkill = true
				} else {
					currentKill.IsTeamkill = false
				}

				// Parse Suicides
				if *currentKill.AttackerSteamID == *currentKill.VictimSteamID {
					currentKill.IsSuicide = true
				} else {
					currentKill.IsSuicide = false
				}
			} else {
				currentKill.IsTeamkill = true
				currentKill.IsSuicide = true
			}
			
		}

		// Assister
		if e.Assister != nil {
			assistSteamID := int64(e.Assister.SteamID64)
			currentKill.AssisterSteamID = &assistSteamID
			assisterName := e.Assister.Name
			currentKill.AssisterName = &assisterName
			if (e.Assister.TeamState != nil) {
				assistTeamName := e.Assister.TeamState.ClanName()
				currentKill.AssisterTeam = &assistTeamName
			}
			assisterSide := "Unknown"
			switch e.Assister.Team {
			case common.TeamTerrorists:
				assisterSide = "T"
			case common.TeamCounterTerrorists:
				assisterSide = "CT"
			case common.TeamSpectators:
				assisterSide = "Spectator"
			case common.TeamUnassigned:
				assisterSide = "Unassigned"
			default:
				assisterSide = "Unknown"
			}
			currentKill.AssisterSide = &assisterSide
		}

		// Parse the opening kill info and trade info
		if len(currentRound.Kills) == 0 {
			currentKill.IsFirstKill = true
		} else {
			currentKill.IsFirstKill = false
			currentKill.IsTrade = isTrade(currentRound.Kills[len(currentRound.Kills)-1], currentKill, currentGame.TickRate, currentGame.ParsingOpts.TradeTime)
			if len(currentRound.Kills) > 0 && e.Victim != nil && currentKill.IsTrade == true {
				currentKill.PlayerTradedName = currentRound.Kills[len(currentRound.Kills)-1].VictimName
				currentKill.PlayerTradedSteamID = currentRound.Kills[len(currentRound.Kills)-1].VictimSteamID
				currentKill.PlayerTradedTeam = currentRound.Kills[len(currentRound.Kills)-1].VictimTeam
			}
		}

		// Parse flash info for kill
		if e.Victim != nil {
			currentKill.VictimBlinded = e.Victim.IsBlinded()
			if e.Victim.IsBlinded() {
				
				// This will only be true if in the killfeed the assister is the flasher
				if e.AssistedFlash {
					currentKill.AssisterSteamID = nil
					currentKill.AssisterName = nil
					currentKill.AssisterTeam = nil
					currentKill.AssisterSide = nil
				}

				// Find their latest flash event
				for _, flash := range currentRound.Flashes {
					if (*flash.PlayerSteamID == *currentKill.VictimSteamID) && (flash.Tick >= currentKill.Tick - 5*currentGame.TickRate) && (flash.Tick <= currentKill.Tick) {
						currentKill.FlashThrowerSteamID = &flash.AttackerSteamID
						currentKill.FlashThrowerName = &flash.AttackerName
						currentKill.FlashThrowerTeam = &flash.AttackerTeam
						currentKill.FlashThrowerSide = &flash.AttackerSide
					}
				}
			}
		}
		
		// Add Kill
		currentRound.Kills = append(currentRound.Kills, currentKill)
	})

	// Parse damage events
	p.RegisterEventHandler(func(e events.PlayerHurt) {
		gs := p.GameState()

		currentDamage := DamageAction{}
		currentDamage.Tick = int64(gs.IngameTick())
		currentDamage.Second = determineSecond(currentDamage.Tick, currentRound, currentGame)
		currentDamage.ClockTime = calculateClocktime(currentDamage.Tick, currentRound, currentGame)
		if e.Weapon != nil {
			currentDamage.Weapon = e.Weapon.String()
			currentDamage.WeaponClass = convertWeaponClass(e.Weapon.Class())
		}
		currentDamage.HitGroup = convertHitGroup(e.HitGroup)
		currentDamage.HpDamage = int64(e.HealthDamage)
		currentDamage.HpDamageTaken = int64(e.HealthDamageTaken)
		currentDamage.ArmorDamage = int64(e.ArmorDamage)
		currentDamage.ArmorDamageTaken = int64(e.ArmorDamageTaken)

		// Attacker
		if e.Attacker != nil {
			attackerSteamID := int64(e.Attacker.SteamID64)
			currentDamage.AttackerSteamID = &attackerSteamID
			attackerName := e.Attacker.Name
			currentDamage.AttackerName = &attackerName
			if (e.Attacker.TeamState != nil) {
				attackerTeamName := e.Attacker.TeamState.ClanName()
				currentDamage.AttackerTeam = &attackerTeamName
			}

			attackerSide := "Unknown"
			switch e.Attacker.Team {
			case common.TeamTerrorists:
				attackerSide = "T"
			case common.TeamCounterTerrorists:
				attackerSide = "CT"
			case common.TeamSpectators:
				attackerSide = "Spectator"
			case common.TeamUnassigned:
				attackerSide = "Unassigned"
			default:
				attackerSide = "Unknown"
			}
			currentDamage.AttackerSide = &attackerSide

			attackerPos := e.Attacker.LastAlivePosition

			currentDamage.AttackerX = &attackerPos.X
			currentDamage.AttackerY = &attackerPos.Y
			currentDamage.AttackerZ = &attackerPos.Z
			attackerViewX := float64(e.Attacker.ViewDirectionX())
			attackerViewY := float64(e.Attacker.ViewDirectionY())
			currentDamage.AttackerViewX = &attackerViewX
			currentDamage.AttackerViewY = &attackerViewY
			attackerStrafe := e.Attacker.IsWalking()
			currentDamage.AttackerStrafe = &attackerStrafe

			if e.Weapon != nil {
				zoomLevel := int64(e.Weapon.ZoomLevel())
				currentDamage.ZoomLevel = &zoomLevel
			}
		}

		// Victim
		if e.Player != nil {
			victimSteamID := int64(e.Player.SteamID64)
			currentDamage.VictimSteamID = &victimSteamID
			victimName := e.Player.Name
			currentDamage.VictimName = &victimName
			if (e.Player.TeamState != nil) {
				victimTeamName := e.Player.TeamState.ClanName()
				currentDamage.VictimTeam = &victimTeamName
			}
			
			victimSide := "Unknown"
			switch e.Player.Team {
			case common.TeamTerrorists:
				victimSide = "T"
			case common.TeamCounterTerrorists:
				victimSide = "CT"
			case common.TeamSpectators:
				victimSide = "Spectator"
			case common.TeamUnassigned:
				victimSide = "Unassigned"
			default:
				victimSide = "Unknown"
			}
			currentDamage.VictimSide = &victimSide

			victimPos := e.Player.LastAlivePosition

			currentDamage.VictimX = &victimPos.X
			currentDamage.VictimY = &victimPos.Y
			currentDamage.VictimZ = &victimPos.Z
			victimViewX := float64(e.Player.ViewDirectionX())
			victimViewY := float64(e.Player.ViewDirectionY())
			currentDamage.VictimViewX = &victimViewX
			currentDamage.VictimViewY = &victimViewY

			// Parse team damage
			currentDamage.IsTeamDmg = false
			if currentDamage.AttackerSide != nil {
				if currentDamage.VictimSide != nil {
					if (*currentDamage.AttackerSide == *currentDamage.VictimSide) {
						currentDamage.IsTeamDmg = true
					}
				}
			}

			// Parse distance
			currentDamage.Distance = 0.0
			if e.Attacker != nil {
				X := math.Pow((*currentDamage.AttackerX - *currentDamage.VictimX), 2)
				Y := math.Pow((*currentDamage.AttackerY - *currentDamage.VictimY), 2)
				Z := math.Pow((*currentDamage.AttackerZ - *currentDamage.VictimZ), 2)
				currentDamage.Distance = math.Sqrt(X + Y + Z)
			}
		}

		// Add damages
		currentRound.Damages = append(currentRound.Damages, currentDamage)
	})

	// Parse a demo frame. If parse rate is 1, then every frame is parsed. If parse rate is 2, then every 2 frames is parsed, and so on
	p.RegisterEventHandler(func(e events.FrameDone) {
		gs := p.GameState()

		if (roundInFreezetime == 0) && (roundInEndTime == 0) {
			currentRound.CTRoundStartEqVal = int64(gs.TeamCounterTerrorists().RoundStartEquipmentValue())
			currentRound.TRoundStartEqVal = int64(gs.TeamTerrorists().RoundStartEquipmentValue())
			currentRound.CTFreezeTimeEndEqVal = int64(gs.TeamCounterTerrorists().FreezeTimeEndEquipmentValue())
			currentRound.TFreezeTimeEndEqVal = int64(gs.TeamTerrorists().FreezeTimeEndEquipmentValue())
			currentRound.CTRoundMoneySpend = int64(gs.TeamCounterTerrorists().MoneySpentThisRound())
			currentRound.TRoundMoneySpend = int64(gs.TeamTerrorists().MoneySpentThisRound())
		}
		
		if (roundInFreezetime == 0) && (currentFrameIdx == 0) && (parseFrames == true) {
			currentFrame := GameFrame{}
			currentFrame.IsKillFrame = false

			// Create empty player lists
			currentFrame.CT.Players = []PlayerInfo{}
			currentFrame.T.Players = []PlayerInfo{}

			currentFrame.Tick = int64(gs.IngameTick())
			currentFrame.Second = determineSecond(currentFrame.Tick, currentRound, currentGame)
			currentFrame.ClockTime = calculateClocktime(currentFrame.Tick, currentRound, currentGame)

			// Parse T
			currentFrame.T = TeamFrameInfo{}
			currentFrame.T.Side = "T"
			if (gs.TeamTerrorists() != nil) {
				currentFrame.T.Team = gs.TeamTerrorists().ClanName()
			}
			currentFrame.T.CurrentEqVal = int64(gs.TeamTerrorists().CurrentEquipmentValue())
			tPlayers := gs.TeamTerrorists().Members()

			for _, p := range tPlayers {
				if p != nil {
					if playerInList(p, currentFrame.T.Players) == false {
						currentFrame.T.Players = append(currentFrame.T.Players, parsePlayer(gs, p))
					}
				}
			}
			
			currentFrame.T.AlivePlayers = countAlivePlayers(currentFrame.T.Players)
			currentFrame.T.TotalUtility = countUtility(currentFrame.T.Players)
			// currentFrame.T.CurrentEqVal = sumPlayerEqVal(currentFrame.T.Players)

			// Parse CT
			currentFrame.CT = TeamFrameInfo{}
			currentFrame.CT.Side = "CT"
			if (gs.TeamCounterTerrorists() != nil) {
				currentFrame.CT.Team = gs.TeamCounterTerrorists().ClanName()
			}
			currentFrame.CT.CurrentEqVal = int64(gs.TeamCounterTerrorists().CurrentEquipmentValue())
			ctPlayers := gs.TeamCounterTerrorists().Members()

			for _, p := range ctPlayers {
				if p != nil {
					if playerInList(p, currentFrame.CT.Players) == false {
						currentFrame.CT.Players = append(currentFrame.CT.Players, parsePlayer(gs, p))
					}
				}
			}
			
			currentFrame.CT.AlivePlayers = countAlivePlayers(currentFrame.CT.Players)
			currentFrame.CT.TotalUtility = countUtility(currentFrame.CT.Players)
			// currentFrame.CT.CurrentEqVal = sumPlayerEqVal(currentFrame.CT.Players)
			
			// Parse projectiles objects
			allGrenades := gs.GrenadeProjectiles()
			currentFrame.Projectiles = []GrenadeInfo{}
			for _, ele := range allGrenades {
				currentProjectile := GrenadeInfo{}
				currentProjectile.ProjectileType = ele.WeaponInstance.String()
				objPos := ele.Trajectory[len(ele.Trajectory)-1]

				currentProjectile.X = float64(objPos.X)
				currentProjectile.Y = float64(objPos.Y)
				currentProjectile.Z = float64(objPos.Z)
				currentFrame.Projectiles = append(currentFrame.Projectiles, currentProjectile)
			}

			// Parse infernos
			allInfernos := gs.Infernos()
			currentFrame.Fires = []Fire{}
			for _, ele := range allInfernos {
				currentFire := Fire{}
				objPos := ele.Entity.Position()
				currentFire.UniqueID = ele.UniqueID()

				currentFire.X = float64(objPos.X)
				currentFire.Y = float64(objPos.Y)
				currentFire.Z = float64(objPos.Z)
				currentFrame.Fires = append(currentFrame.Fires, currentFire)
			}

			// Parse smokes
			currentFrame.Smokes = []Smoke{}
			currentFrame.Smokes = smokes

			// Parse bomb
			bombObj := gs.Bomb()
			currentBomb := BombInfo{}
			objPos := bombObj.Position()

			currentBomb.X = float64(objPos.X)
			currentBomb.Y = float64(objPos.Y)
			currentBomb.Z = float64(objPos.Z)
			currentFrame.Bomb = currentBomb
			if len(currentRound.Bomb) > 0 {
				for _, b := range currentRound.Bomb {
					if b.BombAction == "plant" {
						currentFrame.BombPlanted = true
						currentFrame.BombSite = *b.BombSite
					}
				}	
			} else {
				currentFrame.BombPlanted = false
			}

			// Add frame
			if (len(currentFrame.CT.Players) > 0) || (len(currentFrame.T.Players) > 0) {
				if (len(currentRound.Frames) > 0) {
					if currentRound.Frames[len(currentRound.Frames)-1].Tick < currentFrame.Tick {
						currentRound.Frames = append(currentRound.Frames, currentFrame)
					}
				} else {
					currentRound.Frames = append(currentRound.Frames, currentFrame)
				}
			}
			
			if currentFrameIdx == (currentGame.ParsingOpts.ParseRate - 1) {
				currentFrameIdx = 0
			} else {
				currentFrameIdx = currentFrameIdx + 1
			}
			
		} else {
			if currentFrameIdx == (currentGame.ParsingOpts.ParseRate - 1) {
				currentFrameIdx = 0
			} else {
				currentFrameIdx = currentFrameIdx + 1
			}
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	currentGame.ParsedToFrame = int64(p.CurrentFrame())

	// Add the most recent round
	currentGame.Rounds = append(currentGame.Rounds, currentRound)

	// Clean rounds
	if len(currentGame.Rounds) > 0 {
		// Loop through damages and see if there are any multi-damages in a single tick, and reduce them to one attacker-victim-weapon entry per tick
		if currentGame.ParsingOpts.DamagesRolled {
			for i := range currentGame.Rounds {
				var tempDamages []DamageAction
				for j := range currentGame.Rounds[i].Damages {
					if j < len(currentGame.Rounds[i].Damages) && j > 0 {
						if (len(tempDamages) > 0) &&
							(currentGame.Rounds[i].Damages[j].Tick == tempDamages[len(tempDamages)-1].Tick) &&
							(currentGame.Rounds[i].Damages[j].AttackerSteamID == tempDamages[len(tempDamages)-1].AttackerSteamID) &&
							(currentGame.Rounds[i].Damages[j].VictimSteamID == tempDamages[len(tempDamages)-1].VictimSteamID) &&
							(currentGame.Rounds[i].Damages[j].Weapon == tempDamages[len(tempDamages)-1].Weapon) {
							tempDamages[len(tempDamages)].HpDamage = tempDamages[len(tempDamages)-1].HpDamage + currentGame.Rounds[i].Damages[j].HpDamage
							tempDamages[len(tempDamages)].HpDamageTaken = tempDamages[len(tempDamages)-1].HpDamageTaken + currentGame.Rounds[i].Damages[j].HpDamageTaken
							tempDamages[len(tempDamages)].ArmorDamage = tempDamages[len(tempDamages)-1].ArmorDamage + currentGame.Rounds[i].Damages[j].ArmorDamage
							tempDamages[len(tempDamages)].ArmorDamageTaken = tempDamages[len(tempDamages)-1].ArmorDamageTaken + currentGame.Rounds[i].Damages[j].ArmorDamageTaken
						} else {
							tempDamages = append(tempDamages, currentGame.Rounds[i].Damages[j])
						}
					} else {
						tempDamages = append(tempDamages, currentGame.Rounds[i].Damages[j])
					}
				}
				currentGame.Rounds[i].Damages = tempDamages
			}
		}
		
		// Write the JSON
		var file []byte
		if jsonIndentation {
			file, _ = json.MarshalIndent(currentGame, "", " ")
		} else {
			file, _ = json.Marshal(currentGame)
		}
		_ = ioutil.WriteFile(outpath+"/"+currentGame.MatchName+".json", file, 0644)
	}

	// Check error
	checkError(err)
}

// Function to handle errors
func checkError(err error) {
	if (err != nil) {
		panic(err)
	}
}
