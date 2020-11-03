/*
TODO:
	Fuzzy logic for round ends - see https://github.com/markus-wa/demoinfocs-golang/issues/83
	Add player stats summary?
	Fix name finding alg in csgo - this is in the csgo library 
	Fix the team parsing - this is in the data scraper
	Build go file instead of Go run?

	Add automatic round end after a certain time period
	first and last round of match
	rounds where total score is same
	11 - 13
	11 - 13

	Are flashes correct?
*/

package main

import (
	"flag"
	"os"
	"log"
	"encoding/json"
	"io/ioutil"
	"strings"
	"math"
	"strconv"
	"sort"

	dem "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs"
	common "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/common"
	events "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/events"
	//ex "github.com/markus-wa/demoinfocs-golang/v2/examples"
	//metadata "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/metadata"
	gonav "github.com/pnxenopoulos/csgonavparse"
)

/* Logging
*/
var (
    WarningLogger *log.Logger
    InfoLogger    *log.Logger
    ErrorLogger   *log.Logger
)

func init() {
    file, err := os.OpenFile("demoparser.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
    if err != nil {
        log.Fatal(err)
    }

    InfoLogger = log.New(file, "INFO: ", log.Ldate|log.Ltime|log.Lshortfile)
    WarningLogger = log.New(file, "WARNING: ", log.Ldate|log.Ltime|log.Lshortfile)
    ErrorLogger = log.New(file, "ERROR: ", log.Ldate|log.Ltime|log.Lshortfile)
}

/* Define types for JSON
*/
type Game struct {
	MatchName string `json:"MatchId"`
	ClientName string `json:"ClientName"`
	Map string `json:"MapName"`
	TickRate int64 `json:"TickRate"`
	PlaybackTicks int64 `json:"PlaybackTicks"`
	ParseRate int `json:"ParseRate"`
	Rounds []GameRound `json:"GameRounds"`
}

type GameRound struct {
	RoundNum int64 `json:"RoundNum"`
	StartTick int64 `json:"StartTick"`
	FreezeTimeEnd int64 `json:"FreezeTimeEnd"`
	EndTick int64 `json:"EndTick"`
	ScoreUpdatedTick int64 `json:"ScoreUpdatedTick"`
	EndOfficialTick int64 `json:"EndOfficialTick"`
	TScore int64 `json:"TScore"`
	CTScore int64 `json:"CTScore"`
	WinningSide string `json:"WinningSide"`
	WinningTeam string `json:"WinningTeam"`
	LosingTeam string `json:"LosingTeam"`
	Reason string `json:"RoundEndReason"`
	CTStartEqVal int64 `json:"CTStartEqVal"`
	CTBuyType string `json:"CTBuyType"`
	TStartEqVal int64 `json:"TStartEqVal"`
	TBuyType string `json:"TBuyType"`
	Kills []KillAction `json:"Kills"`
	Damages []DamageAction `json:"Damages"`
	Grenades []GrenadeAction `json:"Grenades"`
	Bomb []BombAction `json:"BombEvents"`
	WeaponFires []WeaponFireAction `json:"WeaponFires"`
	Flashes []FlashAction `json:"Flashes"`
	Frames []GameFrame `json:"Frames"`
}

type GrenadeAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	PlayerSteamId int64 `json:"PlayerSteamId"`
	PlayerName string `json:"PlayerName"`
	PlayerTeam string `json:"PlayerTeam"`
	PlayerSide string `json:"PlayerSide"`
	PlayerX float64 `json:"PlayerX"`
	PlayerY float64 `json:"PlayerY"`
	PlayerZ float64 `json:"PlayerZ"`
	PlayerAreaId int64 `json:"PlayerAreaId"`
	PlayerAreaName string `json:"PlayerAreaName"`
	Grenade string `json:"GrenadeType"`
	GrenadeX float64 `json:"GrenadeX"`
	GrenadeY float64 `json:"GrenadeY"`
	GrenadeZ float64 `json:"GrenadeZ"`
	GrenadeAreaId int64 `json:"GrenadeAreaId"`
	GrenadeAreaName string `json:"GrenadeAreaName"`
}

type BombAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	PlayerSteamId int64 `json:"PlayerSteamId"`
	PlayerName string `json:"PlayerName"`
	PlayerTeam string `json:"PlayerTeam"`
	BombAction string `json:"BombAction"`
	BombSite string `json:"BombSite"`
}

type DamageAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	AttackerSteamId *int64 `json:"AttackerSteamId"`
	AttackerName *string `json:"AttackerName"`
	AttackerTeam *string `json:"AttackerTeam"`
	AttackerSide *string `json:"AttackerSide"`
	AttackerX *float64 `json:"AttackerX"`
	AttackerY *float64 `json:"AttackerY"`
	AttackerZ *float64 `json:"AttackerZ"`
	AttackerAreaId *int64 `json:"AttackerAreaId"`
	AttackerAreaName *string `json:"AttackerAreaName"`
	AttackerViewX *float64 `json:"AttackerViewX"`
	AttackerViewY *float64 `json:"AttackerViewY"`
	VictimSteamId *int64 `json:"VictimSteamId"`
	VictimName *string `json:"VictimName"`
	VictimTeam *string `json:"VictimTeam"`
	VictimSide *string `json:"VictimSide"`
	VictimX *float64 `json:"VictimX"`
	VictimY *float64 `json:"VictimY"`
	VictimZ *float64 `json:"VictimZ"`
	VictimAreaId *int64 `json:"VictimAreaId"`
	VictimAreaName *string `json:"VictimAreaName"`
	VictimViewX *float64 `json:"VictimViewX"`
	VictimViewY *float64 `json:"VictimViewY"`
	Weapon string `json:"Weapon"`
	HpDamage int64 `json:"HpDamage"`
	KillHpDamage int64 `json:"KillHpDamage"`
	ArmorDamage int64 `json:"ArmorDamage"`
	HitGroup string `json:"HitGroup"`
}

type KillAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	AttackerSteamId *int64 `json:"AttackerSteamId"`
	AttackerName *string `json:"AttackerName"`
	AttackerTeam *string `json:"AttackerTeam"`
	AttackerSide *string `json:"AttackerSide"`
	AttackerX *float64 `json:"AttackerX"`
	AttackerY *float64 `json:"AttackerY"`
	AttackerZ *float64 `json:"AttackerZ"`
	AttackerAreaId *int64 `json:"AttackerAreaId"`
	AttackerAreaName *string `json:"AttackerAreaName"`
	AttackerViewX *float64 `json:"AttackerViewX"`
	AttackerViewY *float64 `json:"AttackerViewY"`
	VictimSteamId *int64 `json:"VictimSteamId"`
	VictimName *string `json:"VictimName"`
	VictimTeam *string `json:"VictimTeam"`
	VictimSide *string `json:"VictimSide"`
	VictimX *float64 `json:"VictimX"`
	VictimY *float64 `json:"VictimY"`
	VictimZ *float64 `json:"VictimZ"`
	VictimAreaId *int64 `json:"VictimAreaId"`
	VictimAreaName *string `json:"VictimAreaName"`
	VictimViewX *float64 `json:"VictimViewX"`
	VictimViewY *float64 `json:"VictimViewY"`
	AssisterSteamId *int64 `json:"AssisterSteamId"`
	AssisterName *string `json:"AssisterName"`
	AssisterTeam *string `json:"AssisterTeam"`
	AssisterSide *string `json:"AssisterSide"`
	AssisterX *float64 `json:"AssisterX"`
	AssisterY *float64 `json:"AssisterY"`
	AssisterZ *float64 `json:"AssisterZ"`
	AssisterAreaId *int64 `json:"AssisterAreaId"`
	AssisterAreaName *string `json:"AssisterAreaName"`
	IsWallbang bool `json:"IsWallbang"`
	IsFlashed bool `json:"IsFlashed"`
	IsHeadshot bool `json:"IsHeadshot"`
	IsTrade bool `json:"IsTrade"`
	IsFirstKill bool `json:"IsFirstKill"`
	Weapon string `json:"Weapon"`
}

type WeaponFireAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	PlayerSteamId int64 `json:"PlayerSteamId"`
	PlayerName string `json:"PlayerName"`
	PlayerTeam string `json:"PlayerTeam"`
	PlayerSide string `json:"PlayerSide"`
	PlayerX float64 `json:"PlayerX"`
	PlayerY float64 `json:"PlayerY"`
	PlayerZ float64 `json:"PlayerZ"`
	PlayerAreaId int64 `json:"PlayerAreaId"`
	PlayerAreaName string `json:"PlayerAreaName"`
	PlayerViewX float64 `json:"PlayerViewX"`
	PlayerViewY float64 `json:"PlayerViewY"`
	WeaponName string `json:"WeaponName"`
}

type FlashAction struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	AttackerSteamId int64 `json:"AttackerSteamId"`
	AttackerName string `json:"AttackerName"`
	AttackerTeam string `json:"AttackerTeam"`
	AttackerSide string `json:"AttackerSide"`
	AttackerX float64 `json:"AttackerX"`
	AttackerY float64 `json:"AttackerY"`
	AttackerZ float64 `json:"AttackerZ"`
	AttackerAreaId int64 `json:"AttackerAreaId"`
	AttackerAreaName string `json:"AttackerAreaName"`
	AttackerViewX float64 `json:"AttackerViewX"`
	AttackerViewY float64 `json:"AttackerViewY"`
	PlayerSteamId *int64 `json:"PlayerSteamId"`
	PlayerName *string `json:"PlayerName"`
	PlayerTeam *string `json:"PlayerTeam"`
	PlayerSide *string `json:"PlayerSide"`
	PlayerX *float64 `json:"PlayerX"`
	PlayerY *float64 `json:"PlayerY"`
	PlayerZ *float64 `json:"PlayerZ"`
	PlayerAreaId *int64 `json:"PlayerAreaId"`
	PlayerAreaName *string `json:"PlayerAreaName"`
	PlayerViewX *float64 `json:"PlayerViewX"`
	PlayerViewY *float64 `json:"PlayerViewY"`
}

type GameFrame struct {
	Tick int64 `json:"Tick"`
	Second float64 `json:"Second"`
	FrameToken string `json:"PositionToken"`
	TToken string `json:"TToken"`
	CTToken string `json:"CTToken"`
	T TeamFrameInfo `json:"T"`
	CT TeamFrameInfo `json:"CT"`
	World []WorldObject `json:"World"`
	BombDistToA int64 `json:"BombDistanceToA"`
	BombDistToB int64 `json:"BombDistanceToB"`
}

type WorldObject struct {
	ObjType string `json:"ObjectType"`
	X float64 `json:"X"`
	Y float64 `json:"Y"`
	Z float64 `json:"Z"`
	AreaId int64 `json:"AreaId"`
	AreaName string `json:"AreaName"`
}

type TeamFrameInfo struct {
	Side string `json:"Side"`
	Team string `json:"TeamName"`
	CurrentEqVal int64 `json:"TeamEqVal"`
	PosToken string `json:"PositionToken"`
	AlivePlayers int64 `json:"AlivePlayers"`
	TotalUtility int64 `json:"TotalUtility"`
	UtilityLevel string `json:"UtilityLevel"`
	Players []PlayerInfo `json:"Players"`
}

type PlayerInfo struct {
	PlayerSteamId int64 `json:"SteamId"`
	PlayerName string `json:"Name"`
	X float64 `json:"X"`
	Y float64 `json:"Y"`
	Z float64 `json:"Z"`
	ViewX float64 `json:"ViewX"`
	ViewY float64 `json:"ViewY"`
	AreaId int64 `json:"AreaId"`
	AreaName string `json:"AreaName"`
	Hp int64 `json:"Hp"`
	Armor int64 `json:"Armor"`
	ActiveWeapon string `json:"ActiveWeapon"`
	TotalUtility int64 `json:"TotalUtility"`
	IsAlive bool `json:"IsAlive"`
	IsFlashed bool `json:"IsFlashed"`
	IsAirborne bool `json:"IsAirborne"`
	IsDucking bool `json:"IsDucking"`
	IsScoped bool `json:"IsScoped"`
	IsWalking bool `json:"IsWalking"`
	Inventory []string `json:"Inventory"`
	EqVal int64 `json:"EquipmentValue"`
	Money int64 `json:"Money"`
	HasHelmet bool `json:"HasHelmet"`
	HasDefuse bool `json:"HasDefuse"`
	DistToBombsiteA int64 `json:"DistToBombsiteA"`
	DistToBombsiteB int64 `json:"DistToBombsiteB"`
}

/* Define conversion functions
*/
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
	case 10:
		return "Gear"
	default:
		return "Unknown"
	}
}

/* Define parse functions
*/
func findAreaPlace(currArea *gonav.NavArea, mesh gonav.NavMesh) string {
	name := ""
	if currArea.Place != nil {
		name = currArea.Place.Name
	} else {
		areaCenter := currArea.GetCenter()
		maxDist := 1000000.0
		for _, currPlace := range mesh.Places {
			placeCenter, _ := currPlace.GetEstimatedCenter()
			unSq := math.Pow(float64(areaCenter.X)-float64(placeCenter.X),2) + math.Pow(float64(areaCenter.Y)-float64(placeCenter.Y),2) + math.Pow(float64(areaCenter.Z)-float64(placeCenter.Z),2)
			distance := math.Sqrt(unSq)
			if distance < maxDist {
				name = currPlace.Name
			}
		}
	}
	return name
}

func parsePlayer(p *common.Player, m gonav.NavMesh) PlayerInfo {
	currentPlayer := PlayerInfo{}
	currentPlayer.PlayerSteamId = int64(p.SteamID64)
	currentPlayer.PlayerName = p.Name
	playerPos := p.LastAlivePosition
	playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
	playerArea := m.GetNearestArea(playerPoint, true)
	var playerAreaId int64
	playerAreaPlace := ""
	if playerArea != nil {
		playerAreaId = int64(playerArea.ID)
		if playerArea.Place != nil {
			playerAreaPlace = playerArea.Place.Name
		} else {
			playerAreaPlace = findAreaPlace(playerArea, m)
		}
	}
	currentPlayer.AreaId = playerAreaId
	currentPlayer.AreaName = playerAreaPlace
	// Calc bombsite distances
	bombsiteA := m.GetPlaceByName("BombsiteA")
	aCenter, _ := bombsiteA.GetEstimatedCenter()
	aArea := m.GetNearestArea(aCenter, false)
	bombsiteB := m.GetPlaceByName("BombsiteB")
	bCenter, _ := bombsiteB.GetEstimatedCenter()
	bArea := m.GetNearestArea(bCenter, false)
	pathA, _ := gonav.SimpleBuildShortestPath(playerArea, aArea)
	currentPlayer.DistToBombsiteA = int64(len(pathA.Nodes))
	pathB, _ := gonav.SimpleBuildShortestPath(playerArea, bArea)
	currentPlayer.DistToBombsiteB = int64(len(pathB.Nodes))
	// Calc other metrics
	currentPlayer.X = float64(playerPos.X)
	currentPlayer.Y = float64(playerPos.Y)
	currentPlayer.Z = float64(playerPos.Z)
	currentPlayer.ViewX = float64(p.ViewDirectionX())
	currentPlayer.ViewY = float64(p.ViewDirectionY())
	currentPlayer.Hp = int64(p.Health())
	currentPlayer.Armor = int64(p.Armor())
	currentPlayer.IsAlive = p.IsAlive()
	currentPlayer.IsFlashed = p.IsBlinded()
	currentPlayer.IsAirborne = p.IsAirborne()
	currentPlayer.IsDucking = p.IsDucking()
	currentPlayer.IsScoped = p.IsScoped()
	currentPlayer.IsWalking = p.IsWalking()
	currentPlayer.HasDefuse = p.HasDefuseKit()
	currentPlayer.HasHelmet = p.HasHelmet()
	currentPlayer.Money = int64(p.Money())
	currentPlayer.EqVal = int64(p.EquipmentValueCurrent())
	currentPlayer.TotalUtility = int64(0)
	activeWeapon := ""
	if p.IsAlive() {
		activeWeapon = p.ActiveWeapon().String()
	}
	currentPlayer.ActiveWeapon = activeWeapon
	for _, w := range p.Weapons() {
		if w.String() != "Knife" {
			// Can't drop the knife
			currentPlayer.Inventory = append(currentPlayer.Inventory, w.String())
			if w.Class() == 6 {
				currentPlayer.TotalUtility = currentPlayer.TotalUtility + 1
			}
		}
	}
	return currentPlayer
}

func parseTeamBuy(eqVal int64, side string) string {
	/* Need to add more coverage, rework. Include force buys? Light buy is eco?
	*/
	if side == "CT" {
		if eqVal < 2000 {
			return "Full Eco"
		} else if (eqVal >= 2000) && (eqVal < 6000) {
			return "Eco"
		} else if (eqVal >= 6000) && (eqVal < 22000) {
			return "Half Buy"
		} else if (eqVal >= 22000) {
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
		} else if (eqVal >= 18500) {
			return "Full Buy"
		} else {
			return "Unknown"
		}
	}
}

func acceptableGamePhase(gs dem.GameState) bool {
	warmup := gs.IsWarmupPeriod()
	if warmup == false {
		return true
	} else {
		return false
	}
	//return true
	//if (gp == 2) || (gp == 3) || (gp == 4) {
	//	return true
	//} else {
	//	return false
	//}
}

func isTrade(killA KillAction, killB KillAction) bool {
	// If the the previous killer is not the person killed, it is not a trade
	killBVictimId := *killB.VictimSteamId
	killAAttackerId := *killA.AttackerSteamId
	if killBVictimId != killAAttackerId {
		return false
	} else {
		if (killB.Tick - killA.Tick < int64(5*128)) {
			return true
		} else {
			return false
		}
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

func determineUtilityLevel(x int64) string {
	if x < 5 {
		return "Very Low"
	} else if (x >= 5) && (x < 10) {
		return "Low"
	} else if (x >= 10) && (x < 15) {
		return "High"
	} else if (x >= 15) {
		return "Very High"
	} else {
		return "Unknown"
	}
}

func findIdx(sl []string, val string) int {
    for p, v := range sl {
        if (v == val) {
            return p
        }
    }
    return -1
}

func createAlivePlayerSlice(players []PlayerInfo) []string {
	var alivePlayerPlaces []string
	for _, p := range players {
		if p.IsAlive {
			alivePlayerPlaces = append(alivePlayerPlaces, p.AreaName)
		}
	}
	return alivePlayerPlaces
}

func createCountToken(alivePlaces []string, placeSl []string) string {
	// Create count token, initialize to 0
	countToken := make([]int, len(placeSl))
	for i, _ := range countToken {
		countToken[i] = 0
	}
	// Loop through and add 1 where players are
	if len(alivePlaces) > 0 {
		for _, v := range alivePlaces {
			vIdx := findIdx(placeSl, v)
			countToken[vIdx] = countToken[vIdx]+1
		}
	}
	// Create string token
	tokenStr := ""
	for _, i := range countToken {
		tokenStr = tokenStr + strconv.Itoa(i)
	}
	return tokenStr
}

/* Define cleaning functions
*/
func cleanMapName(mapName string) string {
	lastSlash := strings.LastIndex(mapName, "/")
	if lastSlash == -1 {
		return mapName
	} else {
		return mapName[lastSlash+1:len(mapName)]
	}
}

// Main
func main() {
	InfoLogger.Println("Started demoparser")
	/* Parse the arguments

	Run the parser as follows: go run parse_demo.go -demo /path/to/demo.dem -parserate 1/2/4/8/16/32/64/128 -demoid someDemoIdString

	The parserate should be one of 2^0 to 2^7. The lower the value, the more frames are collected. Indicates spacing between parsed demo frames in ticks.
	*/
	fl := new(flag.FlagSet)
	demoPathPtr := fl.String("demo", "", "Demo file `path`")
	parseRatePtr := fl.Int("parserate", 1, "Parse rate, indicates spacing between ticks")
	demoIdPtr := fl.String("demoid", "", "Demo string ID")
	outpathPtr := fl.String("out", "", "Path to write output JSON")

	err := fl.Parse(os.Args[1:])
	if err != nil {
		ErrorLogger.Println("ERROR PARSING FLAGS")
		ErrorLogger.Println(err.Error())
		panic(err)
	}

	demPath := *demoPathPtr
	parseRate := *parseRatePtr
	outpath := *outpathPtr

	InfoLogger.Printf("Parsed arguments, reading in %s and a parse rate of %d \n", demPath, parseRate)

	// Read in demofile
	f, err := os.Open(demPath)
	defer f.Close()
	checkError(err)

	// Create new demoparser
	p := dem.NewParser(f)

	// Parse demofile header
	header, err := p.ParseHeader()
	checkError(err)

	// Parse nav mesh given the map name
	currentMap := header.MapName
	currentMap = cleanMapName(currentMap)

	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()

	InfoLogger.Printf("Parsed demo header and mesh for map %s \n", currentMap)

	// Create list of places as parsed from the nav mesh
	var placeSl []string
	for _, currPlace := range mesh.Places {
		placeSl = append(placeSl, currPlace.Name)
	}
	
	// Alphabetize the slice of places to standardize it
	sort.Strings(placeSl)

	// Create flags to guide parsing
	roundStarted := 0
	roundInFreezetime := 0
	currentFrameIdx := 0

	// Create game object, then initial round object
	currentGame := Game{}
	currentGame.MatchName = *demoIdPtr // cleanMapName(strings.TrimSuffix(demPath, ".dem"))
	currentGame.Map = cleanMapName(currentMap)
	if p.TickRate() == 0 {
		currentGame.TickRate = 128
	} else {
		currentGame.TickRate = int64(p.TickRate())
	}
	currentGame.PlaybackTicks = int64(header.PlaybackTicks)
	currentGame.ClientName = header.ClientName
	currentGame.ParseRate = int(parseRate)
	
	currentRound := GameRound{}

	InfoLogger.Printf("Demo is of type %s with tickrate %d \n", currentGame.ClientName, currentGame.TickRate)
	InfoLogger.Printf("Demo name is %s from %s\n", currentGame.MatchName, demPath)
	InfoLogger.Println("Registering event handlers, parsing demo")

	// Parse round starts, which sometimes happen when MatchStartedChanged
	p.RegisterEventHandler(func(e events.MatchStartedChanged) {	
		gs := p.GameState()

		if (acceptableGamePhase(gs)) && (roundStarted == 0) && (e.NewIsStarted == true) {
			roundStarted = 1
			roundInFreezetime = 0 // When match starts, the freezetime is usually good to go
			currentRound = GameRound{}
			currentRound.RoundNum = int64(len(currentGame.Rounds)+1)
			currentRound.StartTick = int64(gs.IngameTick())
			currentRound.FreezeTimeEnd = int64(gs.IngameTick())
			currentRound.TScore = int64(gs.TeamTerrorists().Score())
			currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
		}
	})

	// Parse round starts
	p.RegisterEventHandler(func(e events.RoundStart) {	
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			roundStarted = 1
			roundInFreezetime = 1
			currentRound = GameRound{}
			currentRound.RoundNum = int64(len(currentGame.Rounds)+1)
			currentRound.StartTick = int64(gs.IngameTick())
			currentRound.TScore = int64(gs.TeamTerrorists().Score())
			currentRound.CTScore = int64(gs.TeamCounterTerrorists().Score())
		}
	})

	// Parse round freezetime ends
	p.RegisterEventHandler(func(e events.RoundFreezetimeEnd) {		
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			roundInFreezetime = 0
			currentRound.FreezeTimeEnd = int64(gs.IngameTick())
		}
	})

	// Parse round ends
	p.RegisterEventHandler(func(e events.RoundEnd) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			winningTeam := "CT"
			switch e.Winner {
			case common.TeamTerrorists:
				winningTeam = "T"
			case common.TeamCounterTerrorists:
				winningTeam = "CT"
			default:
				winningTeam = "Unknown"
			}
			currentRound.EndTick = int64(gs.IngameTick())
			currentRound.EndOfficialTick = int64(gs.IngameTick())
			currentRound.Reason = convertRoundEndReason(e.Reason)
			currentRound.WinningSide = winningTeam
			currentRound.LosingTeam = e.LoserState.ClanName()
			currentRound.WinningTeam = e.WinnerState.ClanName()
			// Parse the start eq values
			frameIdx := (currentGame.TickRate*3)/int64(currentGame.ParseRate)
			if frameIdx < int64(len(currentRound.Frames)) {
				startFrame := currentRound.Frames[frameIdx-1]
				currentRound.CTStartEqVal = startFrame.CT.CurrentEqVal
				currentRound.TStartEqVal = startFrame.T.CurrentEqVal
				if (len(currentGame.Rounds) == 0) || (len(currentGame.Rounds) == 15) {
					currentRound.CTBuyType = "Pistol"
					currentRound.TBuyType = "Pistol"
				} else {
					currentRound.CTBuyType = parseTeamBuy(currentRound.CTStartEqVal, "CT")
					currentRound.TBuyType = parseTeamBuy(currentRound.TStartEqVal, "T")
				}
				// add to round slice
				currentGame.Rounds = append(currentGame.Rounds, currentRound)
			}
		}
	})

	// Parse score changes
	p.RegisterEventHandler(func(e events.ScoreUpdated) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) && (len(currentGame.Rounds) > 0) {
			// Replace the last round object
			currentGame.Rounds[len(currentGame.Rounds)-1].ScoreUpdatedTick = int64(gs.IngameTick())
			// reset
			roundStarted = 0
		}
	})

	// Parse official round ends. Before this, players can still move around.
	p.RegisterEventHandler(func(e events.RoundEndOfficial) {
		gs := p.GameState()

		// && (roundStarted == 1)
		if (acceptableGamePhase(gs))  {
			// Replace the last round object
			currentGame.Rounds[len(currentGame.Rounds)-1].EndOfficialTick = int64(gs.IngameTick())
		}
	})

	// Parse bomb defuses
	p.RegisterEventHandler(func(e events.BombDefused) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentBomb := BombAction{}
			currentBomb.Tick = int64(gs.IngameTick())
			currentBomb.Second = (float64(currentBomb.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			currentBomb.BombAction = "defuse"
			currentBomb.BombSite = ""
			if e.Site == 65 {
				currentBomb.BombSite = "A"
			} else if e.Site == 66 {
				currentBomb.BombSite = "B"
			}
			currentBomb.PlayerSteamId = int64(e.Player.SteamID64)
			currentBomb.PlayerName = e.Player.Name
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName() 
			// add
			currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		}
	})

	// Parse weapon fires
	p.RegisterEventHandler(func(e events.WeaponFire) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentWeaponFire := WeaponFireAction{}
			currentWeaponFire.Tick = int64(gs.IngameTick())
			currentWeaponFire.Second = (float64(currentWeaponFire.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			currentWeaponFire.PlayerSteamId = int64(e.Shooter.SteamID64)
			currentWeaponFire.PlayerName = e.Shooter.Name
			currentWeaponFire.PlayerTeam = e.Shooter.TeamState.ClanName()
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
			playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
			playerArea := mesh.GetNearestArea(playerPoint, true)
			var playerAreaId int64
			playerAreaPlace := ""
			if playerArea != nil {
				playerAreaId = int64(playerArea.ID)
				if playerArea.Place != nil {
					playerAreaPlace = playerArea.Place.Name
				} else {
					playerAreaPlace = findAreaPlace(playerArea, mesh)
				}
			}
			currentWeaponFire.PlayerAreaId = playerAreaId
			currentWeaponFire.PlayerAreaName = playerAreaPlace
			currentWeaponFire.PlayerX = float64(playerPos.X)
			currentWeaponFire.PlayerY = float64(playerPos.Y)
			currentWeaponFire.PlayerZ = float64(playerPos.Z)
			currentWeaponFire.WeaponName = e.Weapon.String()
			currentWeaponFire.PlayerViewX = float64(e.Shooter.ViewDirectionX())
			currentWeaponFire.PlayerViewY = float64(e.Shooter.ViewDirectionY())
			// add
			currentRound.WeaponFires = append(currentRound.WeaponFires, currentWeaponFire)
		}
	})

	// Parse player flashes
	p.RegisterEventHandler(func(e events.PlayerFlashed) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentFlash := FlashAction{}
			currentFlash.Tick = int64(gs.IngameTick())
			currentFlash.Second = (float64(currentFlash.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			// Attacker
			currentFlash.AttackerSteamId = int64(e.Attacker.SteamID64)
			currentFlash.AttackerName = e.Attacker.Name
			currentFlash.AttackerTeam = e.Attacker.TeamState.ClanName()
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
			attackerPoint := gonav.Vector3{X: float32(attackerPos.X), Y: float32(attackerPos.Y), Z: float32(attackerPos.Z)}
			attackerArea := mesh.GetNearestArea(attackerPoint, true)
			var attackerAreaId int64
			attackerAreaPlace := ""
			if attackerArea != nil {
				attackerAreaId = int64(attackerArea.ID)
				if attackerArea.Place != nil {
					attackerAreaPlace = attackerArea.Place.Name
				} else {
					attackerAreaPlace = findAreaPlace(attackerArea, mesh)
				}
			}
			currentFlash.AttackerAreaId = attackerAreaId
			currentFlash.AttackerAreaName = attackerAreaPlace
			currentFlash.AttackerX = float64(attackerPos.X)
			currentFlash.AttackerY = float64(attackerPos.Y)
			currentFlash.AttackerZ = float64(attackerPos.Z)
			currentFlash.AttackerViewX = float64(e.Attacker.ViewDirectionX())
			currentFlash.AttackerViewY = float64(e.Attacker.ViewDirectionY())
			// Player
			if e.Player != nil {
				playerSteamId := int64(e.Player.SteamID64)
				currentFlash.PlayerSteamId = &playerSteamId
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
				playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
				playerArea := mesh.GetNearestArea(playerPoint, true)
				var playerAreaId int64
				playerAreaPlace := ""
				if playerArea != nil {
					playerAreaId = int64(playerArea.ID)
					if playerArea.Place != nil {
						playerAreaPlace = playerArea.Place.Name
					} else {
						playerAreaPlace = findAreaPlace(playerArea, mesh)
					}
				}
				currentFlash.PlayerAreaId = &playerAreaId
				currentFlash.PlayerAreaName = &playerAreaPlace
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
				// add
				if *currentFlash.PlayerSide != "Spectator" {
					currentRound.Flashes = append(currentRound.Flashes, currentFlash)
				}
				
			}
		}
	})

	// Parse bomb plants
	p.RegisterEventHandler(func(e events.BombPlanted) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentBomb := BombAction{}
			currentBomb.Tick = int64(gs.IngameTick())
			currentBomb.Second = (float64(currentBomb.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			currentBomb.BombAction = "plant"
			currentBomb.BombSite = ""
			if e.Site == 65 {
				currentBomb.BombSite = "A"
			} else if e.Site == 66 {
				currentBomb.BombSite = "B"
			}
			currentBomb.PlayerSteamId = int64(e.Player.SteamID64)
			currentBomb.PlayerName = e.Player.Name
			currentBomb.PlayerTeam = e.Player.TeamState.ClanName() 
			// add
			currentRound.Bomb = append(currentRound.Bomb, currentBomb)
		}
	})

	// Parse molotov events
	p.RegisterEventHandler(func(e events.GrenadeProjectileDestroy) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			if (e.Projectile.Thrower != nil) && ((e.Projectile.WeaponInstance.String() == "Molotov") || (e.Projectile.WeaponInstance.String() == "Incendiary Grenade")) {
				currentGrenade := GrenadeAction{}
				currentGrenade.Tick = int64(gs.IngameTick())
				currentGrenade.Second = (float64(currentGrenade.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
				currentGrenade.PlayerSteamId = int64(e.Projectile.Thrower.SteamID64)
				currentGrenade.PlayerName = e.Projectile.Thrower.Name
				currentGrenade.PlayerTeam = e.Projectile.Thrower.TeamState.ClanName()
				currentGrenade.Grenade = e.Projectile.WeaponInstance.String()
				playerSide := "Unknown"
				switch e.Projectile.Thrower.Team {
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
				// Player loc
				currentGrenade.PlayerSide = playerSide
				playerPos := e.Projectile.Thrower.LastAlivePosition
				playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
				playerArea := mesh.GetNearestArea(playerPoint, true)
				var playerAreaId int64
				playerAreaPlace := ""
				if playerArea != nil {
					playerAreaId = int64(playerArea.ID)
					if playerArea.Place != nil {
						playerAreaPlace = playerArea.Place.Name
					} else {
						playerAreaPlace = findAreaPlace(playerArea, mesh)
					}
				}
				currentGrenade.PlayerAreaId = playerAreaId
				currentGrenade.PlayerAreaName = playerAreaPlace
				currentGrenade.PlayerX = float64(playerPos.X)
				currentGrenade.PlayerY = float64(playerPos.Y)
				currentGrenade.PlayerZ = float64(playerPos.Z)
				// Grenade Loc
				grenadePos := e.Projectile.Position()
				grenadePoint := gonav.Vector3{X: float32(grenadePos.X), Y: float32(grenadePos.Y), Z: float32(grenadePos.Z)}
				grenadeArea := mesh.GetNearestArea(grenadePoint, true)
				var grenadeAreaId int64
				grenadeAreaPlace := ""
				if grenadeArea != nil {
					grenadeAreaId = int64(grenadeArea.ID)
					if grenadeArea.Place != nil {
						grenadeAreaPlace = grenadeArea.Place.Name
					} else {
						grenadeAreaPlace = findAreaPlace(grenadeArea, mesh)
					}
				}
				currentGrenade.GrenadeAreaId = grenadeAreaId
				currentGrenade.GrenadeAreaName = grenadeAreaPlace
				currentGrenade.GrenadeX = float64(grenadePos.X)
				currentGrenade.GrenadeY = float64(grenadePos.Y)
				currentGrenade.GrenadeZ = float64(grenadePos.Z)
				// add
				currentRound.Grenades = append(currentRound.Grenades, currentGrenade)
			}
		}
	})

	// Parse grenade events
	p.RegisterEventHandler(func(e events.GrenadeEventIf) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			if e.Base().Thrower != nil {
				currentGrenade := GrenadeAction{}
				currentGrenade.Tick = int64(gs.IngameTick())
				currentGrenade.Second = (float64(currentGrenade.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
				currentGrenade.PlayerSteamId = int64(e.Base().Thrower.SteamID64)
				currentGrenade.PlayerName = e.Base().Thrower.Name
				currentGrenade.PlayerTeam = e.Base().Thrower.TeamState.ClanName()
				currentGrenade.Grenade = e.Base().Grenade.String()
				playerSide := "Unknown"
				switch e.Base().Thrower.Team {
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
				// Player loc
				currentGrenade.PlayerSide = playerSide
				playerPos := e.Base().Thrower.LastAlivePosition
				playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
				playerArea := mesh.GetNearestArea(playerPoint, true)
				var playerAreaId int64
				playerAreaPlace := ""
				if playerArea != nil {
					playerAreaId = int64(playerArea.ID)
					if playerArea.Place != nil {
						playerAreaPlace = playerArea.Place.Name
					} else {
						playerAreaPlace = findAreaPlace(playerArea, mesh)
					}
				}
				currentGrenade.PlayerAreaId = playerAreaId
				currentGrenade.PlayerAreaName = playerAreaPlace
				currentGrenade.PlayerX = float64(playerPos.X)
				currentGrenade.PlayerY = float64(playerPos.Y)
				currentGrenade.PlayerZ = float64(playerPos.Z)
				// Grenade Loc
				grenadePos := e.Base().Position
				grenadePoint := gonav.Vector3{X: float32(grenadePos.X), Y: float32(grenadePos.Y), Z: float32(grenadePos.Z)}
				grenadeArea := mesh.GetNearestArea(grenadePoint, true)
				var grenadeAreaId int64
				grenadeAreaPlace := ""
				if grenadeArea != nil {
					grenadeAreaId = int64(grenadeArea.ID)
					if grenadeArea.Place != nil {
						grenadeAreaPlace = grenadeArea.Place.Name
					} else {
						grenadeAreaPlace = findAreaPlace(grenadeArea, mesh)
					}
				}
				currentGrenade.GrenadeAreaId = grenadeAreaId
				currentGrenade.GrenadeAreaName = grenadeAreaPlace
				currentGrenade.GrenadeX = float64(grenadePos.X)
				currentGrenade.GrenadeY = float64(grenadePos.Y)
				currentGrenade.GrenadeZ = float64(grenadePos.Z)
				// add
				currentRound.Grenades = append(currentRound.Grenades, currentGrenade)
			}
		}
	})

	// Parse kill events
	p.RegisterEventHandler(func(e events.Kill) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentKill := KillAction{}
			currentKill.Tick = int64(gs.IngameTick())
			currentKill.Second = (float64(currentKill.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			currentKill.Weapon = e.Weapon.String()
			currentKill.IsWallbang = e.IsWallBang()
			currentKill.IsHeadshot = e.IsHeadshot
			if len(currentRound.Kills) == 0 {
				currentKill.IsFirstKill = true
			} else {
				currentKill.IsFirstKill = false
			}
			// Attacker
			if e.Killer != nil {
				attackerSteamId := int64(e.Killer.SteamID64)
				currentKill.AttackerSteamId = &attackerSteamId
				currentKill.AttackerName = &e.Killer.Name
				attackerTeamName := e.Killer.TeamState.ClanName() 
				currentKill.AttackerTeam = &attackerTeamName
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
				attackerPoint := gonav.Vector3{X: float32(attackerPos.X), Y: float32(attackerPos.Y), Z: float32(attackerPos.Z)}
				attackerArea := mesh.GetNearestArea(attackerPoint, true)
				var attackerAreaId int64
				attackerAreaPlace := ""
				if attackerArea != nil {
					currentKill.IsFlashed = e.Killer.IsBlinded()
					attackerAreaId = int64(attackerArea.ID)
					if attackerArea.Place != nil {
						attackerAreaPlace = attackerArea.Place.Name
					} else {
						attackerAreaPlace = findAreaPlace(attackerArea, mesh)
					}
				}
				currentKill.AttackerAreaId = &attackerAreaId
				currentKill.AttackerAreaName = &attackerAreaPlace
				currentKill.AttackerX = &attackerPos.X
				currentKill.AttackerY = &attackerPos.Y
				currentKill.AttackerZ = &attackerPos.Z
				attackerViewX := float64(e.Killer.ViewDirectionX())
				attackerViewY := float64(e.Killer.ViewDirectionY())
				currentKill.AttackerViewX = &attackerViewX
				currentKill.AttackerViewY = &attackerViewY
			}
			// Victim
			victimSteamId := int64(e.Victim.SteamID64)
			currentKill.VictimSteamId = &victimSteamId
			currentKill.VictimName = &e.Victim.Name
			victimTeamName := e.Victim.TeamState.ClanName() 
			currentKill.VictimTeam = &victimTeamName
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
			victimPoint := gonav.Vector3{X: float32(victimPos.X), Y: float32(victimPos.Y), Z: float32(victimPos.Z)}
			victimArea := mesh.GetNearestArea(victimPoint, true)
			var victimAreaId int64
			victimAreaPlace := ""
			if victimArea != nil {
				victimAreaId = int64(victimArea.ID)
				if victimArea.Place != nil {
					victimAreaPlace = victimArea.Place.Name
				} else {
					victimAreaPlace = findAreaPlace(victimArea, mesh)
				}
			}
			currentKill.VictimAreaId = &victimAreaId
			currentKill.VictimAreaName = &victimAreaPlace
			currentKill.VictimX = &victimPos.X
			currentKill.VictimY = &victimPos.Y
			currentKill.VictimZ = &victimPos.Z
			victimViewX := float64(e.Victim.ViewDirectionX())
			victimViewY := float64(e.Victim.ViewDirectionY())
			currentKill.VictimViewX = &victimViewX
			currentKill.VictimViewY = &victimViewY
			// Assister
			if e.Assister != nil {
				assistSteamId := int64(e.Assister.SteamID64)
				currentKill.AssisterSteamId = &assistSteamId
				currentKill.AssisterName = &e.Assister.Name
				assistTeamName := e.Assister.TeamState.ClanName() 
				currentKill.AssisterTeam = &assistTeamName
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
				assisterPos := e.Assister.LastAlivePosition
				assisterPoint := gonav.Vector3{X: float32(assisterPos.X), Y: float32(assisterPos.Y), Z: float32(assisterPos.Z)}
				assisterArea := mesh.GetNearestArea(assisterPoint, true)
				var assisterAreaId int64
				assisterAreaPlace := ""
				if assisterArea != nil {
					assisterAreaId = int64(assisterArea.ID)
					if assisterArea.Place != nil {
						assisterAreaPlace = assisterArea.Place.Name
					} else {
						assisterAreaPlace = findAreaPlace(assisterArea, mesh)
					}
				}
				currentKill.AssisterAreaId = &assisterAreaId
				currentKill.AssisterAreaName = &assisterAreaPlace
				currentKill.AssisterX = &assisterPos.X
				currentKill.AssisterY = &assisterPos.Y
				currentKill.AssisterZ = &assisterPos.Z
			}
			if len(currentRound.Kills) > 0 {
				currentKill.IsTrade = isTrade(currentRound.Kills[len(currentRound.Kills)-1], currentKill)
			}
			// add
			currentRound.Kills = append(currentRound.Kills, currentKill)
		}
	})

	// Parse damage events
	p.RegisterEventHandler(func(e events.PlayerHurt) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) {
			currentDamage := DamageAction{}
			currentDamage.Tick = int64(gs.IngameTick())
			currentDamage.Second = (float64(currentDamage.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			currentDamage.Weapon = e.Weapon.String()
			currentDamage.HitGroup = convertHitGroup(e.HitGroup)
			currentDamage.HpDamage = int64(e.HealthDamage)
			if e.HealthDamage >= e.Player.Health() {
				currentDamage.KillHpDamage = int64(e.Player.Health())
			} else {
				currentDamage.KillHpDamage = currentDamage.HpDamage
			}
			currentDamage.ArmorDamage = int64(e.ArmorDamage)

			// Attacker
			if e.Attacker != nil {
				attackerSteamId := int64(e.Attacker.SteamID64)
				currentDamage.AttackerSteamId = &attackerSteamId
				currentDamage.AttackerName = &e.Attacker.Name
				attackerTeamName := e.Attacker.TeamState.ClanName() 
				currentDamage.AttackerTeam = &attackerTeamName
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
				attackerPoint := gonav.Vector3{X: float32(attackerPos.X), Y: float32(attackerPos.Y), Z: float32(attackerPos.Z)}
				attackerArea := mesh.GetNearestArea(attackerPoint, true)
				var attackerAreaId int64
				attackerAreaPlace := ""
				if attackerArea != nil {
					attackerAreaId = int64(attackerArea.ID)
					if attackerArea.Place != nil {
						attackerAreaPlace = attackerArea.Place.Name
					} else {
						attackerAreaPlace = findAreaPlace(attackerArea, mesh)
					}
				}
				currentDamage.AttackerAreaId = &attackerAreaId
				currentDamage.AttackerAreaName = &attackerAreaPlace
				currentDamage.AttackerX = &attackerPos.X
				currentDamage.AttackerY = &attackerPos.Y
				currentDamage.AttackerZ = &attackerPos.Z
				attackerViewX := float64(e.Attacker.ViewDirectionX())
				attackerViewY := float64(e.Attacker.ViewDirectionY())
				currentDamage.AttackerViewX = &attackerViewX
				currentDamage.AttackerViewY = &attackerViewY
			}
			if e.Player != nil {
				// Victim
				victimSteamId := int64(e.Player.SteamID64)
				currentDamage.VictimSteamId = &victimSteamId
				currentDamage.VictimName = &e.Player.Name
				victimTeamName := e.Player.TeamState.ClanName() 
				currentDamage.VictimTeam = &victimTeamName
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
				victimPoint := gonav.Vector3{X: float32(victimPos.X), Y: float32(victimPos.Y), Z: float32(victimPos.Z)}
				victimArea := mesh.GetNearestArea(victimPoint, true)
				var victimAreaId int64
				victimAreaPlace := ""
				if victimArea != nil {
					victimAreaId = int64(victimArea.ID)
					if victimArea.Place != nil {
						victimAreaPlace = victimArea.Place.Name
					} else {
						victimAreaPlace = findAreaPlace(victimArea, mesh)
					}
				}
				currentDamage.VictimAreaId = &victimAreaId
				currentDamage.VictimAreaName = &victimAreaPlace
				currentDamage.VictimX = &victimPos.X
				currentDamage.VictimY = &victimPos.Y
				currentDamage.VictimZ = &victimPos.Z
				victimViewX := float64(e.Player.ViewDirectionX())
				victimViewY := float64(e.Player.ViewDirectionY())
				currentDamage.VictimViewX = &victimViewX
				currentDamage.VictimViewY = &victimViewY
			}
			// add
			currentRound.Damages = append(currentRound.Damages, currentDamage)
		}
	})

	// Parse a demo frame. If parse rate is 1, then every frame is parsed. If parse rate is 2, then every 2 frames is parsed, and so on
	p.RegisterEventHandler(func(e events.FrameDone) {
		gs := p.GameState()

		if (acceptableGamePhase(gs)) && (roundInFreezetime == 0) && (currentFrameIdx == 0) {
			currentFrame := GameFrame{}
			currentFrame.Tick = int64(gs.IngameTick())
			currentFrame.Second = (float64(currentFrame.Tick)-float64(currentRound.FreezeTimeEnd))/float64(currentGame.TickRate)
			// Parse bomb distance
			bombsiteA := mesh.GetPlaceByName("BombsiteA")
			aCenter, _ := bombsiteA.GetEstimatedCenter()
			aArea := mesh.GetNearestArea(aCenter, false)
			bombsiteB := mesh.GetPlaceByName("BombsiteB")
			bCenter, _ := bombsiteB.GetEstimatedCenter()
			bArea := mesh.GetNearestArea(bCenter, false)
			bombPos := gs.Bomb().Position()
			bombPosVector := gonav.Vector3{X: float32(bombPos.X), Y: float32(bombPos.Y), Z: float32(bombPos.Z)}
			bombLocArea := mesh.GetNearestArea(bombPosVector, true)
			pathA, _ := gonav.SimpleBuildShortestPath(bombLocArea, aArea)
			currentFrame.BombDistToA = int64(len(pathA.Nodes))
			pathB, _ := gonav.SimpleBuildShortestPath(bombLocArea, bArea)
			currentFrame.BombDistToB = int64(len(pathB.Nodes))
			// Parse T
			currentFrame.T = TeamFrameInfo{}
			currentFrame.T.Side = "T"
			currentFrame.T.Team = gs.TeamTerrorists().ClanName()
			currentFrame.T.CurrentEqVal = int64(gs.TeamTerrorists().CurrentEquipmentValue())
			tPlayers := gs.TeamTerrorists().Members()
			for _, p := range tPlayers {
				currentFrame.T.Players = append(currentFrame.T.Players, parsePlayer(p, mesh))
			}
			tPlayerPlaces := createAlivePlayerSlice(currentFrame.T.Players)
			tToken := createCountToken(tPlayerPlaces, placeSl)
			currentFrame.T.PosToken = tToken
			currentFrame.T.AlivePlayers = countAlivePlayers(currentFrame.T.Players)
			currentFrame.T.TotalUtility = countUtility(currentFrame.T.Players)
			currentFrame.T.UtilityLevel = determineUtilityLevel(currentFrame.T.TotalUtility)
			// Parse CT
			currentFrame.CT = TeamFrameInfo{}
			currentFrame.CT.Side = "CT"
			currentFrame.CT.Team = gs.TeamCounterTerrorists().ClanName()
			currentFrame.CT.CurrentEqVal = int64(gs.TeamCounterTerrorists().CurrentEquipmentValue())
			ctPlayers := gs.TeamCounterTerrorists().Members()
			for _, p := range ctPlayers {
				currentFrame.CT.Players = append(currentFrame.CT.Players, parsePlayer(p, mesh))
			}
			ctPlayerPlaces := createAlivePlayerSlice(currentFrame.CT.Players)
			ctToken := createCountToken(ctPlayerPlaces, placeSl)
			currentFrame.CT.PosToken = ctToken
			currentFrame.CT.AlivePlayers = countAlivePlayers(currentFrame.CT.Players)
			currentFrame.CT.TotalUtility = countUtility(currentFrame.CT.Players)
			currentFrame.CT.UtilityLevel = determineUtilityLevel(currentFrame.CT.TotalUtility)
			currentFrame.TToken = tToken
			currentFrame.CTToken = ctToken
			currentFrame.FrameToken = tToken + ctToken
			// Parse world (grenade) objects
			allGrenades := gs.GrenadeProjectiles()
			for _, ele := range allGrenades {
				currentWorldObj := WorldObject{}
				currentWorldObj.ObjType = ele.WeaponInstance.String()
				objPos := ele.Trajectory[len(ele.Trajectory)-1]
				objPoint := gonav.Vector3{X: float32(objPos.X), Y: float32(objPos.Y), Z: float32(objPos.Z)}
				objArea := mesh.GetNearestArea(objPoint, true)
				var objAreaId int64
				objAreaPlace := ""
				if objArea != nil {
					objAreaId = int64(objArea.ID)
					if objArea.Place != nil {
						objAreaPlace = objArea.Place.Name
					} else {
						objAreaPlace = findAreaPlace(objArea, mesh)
					}
				}
				currentWorldObj.AreaId = objAreaId
				currentWorldObj.AreaName = objAreaPlace
				currentWorldObj.X = float64(objPos.X)
				currentWorldObj.Y = float64(objPos.Y)
				currentWorldObj.Z = float64(objPos.Z)
				currentFrame.World = append(currentFrame.World, currentWorldObj)
			}
			// Parse bomb
			bombObj := gs.Bomb()
			currentWorldObj := WorldObject{}
			currentWorldObj.ObjType = "bomb"
			objPos := bombObj.Position()
			objPoint := gonav.Vector3{X: float32(objPos.X), Y: float32(objPos.Y), Z: float32(objPos.Z)}
			objArea := mesh.GetNearestArea(objPoint, true)
			var objAreaId int64
			objAreaPlace := ""
			if objArea != nil {
				objAreaId = int64(objArea.ID)
				if objArea.Place != nil {
					objAreaPlace = objArea.Place.Name
				} else {
					objAreaPlace = findAreaPlace(objArea, mesh)
				}
			}
			currentWorldObj.AreaId = objAreaId
			currentWorldObj.AreaName = objAreaPlace
			currentWorldObj.X = float64(objPos.X)
			currentWorldObj.Y = float64(objPos.Y)
			currentWorldObj.Z = float64(objPos.Z)
			currentFrame.World = append(currentFrame.World, currentWorldObj)
			// add
			currentRound.Frames = append(currentRound.Frames, currentFrame)
			currentFrameIdx = currentFrameIdx + 1
		} else {
			if currentFrameIdx == currentGame.ParseRate {
				currentFrameIdx = 0
			} else {
				currentFrameIdx = currentFrameIdx + 1
			}
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	checkError(err)

	InfoLogger.Println("Parsed %s", demPath)

	/* Clean the JSON

	1) If the initial round scores are not 0-0, change it.
	*/
	if len(currentGame.Rounds) > 0 {
		InfoLogger.Println("Cleaning data")

		// Remove knife round if there
		firstRound := currentGame.Rounds[0]
		knifeKills := 0
		for _, k := range firstRound.Kills {
			if k.Weapon == "Knife" {
				knifeKills = knifeKills + 1
			}
		}
		if knifeKills >= 3 {
			currentGame.Rounds = currentGame.Rounds[1:len(currentGame.Rounds)]
		}

		// Set first round scores to 0
		if currentGame.Rounds[0].TScore != 0 {
			currentGame.Rounds[0].TScore = 0
		}
		if currentGame.Rounds[0].CTScore != 0 {
			currentGame.Rounds[0].CTScore = 0
		}

		/* Find the starting round. Starting round is defined as the first 0-0 round which has following rounds.
		*/
		startIdx := 0
		for i, r := range currentGame.Rounds {
			if (i < len(currentGame.Rounds)-1) {
				if (r.TScore + r.CTScore == 0) && (currentGame.Rounds[i+1].TScore + currentGame.Rounds[i+1].CTScore > 0) {
					startIdx = i
				}
			}
		}
		currentGame.Rounds = currentGame.Rounds[startIdx:len(currentGame.Rounds)]
		for i, _ := range currentGame.Rounds {
			currentGame.Rounds[i].RoundNum = int64(i+1)
		}
		/* Fix the rounds to have pistol rounds instead of ecos
		*/
		for i, _ := range currentGame.Rounds {
			if (i == 0 || i == 15) {
				currentGame.Rounds[i].CTBuyType = "Pistol"
				currentGame.Rounds[i].TBuyType = "Pistol"
			}
		}

		/* Now see if there are any remaining weird rounds
		*/
		//if (currentGame.Rounds[len(currentGame.Rounds)-1].TScore + currentGame.Rounds[len(currentGame.Rounds)-1].CTScore) < (currentGame.Rounds[len(currentGame.Rounds)-2].TScore + currentGame.Rounds[len(currentGame.Rounds)-2].CTScore) {
		//	currentGame.Rounds = currentGame.Rounds[:len(currentGame.Rounds)-1]
		//}
	
		InfoLogger.Println("Cleaned data, writing to JSON file")

		// Write the JSON
		file, _ := json.MarshalIndent(currentGame, "", " ")
		// currentGame.MatchName + ".json"
		_ = ioutil.WriteFile(outpath + "/" + currentGame.MatchName + ".json", file, 0644)
		
		InfoLogger.Println("Wrote to JSON file to: " + outpath + "/" + currentGame.MatchName + ".json")
	}
}

// Function to handle errors
func checkError(err error) {
	if err != nil {
		ErrorLogger.Println("DEMO STREAM ERROR")
		WarningLogger.Println("Demo stream errors can still write output, check for JSON file")
		ErrorLogger.Println(err.Error())
	}
}
