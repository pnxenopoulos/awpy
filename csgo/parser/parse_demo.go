package main

import (
	"fmt"
	"os"

	dem "github.com/markus-wa/demoinfocs-golang"
	common "github.com/markus-wa/demoinfocs-golang/common"
	events "github.com/markus-wa/demoinfocs-golang/events"
	ex "github.com/markus-wa/demoinfocs-golang/examples"
)

// Run parser as follows: go run parse_demofile.go -demo /path/to/demo.dem
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

	/* Get nav mesh given the map name
	Original nav files only exists for the following maps:
		- de_cbble
		- de_dust2
		- de_inferno
		- de_mirage
		- de_nuke
		- de_overpass
		- de_train
		- de_vertigo
	*/

	currentMap := header.MapName
	//mapMetadata := metadata.MapNameToMap[currentMap]

	//fNav, _ := os.Open("../data/original_nav_files/" + currentMap + ".nav")
	//parserNav := gonav.Parser{Reader: fNav}
	//mesh, _ := parserNav.Parse()

	// Create list of empty structs
	var gamePlayerIDs []int64

	// Print map name
	fmt.Printf("[MAP NAME] [%s] \n", currentMap)

	// Parse match starts
	p.RegisterEventHandler(func(e events.MatchStart) {
		gs := p.GameState()
		warmup := gs.IsWarmupPeriod()

		// Only parse non-warmup match starts
		if warmup == false {
			fmt.Printf("[MATCH START] [%d] \n", gs.IngameTick())
		}
	})

	// Parse round starts
	p.RegisterEventHandler(func(e events.RoundStart) {
		gs := p.GameState()
		warmup := gs.IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {
			fmt.Printf("[ROUND START] [%d] [%d, %d] \n", gs.IngameTick(), gs.TeamTerrorists().Score, gs.TeamCounterTerrorists().Score)
		}
	})

	// Parse round ends (non-official)
	p.RegisterEventHandler(func(e events.RoundEnd) {
		gs := p.GameState()
		warmup := gs.IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {

			// Print team buy info
			fmt.Printf("[ROUND PURCHASE] [%d] [T, %d, %d, %d] [CT, %d, %d, %d] \n",
				gs.IngameTick(),
				gs.TeamTerrorists().CashSpentTotal(),
				gs.TeamTerrorists().CashSpentThisRound(),
				gs.TeamTerrorists().FreezeTimeEndEquipmentValue(),
				gs.TeamCounterTerrorists().CashSpentTotal(),
				gs.TeamCounterTerrorists().CashSpentThisRound(),
				gs.TeamCounterTerrorists().FreezeTimeEndEquipmentValue(),
			)

			switch e.Winner {
			case common.TeamTerrorists:
				// Winner's score + 1 because it hasn't actually been updated yet
				fmt.Printf("[ROUND END] [%d] [%d, %d] [T, %s, %s, %d] \n", gs.IngameTick(), gs.TeamTerrorists().Score+1, gs.TeamCounterTerrorists().Score, gs.TeamTerrorists().ClanName, gs.TeamCounterTerrorists().ClanName, e.Reason)
			case common.TeamCounterTerrorists:
				fmt.Printf("[ROUND END] [%d] [%d, %d] [CT, %s, %s, %d] \n", gs.IngameTick(), gs.TeamTerrorists().Score, gs.TeamCounterTerrorists().Score+1, gs.TeamCounterTerrorists().ClanName, gs.TeamTerrorists().ClanName, e.Reason)
			default:
				/* It is currently unknown why rounds may end as draws. Markuswa
				suggested that it may be due to match medic. [NOTE]
				*/
				fmt.Printf("[ROUND END] [%d] DRAW \n", gs.IngameTick())
			}

		}
	})

	// Parse official round ends
	p.RegisterEventHandler(func(e events.RoundEndOfficial) {
		gs := p.GameState()
		warmup := gs.IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {
			fmt.Printf("[ROUND END OFFICIAL] [%d] \n", gs.IngameTick())
		}
	})

	// Parse footsteps
	p.RegisterEventHandler(func(e events.Footstep) {
		gs := p.GameState()
		warmup := gs.IsWarmupPeriod()

		// Only parse non-warmup match starts
		if warmup == false {
			playerExists := false
			for _, element := range gamePlayerIDs {
				if element == e.Player.SteamID {
					playerExists = true
					fmt.Printf("[FOOTSTEP] [%d] [%f %f %f] \n",
						e.Player.SteamID,
						e.Player.Position.X, e.Player.Position.Y, e.Player.Position.Z)
				}
			}
			if playerExists == false {
				gamePlayerIDs = append(gamePlayerIDs, e.Player.SteamID)
				fmt.Printf("[NEW PLAYER] [%d %s %s] \n", e.Player.SteamID, e.Player.Name, e.Player.TeamState.ClanName)
				fmt.Printf("[FOOTSTEP] [%d] [%f %f %f] \n",
					e.Player.SteamID,
					e.Player.Position.X, e.Player.Position.Y, e.Player.Position.Z)
			}
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	checkError(err)
}

// Function to handle errors
func checkError(err error) {
	if err != nil {
		fmt.Printf("[ERROR] Demo Stream Error")
	}
}
