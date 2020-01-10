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

/* TODO:
	- Be sure that if location area ID and name doesn't show, it's probably a problem with nav file paths
*/

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
		- de_dust2
		- de_inferno
		- de_mirage
		- de_nuke
		- de_overpass
		- de_train
	*/
	current_map := header.MapName
	mapMetadata := metadata.MapNameToMap[current_map]

	f_nav, _ := os.Open("../data/original_nav_files/" + current_map + ".nav")
	parser_nav := gonav.Parser{Reader: f_nav}
	mesh, _ := parser_nav.Parse()

	//bombsiteB := mesh.GetPlaceByName("BombsiteB")
	//bCenter, _ := bombsiteB.GetEstimatedCenter()
	//bArea := mesh.GetNearestArea(bCenter, false)
	//fmt.Printf(bArea.Place.Name)

	p.RegisterEventHandler(func(e events.PlayerHurt) {
		/* Parse player damage events

		Player damage events are defined in the parser as a PlayerHurt event. These
		events occur when a player has been damaged, whether by another player or
		the world. We output the following line to the output when we parse a
		PlayerHurt event:

		[MAP_NAME, GAME_TICK] [VICTIM_X, VICTIM_Y, VICTIM_Z, VICTIM_VIEW_X, VICTIM_VIEW_Y, VICTIM_CLOSEST_AREA_ID,
		VICTIM_CLOSEST_AREA_NAME] [ATTACKER_X, ATTACKER_Y, ATTACKER_Z, ATTACKER_VIEW_X, ATTACKER_VIEW_Y,
		ATTACKER_CLOSEST_AREA_ID, ATTACKER_CLOSEST_AREA_NAME] [VICTIM_ID,
		VICTIM_NAME, VICTIM_TEAM, VICTIM_SIDE, VICTIM_TEAM_EQ_VAL] [ATTACKER_ID,
		ATTACKER_NAME, ATTACKER_TEAM, ATTACKER_SIDE, ATTACKER_TEAM_EQ_VAL] [HP_DMG,
		ARMOR_DMG, WEAPON, HIT_GROUP]
		*/
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup player hurt events
		if warmup == false {
			// First block (game state)
			game_tick := p.GameState().IngameTick()
			var map_name string = header.MapName

			// Second block (victim location)
			var victim_x float64 = 0.0
			var victim_y float64 = 0.0
			var victim_z float64 = 0.0
			var victim_x_viz float64 = 0.0
			var victim_y_viz float64 = 0.0
			var victim_closest_area_id uint32 = 0
			var victim_closest_area_name string = "NA"
			var victim_view_x float32 = 0.0
			var victim_view_y float32 = 0.0

			// Third block (attacker location)
			var attacker_x float64 = 0.0
			var attacker_y float64 = 0.0
			var attacker_z float64 = 0.0
			var attacker_x_viz float64 = 0.0
			var attacker_y_viz float64 = 0.0
			var attacker_closest_area_id uint32 = 0
			var attacker_closest_area_name string = "NA"
			var attacker_view_x float32 = 0.0
			var attacker_view_y float32 = 0.0

			// Fourth block (victim player/team)
			var victim_id int64 = 0
			var victim_name string = "NA"
			var victim_team string = "NA"
			var victim_side common.Team
			var victim_side_string string = "NA"
			var victim_team_eq_val int = 0

			// Fifth block (attacker player/team)
			var attacker_id int64 = 0
			var attacker_name string = "NA"
			var attacker_team string = "NA"
			var attacker_side common.Team
			var attacker_side_string string = "NA"
			var attacker_team_eq_val int = 0

			// Sixth block (Damage/Weapon)
			hp_damage := e.HealthDamage
			/* If a player has more than 100 damage taken, squash this value back
			down to 100. This may need to be changed in the future. [NOTE]
			*/
			if hp_damage > 100 {
				hp_damage = 100
			}
			armor_damage := e.ArmorDamage
			weapon_id := e.Weapon.Weapon
			hit_group := e.HitGroup

			// Find victim values
			if e.Player == nil {
				victim_id = 0
			} else {
				victim_id = e.Player.SteamID
				victim_x = e.Player.Position.X
				victim_y = e.Player.Position.Y
				victim_z = e.Player.Position.Z
				victim_x_viz, victim_y_viz = mapMetadata.TranslateScale(victim_x, victim_y)
				victim_view_x = e.Player.ViewDirectionX
				victim_view_y = e.Player.ViewDirectionY
				victim_location := gonav.Vector3{X: float32(victim_x), Y: float32(victim_y), Z: float32(victim_z)}
				victim_area := mesh.GetNearestArea(victim_location, true)
				if victim_area != nil {
					victim_closest_area_id = victim_area.ID
					if victim_area.Place != nil {
						victim_closest_area_name = victim_area.Place.Name
					}
				}
				victim_name = e.Player.Name
				victim_team = e.Player.TeamState.ClanName
				victim_side = e.Player.Team
				if victim_side == 2 {
					victim_side_string = "T"
				} else if victim_side == 3 {
					victim_side_string = "CT"
				}
				victim_team_eq_val = e.Player.TeamState.CurrentEquipmentValue()
			}

			// Find attacker values
			if e.Attacker == nil {
				attacker_id = 0
			} else {
				attacker_id = e.Attacker.SteamID
				attacker_x = e.Attacker.Position.X
				attacker_y = e.Attacker.Position.Y
				attacker_z = e.Attacker.Position.Z
				attacker_x_viz, attacker_y_viz = mapMetadata.TranslateScale(attacker_x, attacker_y)
				attacker_view_x = e.Attacker.ViewDirectionX
				attacker_view_y = e.Attacker.ViewDirectionY
				attacker_location := gonav.Vector3{X: float32(attacker_x), Y: float32(attacker_y), Z: float32(attacker_z)}
				attacker_area := mesh.GetNearestArea(attacker_location, true)
				if attacker_area != nil {
					attacker_closest_area_id = attacker_area.ID
					if attacker_area.Place != nil {
						attacker_closest_area_name = attacker_area.Place.Name
					}
				}
				attacker_name = e.Attacker.Name
				attacker_team = e.Attacker.TeamState.ClanName
				attacker_side = e.Attacker.Team
				if attacker_side == 2 {
					attacker_side_string = "T"
				} else if attacker_side == 3 {
					attacker_side_string = "CT"
				}
				attacker_team_eq_val = e.Attacker.TeamState.CurrentEquipmentValue()
			}

			// Print a line of the damage information
			fmt.Printf("[DAMAGE] [%s, %d] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%d, %s, %s, %s, %d] [%d, %s, %s, %s, %d] [%d, %d, %d, %d] \n",
			map_name, game_tick,
			victim_x, victim_y, victim_z, victim_x_viz, victim_y_viz, victim_view_x, victim_view_y, victim_closest_area_id, victim_closest_area_name,
			attacker_x, attacker_y, attacker_z, attacker_x_viz, attacker_y_viz, attacker_view_x, attacker_view_y, attacker_closest_area_id, attacker_closest_area_name,
			victim_id, victim_name, victim_team, victim_side_string, victim_team_eq_val,
			attacker_id, attacker_name, attacker_team, attacker_side_string, attacker_team_eq_val,
			hp_damage, armor_damage, weapon_id, hit_group)
		}
	})

	p.RegisterEventHandler(func(e events.Kill) {
		/* Parse player kill events

		Player kill events are defined in the parser as a Kill event. These
		events occur when a player has been reached 0 HP, through a damage event.
		We output the following line to the output when we parse a Kill event:

		[MAP_NAME, GAME_TICK] [VICTIM_X, VICTIM_Y, VICTIM_Z, VICTIM_VIEW_X, VICTIM_VIEW_Y, VICTIM_CLOSEST_AREA_ID,
		VICTIM_CLOSEST_AREA_NAME] [ATTACKER_X, ATTACKER_Y, ATTACKER_Z, ATTACKER_VIEW_X, ATTACKER_VIEW_Y,
		ATTACKER_CLOSEST_AREA_ID, ATTACKER_CLOSEST_AREA_NAME] [VICTIM_ID,
		VICTIM_NAME, VICTIM_TEAM, VICTIM_SIDE, VICTIM_TEAM_EQ_VAL] [ATTACKER_ID,
		ATTACKER_NAME, ATTACKER_TEAM, ATTACKER_SIDE, ATTACKER_TEAM_EQ_VAL] [
		WEAPON_ID, IS_WALLSHOT, IS_HEADSHOT]
		*/
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup kill events
		if warmup == false {
			// First block (game state)
			game_tick := p.GameState().IngameTick()
			var map_name string = header.MapName

			// Second block (victim location)
			var victim_x float64 = 0.0
			var victim_y float64 = 0.0
			var victim_z float64 = 0.0
			var victim_x_viz float64 = 0.0
			var victim_y_viz float64 = 0.0
			var victim_closest_area_id uint32 = 0
			var victim_closest_area_name string = "NA"
			var victim_view_x float32 = 0.0
			var victim_view_y float32 = 0.0

			// Third block (attacker location)
			var attacker_x float64 = 0.0
			var attacker_y float64 = 0.0
			var attacker_z float64 = 0.0
			var attacker_x_viz float64 = 0.0
			var attacker_y_viz float64 = 0.0
			var attacker_closest_area_id uint32 = 0
			var attacker_closest_area_name string = "NA"
			var attacker_view_x float32 = 0.0
			var attacker_view_y float32 = 0.0

			// Fourth block (victim player/team)
			var victim_id int64 = 0
			var victim_name string = "NA"
			var victim_team string = "NA"
			var victim_side common.Team
			var victim_side_string string = "NA"
			var victim_team_eq_val int = 0

			// Fifth block (attacker player/team)
			var attacker_id int64 = 0
			var attacker_name string = "NA"
			var attacker_team string = "NA"
			var attacker_side common.Team
			var attacker_side_string string = "NA"
			var attacker_team_eq_val int = 0

			// Sixth block (weapon/wallshot/headshot)
			weapon_id := e.Weapon.Weapon
			is_wallshot := e.PenetratedObjects
			is_headshot := e.IsHeadshot

			// Find victim values
			if e.Victim == nil {
				victim_id = 0
			} else {
				victim_id = e.Victim.SteamID
				victim_x = e.Victim.Position.X
				victim_y = e.Victim.Position.Y
				victim_z = e.Victim.Position.Z
				victim_x_viz, victim_y_viz = mapMetadata.TranslateScale(victim_x, victim_y)
				victim_view_x = e.Victim.ViewDirectionX
				victim_view_y = e.Victim.ViewDirectionY
				victim_location := gonav.Vector3{X: float32(victim_x), Y: float32(victim_y), Z: float32(victim_z)}
				victim_area := mesh.GetNearestArea(victim_location, true)
				if victim_area != nil {
					victim_closest_area_id = victim_area.ID
					if victim_area.Place != nil {
						victim_closest_area_name = victim_area.Place.Name
					}
				}
				victim_name = e.Victim.Name
				victim_team = e.Victim.TeamState.ClanName
				victim_side = e.Victim.Team
				if victim_side == 2 {
					victim_side_string = "T"
				} else if victim_side == 3 {
					victim_side_string = "CT"
				}
				victim_team_eq_val = e.Victim.TeamState.CurrentEquipmentValue()
			}

			// Find attacker values
			if e.Killer == nil {
				attacker_id = 0
			} else {
				attacker_id = e.Killer.SteamID
				attacker_x = e.Killer.Position.X
				attacker_y = e.Killer.Position.Y
				attacker_z = e.Killer.Position.Z
				attacker_x_viz, attacker_y_viz = mapMetadata.TranslateScale(attacker_x, attacker_y)
				attacker_view_x = e.Killer.ViewDirectionX
				attacker_view_y = e.Killer.ViewDirectionY
				attacker_location := gonav.Vector3{X: float32(attacker_x), Y: float32(attacker_y), Z: float32(attacker_z)}
				attacker_area := mesh.GetNearestArea(attacker_location, true)
				if attacker_area != nil {
					attacker_closest_area_id = attacker_area.ID
					if attacker_area.Place != nil {
						attacker_closest_area_name = attacker_area.Place.Name
					}
				}
				attacker_name = e.Killer.Name
				attacker_team = e.Killer.TeamState.ClanName
				attacker_side = e.Killer.Team
				if attacker_side == 2 {
					attacker_side_string = "T"
				} else if attacker_side == 3 {
					attacker_side_string = "CT"
				}
				attacker_team_eq_val = e.Killer.TeamState.CurrentEquipmentValue()
			}

			// Print a line of the kill information
			fmt.Printf("[KILL] [%s, %d] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s] [%d, %s, %s, %s, %d] [%d, %s, %s, %s, %d] [%d, %d, %t] \n",
			map_name, game_tick,
			victim_x, victim_y, victim_z, victim_x_viz, victim_y_viz, victim_view_x, victim_view_y, victim_closest_area_id, victim_closest_area_name,
			attacker_x, attacker_y, attacker_z, attacker_x_viz, attacker_y_viz, attacker_view_x, attacker_view_y, attacker_closest_area_id, attacker_closest_area_name,
			victim_id, victim_name, victim_team, victim_side_string, victim_team_eq_val,
			attacker_id, attacker_name, attacker_team, attacker_side_string, attacker_team_eq_val,
			weapon_id, is_wallshot, is_headshot)
		}
	})

	p.RegisterEventHandler(func(e events.RoundStart) {
		/* Parse round start events

		Round start events happen when a round starts. We output round end events
		as:

		[MAP_NAME, GAME_TICK] [T_SCORE, CT_SCORE]
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

		Round end events happen when a round is ended, such as through a successful
		bomb plant or through eliminating the other side. We output round end events
		as:

		[MAP_NAME, GAME_TICK] [T_SCORE, CT_SCORE] [WIN_SIDE, WIN_TEAM_NAME, REASON]
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

	p.RegisterEventHandler(func(e events.MatchStart) {
		/* Parse match start events

		Match start events happen when a match officially starts. We output match
		start events as:

		[MAP_NAME, GAME_TICK]
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

		Bomb plant events happen when a bomb is successfully planted. We output
		bomb plant events as:

		[MAP_NAME, GAME_TICK] [PLAYER_ID, PLAYER_NAME, PLAYER_TEAM] [PLAYER_X,
		PLAYER_Y, PLAYER_Z, AREA_ID, BOMB_SITE]
		*/
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bomb_site = "None"
			var player_id int64 = 0
			var player_name string = "NA"
			var player_team string = "NA"
			var player_x float64 = 0
			var player_y float64 = 0
			var player_z float64 = 0
			var area_id uint32 = 0

			player_id = e.BombEvent.Player.SteamID
			player_name = e.BombEvent.Player.Name
			player_team = e.BombEvent.Player.TeamState.ClanName
			player_x = e.BombEvent.Player.Position.X
			player_y = e.BombEvent.Player.Position.Y
			player_z = e.BombEvent.Player.Position.Z

			player_point := gonav.Vector3{X: float32(player_x), Y: float32(player_y), Z: float32(player_z)}
			area := mesh.GetNearestArea(player_point, true)
			if area != nil {
				area_id = area.ID
			}

			if e.Site == 65 {
				bomb_site = "A"
			} else if e.Site == 66 {
				bomb_site = "B"
			}
			fmt.Printf("[BOMB PLANT] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
			header.MapName, gs.IngameTick(),
			player_id, player_name, player_team,
			player_x, player_y, player_z, area_id, bomb_site)
		}
	})

	p.RegisterEventHandler(func(e events.BombDefused) {
		/* Parse bomb defuse events

		Bomb defuse events happen when a bomb is successfully defused. We output
		bomb defuse events as:

		[MAP_NAME, GAME_TICK] [PLAYER_ID, PLAYER_NAME, PLAYER_TEAM] [PLAYER_X,
		PLAYER_Y, PLAYER_Z, AREA_ID, BOMB_SITE]
		*/
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bomb_site = "None"
			var player_id int64 = 0
			var player_name string = "NA"
			var player_team string = "NA"
			var player_x float64 = 0
			var player_y float64 = 0
			var player_z float64 = 0
			var area_id uint32 = 0

			player_id = e.BombEvent.Player.SteamID
			player_name = e.BombEvent.Player.Name
			player_team = e.BombEvent.Player.TeamState.ClanName
			player_x = e.BombEvent.Player.Position.X
			player_y = e.BombEvent.Player.Position.Y
			player_z = e.BombEvent.Player.Position.Z

			player_point := gonav.Vector3{X: float32(player_x), Y: float32(player_y), Z: float32(player_z)}
			area := mesh.GetNearestArea(player_point, true)
			if area != nil {
				area_id = area.ID
			}

			if e.Site == 65 {
				bomb_site = "A"
			} else if e.Site == 66 {
				bomb_site = "B"
			}
			fmt.Printf("[BOMB DEFUSE] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
			header.MapName, gs.IngameTick(),
			player_id, player_name, player_team,
			player_x, player_y, player_z, area_id, bomb_site)
		}
	})

	p.RegisterEventHandler(func(e events.BombDefused) {
		/* Parse bomb explode events

		Bomb explode events happen when a bomb explodes. We output
		bomb explode events as:

		[MAP_NAME, GAME_TICK] [PLAYER_ID, PLAYER_NAME, PLAYER_TEAM] [PLAYER_X,
		PLAYER_Y, PLAYER_Z, AREA_ID, BOMB_SITE]
		*/
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup events
		if warmup == false {
			var bomb_site = "None"
			var player_id int64 = 0
			var player_name string = "NA"
			var player_team string = "NA"
			var player_x float64 = 0
			var player_y float64 = 0
			var player_z float64 = 0
			var area_id uint32 = 0

			player_id = e.BombEvent.Player.SteamID
			player_name = e.BombEvent.Player.Name
			player_team = e.BombEvent.Player.TeamState.ClanName
			player_x = e.BombEvent.Player.Position.X
			player_y = e.BombEvent.Player.Position.Y
			player_z = e.BombEvent.Player.Position.Z

			player_point := gonav.Vector3{X: float32(player_x), Y: float32(player_y), Z: float32(player_z)}
			area := mesh.GetNearestArea(player_point, true)
			if area != nil {
				area_id = area.ID
			}

			if e.Site == 65 {
				bomb_site = "A"
			} else if e.Site == 66 {
				bomb_site = "B"
			}
			fmt.Printf("[BOMB EXPLODE] [%s, %d] [%d, %s, %s] [%f, %f, %f, %d, %s] \n",
			header.MapName, gs.IngameTick(),
			player_id, player_name, player_team,
			player_x, player_y, player_z, area_id, bomb_site)
		}
	})

	p.RegisterEventHandler(func(e events.Footstep) {
		/* Parse player footstep events

		Player footstep events are defined in the parser as a Footstep event. These
		events occur when a player moves in game.
		We output the following line to the output when we parse a Footstep event:

		[MAP_NAME, GAME_TICK] [PLAYER_ID, PLAYER_NAME, PLAYER_TEAM, PLAYER_SIDE] [
		PLAYER_X, PLAYER_Y, PLAYER_Z, PLAYER_VIEW_X, PLAYER_VIEW_Y, CLOSEST_AREA_ID, CLOSEST_AREA_NAME]
		*/
		gs := p.GameState()
		warmup := p.GameState().IsWarmupPeriod()

		// Only parse non-warmup footsteps
		if warmup == false {
			var player_id int64 = 0
			var player_name string = "NA"
			var player_x float64 = 0.0
			var player_y float64 = 0.0
			var player_z float64 = 0.0
			var player_x_viz float64 = 0.0
			var player_y_viz float64 = 0.0
			var player_view_x float32 = 0.0
			var player_view_y float32 = 0.0
			var player_side common.Team
			var player_side_string string = "NA"
			var player_team string = "NA"
			var area_id uint32 = 0
			var area_place string = "NA"

			if e.Player == nil {
				player_id = 0
			} else {
				player_id = e.Player.SteamID
				//player_name = e.Player.Name
				player_x = e.Player.Position.X
				player_y = e.Player.Position.Y
				player_z = e.Player.Position.Z
				player_view_x = e.Player.ViewDirectionX
				player_view_y = e.Player.ViewDirectionY
				player_x_viz, player_y_viz = mapMetadata.TranslateScale(player_x, player_y)
				player_side = e.Player.Team
				player_team = e.Player.TeamState.ClanName
				player_name = e.Player.Name
				player_point := gonav.Vector3{X: float32(player_x), Y: float32(player_y), Z: float32(player_z)}
				//area := mesh.GetNearestArea(player_point, false)
				//player_point := gonav.Vector3{X: float32(1293.267944), Y: float32(1532.817139), Z: float32(1.031250)}
				area := mesh.GetNearestArea(player_point, true)
				if area != nil {
					area_id = area.ID
					if area.Place != nil {
						area_place = area.Place.Name
					}
				}
			}

			if player_side == 2 {
				player_side_string = "T"
			} else if player_side == 3 {
				player_side_string = "CT"
			}

			fmt.Printf("[FOOTSTEP] [%s, %d] [%d, %s, %s, %s] [%f, %f, %f, %f, %f, %f, %f, %d, %s] \n",
			header.MapName, gs.IngameTick(),
			player_id, player_name, player_team, player_side_string,
			player_x, player_y, player_z, player_x_viz, player_y_viz, player_view_x, player_view_y,
			area_id, area_place)
		}
	})

	// Parse demofile to end
	err = p.ParseToEnd()
	checkError(err)
}

// Function to handle errors
func checkError(err error) {
	if err != nil {
		panic(err)
	}
}
