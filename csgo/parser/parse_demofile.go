package main

import (
	"fmt"
	"os"

	dem "github.com/markus-wa/demoinfocs-golang"
	common "github.com/markus-wa/demoinfocs-golang/common"
	events "github.com/markus-wa/demoinfocs-golang/events"
	ex "github.com/markus-wa/demoinfocs-golang/examples"
	metadata "github.com/markus-wa/demoinfocs-golang/metadata"
	"github.com/mrazza/gonav"
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
	Keep in mind that original nav files only exists for the following maps:
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
	mapMetadata := metadata.MapNameToMap[currentMap]

	fNav, _ := os.Open("../data/original_nav_files/" + currentMap + ".nav")
	parserNav := gonav.Parser{Reader: fNav}
	mesh, _ := parserNav.Parse()

	p.RegisterEventHandler(func(e events.PlayerHurt) {
		/* Parse player damage events
		 */
		warmup := p.GameState().IsWarmupPeriod()
		started := p.GameState().IsMatchStarted()

		// Only parse non-warmup player hurt events
		if warmup == false && started == true {
			// First block (game state)
			gameTick := p.GameState().IngameTick()
			var mapName string = header.MapName

			// Second block (victim location)
			var victimX float64 = 0.0
			var victimY float64 = 0.0
			var victimZ float64 = 0.0
			var VictimXViz float64 = 0.0
			var VictimYViz float64 = 0.0
			var VictimClosestAreaID uint32 = 0
			var VictimClosestAreaName string = "NA"
			var VictimViewX float32 = 0.0
			var VictimViewY float32 = 0.0

			// Third block (attacker location)
			var attackerX float64 = 0.0
			var attackerY float64 = 0.0
			var attackerZ float64 = 0.0
			var attackerXViz float64 = 0.0
			var attackerYViz float64 = 0.0
			var attackerClosestAreaID uint32 = 0
			var attackerClosestAreaName string = "NA"
			var attackerViewX float32 = 0.0
			var attackerViewY float32 = 0.0

			// Fourth block (victim player/team)
			var victimID int64 = 0
			var victimName string = "NA"
			var victimTeam string = "NA"
			var victimSide common.Team
			var victimSideString string = "NA"
			var victimTeamEqVal int = 0

			// Fifth block (attacker player/team)
			var attackerID int64 = 0
			var attackerName string = "NA"
			var attackerTeam string = "NA"
			var attackerSide common.Team
			var attackerSideString string = "NA"
			var attackerTeamEqVal int = 0

			// Sixth block (Damage/Weapon)
			hpDmg := e.HealthDamage
			KillHpDmg := hpDmg

			/* If a player has more than 100 damage taken, squash this value back
			down to 100. This may need to be changed in the future. [NOTE]
			*/

			if hpDmg > 100 {
				KillHpDmg = 100
			}
			armorDmg := e.ArmorDamage
			weaponID := e.Weapon.Weapon
			hitGroup := e.HitGroup

			// Find victim values
			if e.Player == nil {
				victimID = 0
			} else {
				victimID = e.Player.SteamID
				victimX = e.Player.Position.X
				victimY = e.Player.Position.Y
				victimZ = e.Player.Position.Z
				VictimXViz, VictimYViz = mapMetadata.TranslateScale(victimX, victimY)
				VictimViewX = e.Player.ViewDirectionX
				VictimViewY = e.Player.ViewDirectionY
				victimLoc := gonav.Vector3{X: float32(victimX), Y: float32(victimY), Z: float32(victimZ)}
				victimArea := mesh.GetNearestArea(victimLoc, true)
				if victimArea != nil {
					VictimClosestAreaID = victimArea.ID
					if victimArea.Place != nil {
						VictimClosestAreaName = victimArea.Place.Name
					}
				}
				victimName = e.Player.Name
				victimTeam = e.Player.TeamState.ClanName
				victimSide = e.Player.Team
				if victimSide == 2 {
					victimSideString = "T"
				} else if victimSide == 3 {
					victimSideString = "CT"
				}
				victimTeamEqVal = e.Player.TeamState.RoundStartEquipmentValue()
			}

			// Find attacker values
			if e.Attacker == nil {
				attackerID = 0
			} else {
				attackerID = e.Attacker.SteamID
				attackerX = e.Attacker.Position.X
				attackerY = e.Attacker.Position.Y
				attackerZ = e.Attacker.Position.Z
				attackerXViz, attackerYViz = mapMetadata.TranslateScale(attackerX, attackerY)
				attackerViewX = e.Attacker.ViewDirectionX
				attackerViewY = e.Attacker.ViewDirectionY
				attackerLoc := gonav.Vector3{X: float32(attackerX), Y: float32(attackerY), Z: float32(attackerZ)}
				attackerArea := mesh.GetNearestArea(attackerLoc, true)
				if attackerArea != nil {
					attackerClosestAreaID = attackerArea.ID
					if attackerArea.Place != nil {
						attackerClosestAreaName = attackerArea.Place.Name
					}
				}
				attackerName = e.Attacker.Name
				attackerTeam = e.Attacker.TeamState.ClanName
				attackerSide = e.Attacker.Team
				if attackerSide == 2 {
					attackerSideString = "T"
				} else if attackerSide == 3 {
					attackerSideString = "CT"
				}
				attackerTeamEqVal = e.Attacker.TeamState.RoundStartEquipmentValue()
			}

			// Print a line of the damage information
			fmt.Printf("[DAMAGE] [%s, %d] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%d, %s, %s, %s, %d] [%d, %s, %s, %s, %d] [%d, %d, %d, %d, %d] \n",
				mapName, gameTick,
				victimX, victimY, victimZ, VictimXViz, VictimYViz, VictimViewX, VictimViewY, VictimClosestAreaID, VictimClosestAreaName,
				attackerX, attackerY, attackerZ, attackerXViz, attackerYViz, attackerViewX, attackerViewY, attackerClosestAreaID, attackerClosestAreaName,
				victimID, victimName, victimTeam, victimSideString, victimTeamEqVal,
				attackerID, attackerName, attackerTeam, attackerSideString, attackerTeamEqVal,
				hpDmg, KillHpDmg, armorDmg, weaponID, hitGroup)
		}
	})

	p.RegisterEventHandler(func(e events.GrenadeEventIf) {
		/* Parse grenade events (except incendiary)
		 */
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup grenade events
		if warmup == false {
			// First block (game state)
			gameTick := p.GameState().IngameTick()
			var mapName string = header.MapName

			// Second block (player info)
			var playerID int64 = 0
			var playerName string = "NA"
			var posX float64 = 0.0
			var posY float64 = 0.0
			var posZ float64 = 0.0
			var posXViz float64 = 0.0
			var posYViz float64 = 0.0
			var playerSide common.Team
			var playerSideString string = "NA"
			var playerTeam string = "NA"
			var areaID uint32 = 0
			var areaPlace string = "NA"

			if e.Base().Thrower == nil {
				playerID = 0
			} else {
				playerID = e.Base().Thrower.SteamID
				//playerName = e.Player.Name
				posX = e.Base().Position.X
				posY = e.Base().Position.Y
				posZ = e.Base().Position.Z
				posXViz, posYViz = mapMetadata.TranslateScale(posX, posY)
				playerSide = e.Base().Thrower.Team
				playerTeam = e.Base().Thrower.TeamState.ClanName
				playerName = e.Base().Thrower.Name
				posPoint := gonav.Vector3{X: float32(posX), Y: float32(posY), Z: float32(posZ)}
				area := mesh.GetNearestArea(posPoint, true)
				if area != nil {
					areaID = area.ID
					if area.Place != nil {
						areaPlace = area.Place.Name
					}
				}

				if playerSide == 2 {
					playerSideString = "T"
				} else if playerSide == 3 {
					playerSideString = "CT"
				}
			}
			grenadeType := e.Base().GrenadeType

			if grenadeType != 503 {
				fmt.Printf("[GRENADE] [%s, %d] [%d, %s, %s, %s] [%f, %f, %f, %f, %f, %d, %s, %d]\n",
					mapName, gameTick,
					playerID, playerName, playerTeam, playerSideString,
					posX, posY, posZ, posXViz, posYViz,
					areaID, areaPlace, grenadeType)
			}
		}
	})

	p.RegisterEventHandler(func(e events.GrenadeProjectileDestroy) {
		/* Parse incendiary grenade events
		 */
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup grenade events
		if warmup == false {
			// First block (game state)
			gameTick := p.GameState().IngameTick()
			var mapName string = header.MapName

			// Second block (player info)
			var playerID int64 = 0
			var playerName string = "NA"
			var posX float64 = 0.0
			var posY float64 = 0.0
			var posZ float64 = 0.0
			var posXViz float64 = 0.0
			var posYViz float64 = 0.0
			var playerSide common.Team
			var playerSideString string = "NA"
			var playerTeam string = "NA"
			var areaID uint32 = 0
			var areaPlace string = "NA"

			if e.Projectile.Thrower == nil {
				playerID = 0
			} else {
				playerID = e.Projectile.Thrower.SteamID
				//playerName = e.Player.Name
				posX = e.Projectile.Position.X
				posY = e.Projectile.Position.Y
				posZ = e.Projectile.Position.Z
				posXViz, posYViz = mapMetadata.TranslateScale(posX, posY)
				playerSide = e.Projectile.Thrower.Team
				playerTeam = e.Projectile.Thrower.TeamState.ClanName
				playerName = e.Projectile.Thrower.Name
				posPoint := gonav.Vector3{X: float32(posX), Y: float32(posY), Z: float32(posZ)}
				area := mesh.GetNearestArea(posPoint, true)
				if area != nil {
					areaID = area.ID
					if area.Place != nil {
						areaPlace = area.Place.Name
					}
				}

				if playerSide == 2 {
					playerSideString = "T"
				} else if playerSide == 3 {
					playerSideString = "CT"
				}
			}
			grenadeType := e.Projectile.WeaponInstance.Weapon

			if grenadeType == 503 {
				fmt.Printf("[GRENADE] [%s, %d] [%d, %s, %s, %s] [%f, %f, %f, %f, %f, %d, %s, %d]\n",
					mapName, gameTick,
					playerID, playerName, playerTeam, playerSideString,
					posX, posY, posZ, posXViz, posYViz,
					areaID, areaPlace, grenadeType)
			}
		}
	})

	p.RegisterEventHandler(func(e events.Kill) {
		/* Parse player kill events
		 */
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup kill events
		if warmup == false {
			// First block (game state)
			gameTick := p.GameState().IngameTick()
			var mapName string = header.MapName

			// Second block (victim location)
			var victimX float64 = 0.0
			var victimY float64 = 0.0
			var victimZ float64 = 0.0
			var VictimXViz float64 = 0.0
			var VictimYViz float64 = 0.0
			var VictimClosestAreaID uint32 = 0
			var VictimClosestAreaName string = "NA"
			var VictimViewX float32 = 0.0
			var VictimViewY float32 = 0.0

			// Third block (attacker location)
			var attackerX float64 = 0.0
			var attackerY float64 = 0.0
			var attackerZ float64 = 0.0
			var attackerXViz float64 = 0.0
			var attackerYViz float64 = 0.0
			var attackerClosestAreaID uint32 = 0
			var attackerClosestAreaName string = "NA"
			var attackerViewX float32 = 0.0
			var attackerViewY float32 = 0.0

			// Fourth block (victim player/team)
			var victimID int64 = 0
			var victimName string = "NA"
			var victimTeam string = "NA"
			var victimSide common.Team
			var victimSideString string = "NA"
			var victimTeamEqVal int = 0

			// Fifth block (attacker player/team)
			var attackerID int64 = 0
			var attackerName string = "NA"
			var attackerTeam string = "NA"
			var attackerSide common.Team
			var attackerSideString string = "NA"
			var attackerTeamEqVal int = 0
			var attackerAssistID int64 = 0
			var attackerAssistName string = "NA"
			var attackerAssistTeam string = "NA"
			var attackerAssistSide common.Team
			var attackerAssistSideString string = "NA"

			// Sixth block (weapon/wallshot/headshot)
			weaponID := e.Weapon.Weapon
			isWallshot := e.PenetratedObjects
			isHeadshot := e.IsHeadshot

			// Find victim values
			if e.Victim == nil {
				victimID = 0
			} else {
				victimID = e.Victim.SteamID
				victimX = e.Victim.Position.X
				victimY = e.Victim.Position.Y
				victimZ = e.Victim.Position.Z
				VictimXViz, VictimYViz = mapMetadata.TranslateScale(victimX, victimY)
				VictimViewX = e.Victim.ViewDirectionX
				VictimViewY = e.Victim.ViewDirectionY
				victimLoc := gonav.Vector3{X: float32(victimX), Y: float32(victimY), Z: float32(victimZ)}
				victimArea := mesh.GetNearestArea(victimLoc, true)
				if victimArea != nil {
					VictimClosestAreaID = victimArea.ID
					if victimArea.Place != nil {
						VictimClosestAreaName = victimArea.Place.Name
					}
				}
				victimName = e.Victim.Name
				victimTeam = e.Victim.TeamState.ClanName
				victimSide = e.Victim.Team
				if victimSide == 2 {
					victimSideString = "T"
				} else if victimSide == 3 {
					victimSideString = "CT"
				}
				victimTeamEqVal = e.Victim.TeamState.RoundStartEquipmentValue()
			}

			// Find attacker values
			if e.Killer == nil {
				attackerID = 0
			} else {
				attackerID = e.Killer.SteamID
				attackerX = e.Killer.Position.X
				attackerY = e.Killer.Position.Y
				attackerZ = e.Killer.Position.Z
				attackerXViz, attackerYViz = mapMetadata.TranslateScale(attackerX, attackerY)
				attackerViewX = e.Killer.ViewDirectionX
				attackerViewY = e.Killer.ViewDirectionY
				attackerLoc := gonav.Vector3{X: float32(attackerX), Y: float32(attackerY), Z: float32(attackerZ)}
				attackerArea := mesh.GetNearestArea(attackerLoc, true)
				if attackerArea != nil {
					attackerClosestAreaID = attackerArea.ID
					if attackerArea.Place != nil {
						attackerClosestAreaName = attackerArea.Place.Name
					}
				}
				attackerName = e.Killer.Name
				attackerTeam = e.Killer.TeamState.ClanName
				attackerSide = e.Killer.Team
				if attackerSide == 2 {
					attackerSideString = "T"
				} else if attackerSide == 3 {
					attackerSideString = "CT"
				}
				attackerTeamEqVal = e.Killer.TeamState.RoundStartEquipmentValue()
			}

			// Find assister values
			if e.Assister == nil {
				attackerAssistID = 0
			} else {
				attackerAssistID = e.Assister.SteamID
				attackerAssistName = e.Assister.Name
				attackerAssistTeam = e.Assister.TeamState.ClanName
				attackerAssistSide = e.Assister.Team
				if attackerAssistSide == 2 {
					attackerAssistSideString = "T"
				} else {
					attackerAssistSideString = "CT"
				}
			}

			// Print a line of the kill information
			fmt.Printf("[KILL] [%s, %d] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%d, %s, %s, %s, %d] [%d, %s, %s, %s, %d] [%d, %s, %s, %s]  [%d, %d, %t] \n",
				mapName, gameTick,
				victimX, victimY, victimZ, VictimXViz, VictimYViz, VictimViewX, VictimViewY, VictimClosestAreaID, VictimClosestAreaName,
				attackerX, attackerY, attackerZ, attackerXViz, attackerYViz, attackerViewX, attackerViewY, attackerClosestAreaID, attackerClosestAreaName,
				victimID, victimName, victimTeam, victimSideString, victimTeamEqVal,
				attackerID, attackerName, attackerTeam, attackerSideString, attackerTeamEqVal,
				attackerAssistID, attackerAssistName, attackerAssistTeam, attackerAssistSideString,
				weaponID, isWallshot, isHeadshot)
		}
	})

	p.RegisterEventHandler(func(e events.RoundStart) {
		/* Parse round start events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {
			fmt.Printf("[ROUND START] [%s, %d] [%d, %d] \n", header.MapName, gs.IngameTick(), gs.TeamTerrorists().Score, gs.TeamCounterTerrorists().Score)
		}
	})

	p.RegisterEventHandler(func(e events.RoundEnd) {
		/* Parse round end events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {
			switch e.Winner {
			case common.TeamTerrorists:
				// Winner's score + 1 because it hasn't actually been updated yet
				fmt.Printf("[ROUND END] [%s, %d] [%d, %d] [T, %s, %s, %d] \n", header.MapName, gs.IngameTick(), gs.TeamTerrorists().Score+1, gs.TeamCounterTerrorists().Score, gs.TeamTerrorists().ClanName, gs.TeamCounterTerrorists().ClanName, e.Reason)
			case common.TeamCounterTerrorists:
				fmt.Printf("[ROUND END] [%s, %d] [%d, %d] [CT, %s, %s, %d] \n", header.MapName, gs.IngameTick(), gs.TeamTerrorists().Score, gs.TeamCounterTerrorists().Score+1, gs.TeamCounterTerrorists().ClanName, gs.TeamTerrorists().ClanName, e.Reason)
			default:
				/* It is currently unknown why rounds may end as draws. Markuswa
				suggested that it may be due to match medic. [NOTE]
				*/
				fmt.Printf("[ROUND END] [%s, %d] DRAW \n", header.MapName, gs.IngameTick())
			}
		}
	})

	p.RegisterEventHandler(func(e events.RoundEndOfficial) {
		/* Parse official round end
		 */

		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup rounds
		if warmup == false {
			fmt.Printf("[ROUND END OFFICIAL] [%s, %d] \n", header.MapName, gs.IngameTick())
		}
	})

	p.RegisterEventHandler(func(e events.MatchStart) {
		/* Parse match start events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup match starts
		if warmup == false {
			fmt.Printf("[MATCH START] [%s, %d] \n", header.MapName, gs.IngameTick())
		}
	})

	p.RegisterEventHandler(func(e events.BombPlanted) {
		/* Parse bomb plant events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bombSite = "None"
			var playerID int64 = 0
			var playerName string = "NA"
			var playerTeam string = "NA"
			var playerX float64 = 0
			var playerY float64 = 0
			var playerZ float64 = 0
			var areaID uint32 = 0

			playerID = e.BombEvent.Player.SteamID
			playerName = e.BombEvent.Player.Name
			playerTeam = e.BombEvent.Player.TeamState.ClanName
			playerX = e.BombEvent.Player.Position.X
			playerY = e.BombEvent.Player.Position.Y
			playerZ = e.BombEvent.Player.Position.Z

			playerPoint := gonav.Vector3{X: float32(playerX), Y: float32(playerY), Z: float32(playerZ)}
			area := mesh.GetNearestArea(playerPoint, true)
			if area != nil {
				areaID = area.ID
			}

			if e.Site == 65 {
				bombSite = "A"
			} else if e.Site == 66 {
				bombSite = "B"
			}
			fmt.Printf("[BOMB PLANT] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
				header.MapName, gs.IngameTick(),
				playerID, playerName, playerTeam,
				playerX, playerY, playerZ, areaID, bombSite)
		}
	})

	p.RegisterEventHandler(func(e events.BombDefused) {
		/* Parse bomb defuse events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bombSite = "None"
			var playerID int64 = 0
			var playerName string = "NA"
			var playerTeam string = "NA"
			var playerX float64 = 0
			var playerY float64 = 0
			var playerZ float64 = 0
			var areaID uint32 = 0

			playerID = e.BombEvent.Player.SteamID
			playerName = e.BombEvent.Player.Name
			playerTeam = e.BombEvent.Player.TeamState.ClanName
			playerX = e.BombEvent.Player.Position.X
			playerY = e.BombEvent.Player.Position.Y
			playerZ = e.BombEvent.Player.Position.Z

			playerPoint := gonav.Vector3{X: float32(playerX), Y: float32(playerY), Z: float32(playerZ)}
			area := mesh.GetNearestArea(playerPoint, true)
			if area != nil {
				areaID = area.ID
			}

			if e.Site == 65 {
				bombSite = "A"
			} else if e.Site == 66 {
				bombSite = "B"
			}
			fmt.Printf("[BOMB DEFUSE] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
				header.MapName, gs.IngameTick(),
				playerID, playerName, playerTeam,
				playerX, playerY, playerZ, areaID, bombSite)
		}
	})

	p.RegisterEventHandler(func(e events.BombDefused) {
		/* Parse bomb explode events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bombSite = "None"
			var playerID int64 = 0
			var playerName string = "NA"
			var playerTeam string = "NA"
			var playerX float64 = 0
			var playerY float64 = 0
			var playerZ float64 = 0
			var areaID uint32 = 0

			playerID = e.BombEvent.Player.SteamID
			playerName = e.BombEvent.Player.Name
			playerTeam = e.BombEvent.Player.TeamState.ClanName
			playerX = e.BombEvent.Player.Position.X
			playerY = e.BombEvent.Player.Position.Y
			playerZ = e.BombEvent.Player.Position.Z

			playerPoint := gonav.Vector3{X: float32(playerX), Y: float32(playerY), Z: float32(playerZ)}
			area := mesh.GetNearestArea(playerPoint, true)
			if area != nil {
				areaID = area.ID
			}

			if e.Site == 65 {
				bombSite = "A"
			} else if e.Site == 66 {
				bombSite = "B"
			}
			fmt.Printf("[BOMB EXPLODE] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
				header.MapName, gs.IngameTick(),
				playerID, playerName, playerTeam,
				playerX, playerY, playerZ, areaID, bombSite)
		}
	})

	p.RegisterEventHandler(func(e events.Footstep) {
		/* Parse player footstep events
		 */
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup footsteps
		if warmup == false {
			var playerID int64 = 0
			var playerName string = "NA"
			var playerX float64 = 0.0
			var playerY float64 = 0.0
			var playerZ float64 = 0.0
			var playerXViz float64 = 0.0
			var playerYViz float64 = 0.0
			var playerViewX float32 = 0.0
			var playerViewY float32 = 0.0
			var playerSide common.Team
			var playerSideString string = "NA"
			var playerTeam string = "NA"
			var areaID uint32 = 0
			var areaPlace string = "NA"
			var distanceBombsiteA int = 999
			var distanceBombsiteB int = 999

			if e.Player == nil {
				playerID = 0
			} else {
				playerID = e.Player.SteamID
				playerX = e.Player.Position.X
				playerY = e.Player.Position.Y
				playerZ = e.Player.Position.Z
				playerViewX = e.Player.ViewDirectionX
				playerViewY = e.Player.ViewDirectionY
				playerXViz, playerYViz = mapMetadata.TranslateScale(playerX, playerY)
				playerSide = e.Player.Team
				playerTeam = e.Player.TeamState.ClanName
				playerName = e.Player.Name
				playerPoint := gonav.Vector3{X: float32(playerX), Y: float32(playerY), Z: float32(playerZ)}
				//area := mesh.GetNearestArea(playerPoint, false)
				//playerPoint := gonav.Vector3{X: float32(1293.267944), Y: float32(1532.817139), Z: float32(1.031250)}
				area := mesh.GetNearestArea(playerPoint, true)
				if area != nil {
					areaID = area.ID
					if area.Place != nil {
						areaPlace = area.Place.Name
					}
				}
				// Bombsite A distance
				bombsiteMeshA := mesh.GetPlaceByName("BombsiteA")
				bombsiteCenterA, _ := bombsiteMeshA.GetEstimatedCenter()
				bombsiteAreaA := mesh.GetNearestArea(bombsiteCenterA, false)
				pathA, _ := gonav.SimpleBuildShortestPath(area, bombsiteAreaA)
				var areasVisitedA int = 0
				for _, currNode := range pathA.Nodes {
					if currNode != nil {
						areasVisitedA = areasVisitedA + 1
					}
				}
				distanceBombsiteA = areasVisitedA
				// Bombsite B distance
				bombsiteMeshB := mesh.GetPlaceByName("BombsiteB")
				bombsiteCenterB, _ := bombsiteMeshB.GetEstimatedCenter()
				bombsiteAreaB := mesh.GetNearestArea(bombsiteCenterB, false)
				pathB, _ := gonav.SimpleBuildShortestPath(area, bombsiteAreaB)
				var areasVisitedB int = 0
				for _, currNode := range pathB.Nodes {
					if currNode != nil {
						areasVisitedB = areasVisitedB + 1
					}
				}
				distanceBombsiteB = areasVisitedB
			}

			if playerSide == 2 {
				playerSideString = "T"
			} else if playerSide == 3 {
				playerSideString = "CT"
			}

			fmt.Printf("[FOOTSTEP] [%s, %d] [%d, %s, %s, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s, %d, %d] \n",
				header.MapName, gs.IngameTick(),
				playerID, playerName, playerTeam, playerSideString,
				playerX, playerY, playerZ, playerXViz, playerYViz, playerViewX, playerViewY,
				areaID, areaPlace, distanceBombsiteA, distanceBombsiteB)
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
