package main

import (
	"testing"

	common "github.com/markus-wa/demoinfocs-golang/v3/pkg/demoinfocs/common"
)

func TestConvertRank(t *testing.T) {
	t.Parallel()
	var rankInt int
	ranks := []string{"Expired", "Unranked", "Silver 1", "Silver 2", "Silver 3", "Silver 4", "Silver Elite",
		"Silver Elite Master", "Gold Nova 1", "Gold Nova 2", "Gold Nova 3", "Gold Nova Master",
		"Master Guardian 1", "Master Guardian 2", "Master Guardian Elite", "Distinguished Master Guardian",
		"Legendary Eagle", "Legendary Eagle Master", "Supreme Master First Class", "The Global Elite", "Unranked"}
	for index, want := range ranks {
		rankInt = index - 1
		is := convertRank(rankInt)
		if is != want {
			t.Errorf("Rank value of %v should convert to %v, but was %v", rankInt, want, is)
		}
	}
}

func FuzzConvertRank(f *testing.F) {
	f.Fuzz(func(t *testing.T, rankInt int) {
		is := convertRank(rankInt)
		if (rankInt < -1 || rankInt > 18) && is != unranked {
			t.Errorf("Rank value of %v should convert to %v, but was %v", rankInt, unranked, is)
		}
	})
}

func TestDetermineSecond(t *testing.T) {
	t.Parallel()
	var value int64 = -2
	var want float64
	var bombPlantTick int64 = 256
	currentRound := GameRound{FreezeTimeEndTick: 128, BombPlantTick: &bombPlantTick}
	var tickRate int64 = 128
	is := determineSecond(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a second value of %v but got %v.", value, want, is)
	}

	value = 128 * 5
	want = 3.0
	bombPlantTick = 256
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: &bombPlantTick}
	tickRate = 128
	is = determineSecond(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a second value of %v but got %v.", value, want, is)
	}

	value = 128 * 5
	want = 4.0
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: nil}
	tickRate = 128
	is = determineSecond(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a second value of %v but got %v.", value, want, is)
	}

	value = 128 * 5
	want = 8.0
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: nil}
	tickRate = 64
	is = determineSecond(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a second value of %v but got %v.", value, want, is)
	}
}

func FuzzDetermineSecond(f *testing.F) {
	f.Fuzz(func(t *testing.T, tick int64) {
		is := determineSecond(tick, GameRound{FreezeTimeEndTick: 0, BombPlantTick: nil}, 1)
		var want float64
		if tick > 0 {
			want = float64(tick)
		}
		if is != want {
			t.Errorf("Expected a tick of %v to produce a second value of %v but got %v.", tick, want, is)
		}
	})
}

func TestCalculateClockTime(t *testing.T) {
	t.Parallel()
	zeroTime := "00:00"
	var value int64 = -2
	var want = zeroTime
	var bombPlantTick int64 = 256
	currentRound := GameRound{FreezeTimeEndTick: 128, BombPlantTick: &bombPlantTick}
	var tickRate int64 = 128
	is := calculateClocktime(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a clockTime of %v but got %v.", value, want, is)
	}

	value = 128 * 5
	want = "00:37"
	bombPlantTick = 256
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: &bombPlantTick}
	tickRate = 128
	is = calculateClocktime(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a clockTime of %v but got %v.", value, want, is)
	}

	value = 128 * 15
	want = "01:41"
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: nil}
	tickRate = 128
	is = calculateClocktime(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a clockTime of %v but got %v.", value, want, is)
	}

	value = 128 * 51
	want = "00:15"
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: nil}
	tickRate = 64
	is = calculateClocktime(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a clockTime of %v but got %v.", value, want, is)
	}

	value = 128 * 500
	want = zeroTime
	currentRound = GameRound{FreezeTimeEndTick: 128, BombPlantTick: nil}
	tickRate = 64
	is = calculateClocktime(value, currentRound, tickRate)
	if is != want {
		t.Errorf("Expected a tick of %v to produce a clockTime of %v but got %v.", value, want, is)
	}
}

func TestPlayerInList(t *testing.T) {
	t.Parallel()
	player := common.Player{SteamID64: 1}
	playersList := []PlayerInfo{{PlayerSteamID: 1}, {PlayerSteamID: 2}, {PlayerSteamID: 3}, {PlayerSteamID: 4}}
	want := true
	is := playerInList(&player, playersList)
	if is != want {
		t.Errorf("Player %v was in slice %v but not found.", player, playersList)
	}

	player = common.Player{SteamID64: 1}
	playersList = []PlayerInfo{{PlayerSteamID: 5}, {PlayerSteamID: 2}, {PlayerSteamID: 3}, {PlayerSteamID: 4}}
	want = false
	is = playerInList(&player, playersList)
	if is != want {
		t.Errorf("Player %v was not in slice %v but found.", player, playersList)
	}

	player = common.Player{SteamID64: 1}
	playersList = []PlayerInfo{}
	want = false
	is = playerInList(&player, playersList)
	if is != want {
		t.Errorf("Empty lists should return false.")
	}

	playersList = []PlayerInfo{}
	want = false
	is = playerInList(nil, playersList)
	if is != want {
		t.Errorf("Empty lists should return false even for nil players.")
	}
}

func TestParseTeamBuy(t *testing.T) {
	t.Parallel()
	fullEco := "Full Eco"
	semiEco := "Semi Eco"
	semiBuy := "Semi Buy"
	fullBuy := "Full Buy"
	values := []int64{-1000, 0, 1000, 5500, 15000, 19000, 26000, 1000, 5500, 15000,
		19000, 26000, 1000, 5500, 15000, 26000}
	sides := []string{"CT", "CT", "CT", "CT", "CT", "CT", "CT",
		"T", "T", "T", "T", "T", "T", "T", "T", "T"}
	style := []string{"csgo", "csgo", "csgo", "csgo", "csgo", "csgo", "csgo",
		"csgo", "csgo", "csgo", "csgo", "csgo", "hltv", "hltv", "hltv", "hltv"}
	wants := []string{fullEco, fullEco, fullEco, "Eco", "Half Buy", "Half Buy", fullBuy,
		fullEco, "Eco", "Half Buy", fullBuy, fullBuy, fullEco, semiEco, semiBuy, fullBuy}
	for index := range values {
		is := parseTeamBuy(values[index], sides[index], style[index])
		want := wants[index]
		if is != want {
			t.Errorf("Expected a buy style of %v for eqVal %v; side %v; style %v but got %v instead.",
				want, values[index], sides[index], style[index], is)
		}
	}
}

func FuzzParseTeamBuy(f *testing.F) {
	f.Fuzz(func(t *testing.T, eqVal int64, side string, style string) {
		is := parseTeamBuy(eqVal, side, style)
		if is == "Unknown" {
			t.Errorf("Should never reach unknown!")
		}
	})
}

func TestIsTrade(t *testing.T) {
	t.Parallel()
	tradeTime := 5
	tickRate := 1
	aaSteamID := int64(1)
	bvSteamID := int64(1)
	killA := KillAction{AttackerSteamID: &aaSteamID, Tick: 1}
	killB := KillAction{VictimSteamID: &bvSteamID, Tick: 2}
	want := true
	is := isTrade(killA, killB, int64(tickRate), int64(tradeTime))
	if is != want {
		t.Errorf("Expected %v to trade the kill of %v.",
			killB, killA)
	}

	aaSteamID = int64(1)
	bvSteamID = int64(1)
	killA = KillAction{AttackerSteamID: &aaSteamID, Tick: 1}
	killB = KillAction{VictimSteamID: &bvSteamID, Tick: 10}
	want = false
	is = isTrade(killA, killB, int64(tickRate), int64(tradeTime))
	if is != want {
		t.Errorf("Expected %v not to trade the kill of %v because it was outside the tradeTime of %v.",
			killB, killA, tradeTime)
	}

	aaSteamID = int64(1)
	bvSteamID = int64(2)
	killA = KillAction{AttackerSteamID: &aaSteamID, Tick: 1}
	killB = KillAction{VictimSteamID: &bvSteamID, Tick: 2}
	want = false
	is = isTrade(killA, killB, int64(tickRate), int64(tradeTime))
	if is != want {
		t.Errorf("Expected %v not to trade the kill of %v because the killer did not die.",
			killB, killA)
	}

	bvSteamID = int64(2)
	killA = KillAction{AttackerSteamID: nil, Tick: 1}
	killB = KillAction{VictimSteamID: &bvSteamID, Tick: 2}
	want = false
	is = isTrade(killA, killB, int64(tickRate), int64(tradeTime))
	if is != want {
		t.Errorf("Expected %v not to trade the kill of %v because there was no original killer.",
			killB, killA)
	}

	aaSteamID = int64(1)
	killA = KillAction{AttackerSteamID: &aaSteamID, Tick: 1}
	killB = KillAction{VictimSteamID: nil, Tick: 2}
	want = false
	is = isTrade(killA, killB, int64(tickRate), int64(tradeTime))
	if is != want {
		t.Errorf("Expected %v not to trade the kill of %v because there was no second victim.",
			killB, killA)
	}
}

func TestCountAlivePlayers(t *testing.T) {
	t.Parallel()
	players := []PlayerInfo{{IsAlive: true}, {IsAlive: false}, {IsAlive: true}}
	want := int64(2)
	is := countAlivePlayers(players)
	if is != want {
		t.Errorf("Expected %v players to be alive in %v but got %v instead.",
			want, players, is)
	}
	players = []PlayerInfo{}
	want = int64(0)
	is = countAlivePlayers(players)
	if is != want {
		t.Errorf("Empty slice should have 0 alive players.")
	}
}

func TestCountUtility(t *testing.T) {
	t.Parallel()
	players := []PlayerInfo{{IsAlive: true, TotalUtility: 6},
		{IsAlive: false, TotalUtility: 5}, {IsAlive: true, TotalUtility: 3}}
	want := int64(9)
	is := countUtility(players)
	if is != want {
		t.Errorf("Expected total utility of %v in %v but got %v instead.",
			want, players, is)
	}
	players = []PlayerInfo{}
	want = int64(0)
	is = countUtility(players)
	if is != want {
		t.Errorf("Empty slice should have 0 utility players.")
	}
}

func TestCleanMapName(t *testing.T) {
	t.Parallel()
	deCache := "de_cache"
	mapName := deCache
	want := deCache
	is := cleanMapName(mapName)
	if is != want {
		t.Errorf("Expected cleaned name of %v for %v but got %v instead.", want, mapName, is)
	}

	mapName = ""
	want = ""
	is = cleanMapName(mapName)
	if is != want {
		t.Errorf("Expected cleaned name of %v for %v but got %v instead.", want, mapName, is)
	}

	mapName = "test/de_cache"
	want = deCache
	is = cleanMapName(mapName)
	if is != want {
		t.Errorf("Expected cleaned name of %v for %v but got %v instead.", want, mapName, is)
	}

	mapName = "test/test/de_cache"
	want = deCache
	is = cleanMapName(mapName)
	if is != want {
		t.Errorf("Expected cleaned name of %v for %v but got %v instead.", want, mapName, is)
	}
}
