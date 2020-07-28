package main

import (
	"fmt"
	"os"

	dem "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs"
	common "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/common"
	events "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/events"
	ex "github.com/markus-wa/demoinfocs-golang/v2/examples"
	metadata "github.com/markus-wa/demoinfocs-golang/v2/pkg/demoinfocs/metadata"
	gonav "github.com/pnxenopoulos/csgonavparse"
)

func printPlayer(p *common.Player, m gonav.NavMesh, mapMetadata metadata.Map) {
	playerPos := p.Position()
	playerPoint := gonav.Vector3{X: float32(playerPos.X), Y: float32(playerPos.Y), Z: float32(playerPos.Z)}
	area := m.GetNearestArea(playerPoint, true)
	XViz, YViz := mapMetadata.TranslateScale(playerPos.X, playerPos.Y)
	var areaId uint32 = 0
	areaPlace := ""
	if area != nil {
		areaId = area.ID
		if area.Place != nil {
			areaPlace = area.Place.Name
		}
	}
	fmt.Printf("<Player SteamId='%d' PlayerName='%s' Hp='%d' Armor='%d' EqVal='%d' HasDefuse='%v' HasHelmet='%v' X='%f' Y='%f' Z='%f' XViz='%f' YViz='%f' AreaName='%s' AreaId='%d' /> \n", p.SteamID64, p.Name, p.Health(), p.Armor(), p.EquipmentValueCurrent(), p.HasDefuseKit(), p.HasHelmet(), playerPos.X, playerPos.Y, playerPos.Z, XViz, YViz, areaPlace, areaId)
}

func printTeam(ts *common.TeamState, side string, m gonav.NavMesh, mapMetadata metadata.Map) {
	fmt.Printf("<Team Side='%s' TeamName='%s' EqVal='%d'> \n", side, ts.ClanName(), ts.CurrentEquipmentValue())
	teamPlayers := ts.Members()
	for _, p := range teamPlayers {
		printPlayer(p, m, mapMetadata)
	}
	fmt.Printf("</Team> \n")
}
	
func printGameFrame(gs dem.GameState, m gonav.NavMesh, st int, mapMetadata metadata.Map) {
	fmt.Printf("<Frame Tick='%d' TicksSinceStart='%d'> \n", gs.IngameTick(), (gs.IngameTick()-st))
	ctSide := gs.TeamCounterTerrorists()
	tSide := gs.TeamTerrorists()
	printTeam(ctSide, "CT", m, mapMetadata)
	printTeam(tSide, "T", m, mapMetadata)
	fmt.Printf("</Frame> \n")
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
	mapMetadata := metadata.MapNameToMap[currentMap]

	fNav, _ := os.Open("../data/nav/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()

	// Create flags
	roundStarted := 0
	roundStartTick := 0
	bombSite := ""

	// [PRINT] Starter <game> tag
	fmt.Printf("<Game Map='%s'> \n", currentMap)

	// [PRINT] Round starts
	p.RegisterEventHandler(func(e events.RoundStart) {		

		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		// matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 0) {
			bombSite = ""
			roundStarted = 1
			roundStartTick = gs.IngameTick()
			fmt.Printf("<Round StartTick='%d' TScore='%d' CTScore='%d'> \n", gs.IngameTick(), gs.TeamTerrorists().Score(), gs.TeamCounterTerrorists().Score())
		}
	})

	// [PRINT] Round ends
	p.RegisterEventHandler(func(e events.RoundEnd) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		// matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			winningTeam := "CT"
			switch e.Winner {
			case common.TeamTerrorists:
				winningTeam = "T"
			case common.TeamCounterTerrorists:
				winningTeam = "CT"
			default:
				winningTeam = "CT"
			}
			fmt.Printf("<RoundEnd EndTick='%d' WinningSide='%s' Reason='%d' /> \n", gs.IngameTick(), winningTeam, e.Reason)
			fmt.Printf("</Round> \n")
			bombSite = ""
			roundStarted = 0
		}
	})

	// [PRINT] Events
	p.RegisterEventHandler(func(e events.BombPlanted) {
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup bomb plants
		if (warmup == false) && (roundStarted == 1) {
			if e.Site == 65 {
				bombSite = "A"
			} else if e.Site == 66 {
				bombSite = "B"
			}
		}
	})

	/* p.RegisterEventHandler(func(e events.FrameDone) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()
		// matchStarted := p.GameState().IsMatchStarted()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata, bombSite)
		}
	}) */

	p.RegisterEventHandler(func(e events.PlayerHurt) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata)
		}
	})

	p.RegisterEventHandler(func(e events.Footstep) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata)
		}
	})

	p.RegisterEventHandler(func(e events.Kill) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata)
		}
	})

	p.RegisterEventHandler(func(e events.PlayerJump) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata)
		}
	})

	p.RegisterEventHandler(func(e events.ItemPickup) {
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if (warmup == false) && (roundStarted == 1) {
			printGameFrame(gs, mesh, roundStartTick, mapMetadata)
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	checkError(err)

	// Print end game
	if (roundStarted == 1) {
		fmt.Printf("</Round> \n")
	}
	fmt.Printf("</Game>")
}

// Function to handle errors
func checkError(err error) {
	if err != nil {
		fmt.Printf("[ERROR] Demo Stream Error")
	}
}
