package main

import (
	"fmt"
	"os"

	dem "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs"
	common "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/common"
	events "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/events"
	ex "github.com/markus-wa/demoinfocs-golang/v2/examples"
	gonav "github.com/pnxenopoulos/csgonavparse"
)

func printPlayer(p *common.Player, m gonav.NavMesh) {
	playerPos := p.Position()
	playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
	area := m.GetNearestArea(playerPoint, true)
	var areaId uint32 = 0
	areaPlace := ""
	if area != nil {
		areaId = area.ID
		if area.Place != nil {
			areaPlace = area.Place.Name
		}
	}
	fmt.Printf("<player id='%d' name='%s' hp='%d' armor='%d' eqVal='%d' hasDefuse='%v' hasHelmet='%v' posX='%f' posY='%f' posZ='%f' areaName='%s' areaId='%d' /> \n", p.SteamID64, p.Name, p.Health(), p.Armor(), p.EquipmentValueCurrent(), p.HasDefuseKit(), p.HasHelmet(), playerPos.X, playerPos.Y, playerPos.Z, areaPlace, areaId)
}

func printTeam(ts *common.TeamState, side string, m gonav.NavMesh) {
	fmt.Printf("<team side='%s' name='%s' eqVal='%d' startEqVal ='%d'> \n", side, ts.ClanName(), ts.CurrentEquipmentValue(), ts.FreezeTimeEndEquipmentValue())
	teamPlayers := ts.Members()
	for _, p := range teamPlayers {
		printPlayer(p, m)
	}
	fmt.Printf("</team> \n")
}
	
func printGameFrame(gs dem.GameState, m gonav.NavMesh) {
	fmt.Printf("<frame tick='%d'> \n", gs.IngameTick())
	ctSide := gs.TeamCounterTerrorists()
	tSide := gs.TeamTerrorists()
	printTeam(ctSide, "CT", m)
	printTeam(tSide, "T", m)
	fmt.Printf("</frame> \n")
}

// Run parser as follows: go run parse_demo.go -demo /path/to/demo.dem
func main() {
	// Read in demofile
	f, err := os.Open(ex.DemoPathFromArgs())
	defer f.Close()
	checkError(err)

	// Create new demoparser
	p := dem.NewParser(f)

	// Parse demofile header
	header, err := p.ParseHeader()
	checkError(err)

	// Get nav mesh given the map name

	currentMap := header.MapName

	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()

	// Create flags
	roundStarted := 0

	// [PRINT] Starter <game> tag
	fmt.Printf("<game map='%s'> \n", currentMap)

	// [PRINT] Round starts
	p.RegisterEventHandler(func(e events.RoundStart) {		

		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (matchStarted == true) {
			roundStarted = 1
			fmt.Printf("<round startTick='%d' tScore='%d' ctScore='%d'> \n", gs.IngameTick(), gs.TeamTerrorists().Score(), gs.TeamCounterTerrorists().Score())
		}
	})

	// [PRINT] Round ends
	p.RegisterEventHandler(func(e events.RoundEnd) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (matchStarted == true) && (roundStarted == 1) {
			winningTeam := "CT"
			switch e.Winner {
			case common.TeamTerrorists:
				winningTeam = "T"
			case common.TeamCounterTerrorists:
				winningTeam = "CT"
			default:
				winningTeam = "CT"
			}
			fmt.Printf("<roundEnd endTick='%d' winningTeam='%s' reason='%d' /> \n", gs.IngameTick(), winningTeam, e.Reason)
			fmt.Printf("</round> \n")
			roundStarted = 0
		}
	})

	// [PRINT] Events
	p.RegisterEventHandler(func(e events.PlayerHurt) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (matchStarted == true) && (roundStarted == 1) {
			printGameFrame(gs, mesh)
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	checkError(err)

	// Print end game
	fmt.Printf("</game>")
}

// Function to handle errors
func checkError(err error) {
	if err != nil {
		fmt.Printf("[ERROR] Demo Stream Error")
	}
}
