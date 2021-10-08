# CSGO Python Library Parser
[Index](README.md) | [Data](data.md) | [Demofiles](demofiles.md) | [Parser](parser.md) | [Demo Cleaning](demo_cleaning.md) | [Analytics](analytics.md) | [Visualization](visualization.md)

###### Table of Contents
[Parser Parameters](#parser-parameters)

[Server Variables](#server-variables)

[Match Phases](#match-phases)

[Game Rounds](#game-rounds) ([Kills](#kills) - [Damages](#damages) - [Grenades](#grenades) - [Bomb Events](#bomb-events) - [Flashes](#flashes) - [Frames](#frames))

In this document, we describe the parser and its associated output. The main feature of our library is the CSGO demo parsing functionality. Essentially, our library is a Python wrapper to [markus-wa's parser written in Go](https://github.com/markus-wa/demoinfocs-golang). As Markus' parser parses the raw events, we order them into a sensible hierarchy, and parse useful metadata for events and the demo itself. Although the library allows us to parse into JSON or Pandas DataFrames, the data itself is the same. For the purposes of this documentation, we will focus on the JSON output.

This documentation is quite important, because our parser parses demofiles as they are (and CSGO demos are _very_ imperfect). Although we provide some functions to clean demofiles, it is still useful to know what the parser is parsing.

To parse the data, we simply run:

```
from csgo.parser import DemoParser

demo_parser = DemoParser(demofile="my-demo.dem", parse_rate=128)

data = demo_parser.parse()
```

What do we do next? Our data is written to `data`, which is a dictionary. The top level keys are as follows:

- `matchID` (demo id, inferred from file name if not passed to parser via `demo_id` argument)
- `clientName` (usually GOTV demo)
- `mapName` (Even for workshop maps of old official maps, the name is parsed to be the map name, i.e. `de_nuke_12345` becomes `de_nuke`)
- `tickRate` (The tickrate that the demo was recorded, or -1 if the demo header isn't available)
- `playbackTicks` (Total number of ticks in the demo)
- `parserParameters` (Parsing parameters passed via `DemoParser` class)
- `serverVars` (Parsed server variables)
- `matchPhases` (Dictionary of the ticks when phase changes happened, such as match starts, round starts/ends, team side switches, etc.)
- `parsedPlaces` (If the parser finds an associated `.nav` file based on the parsed map name, then the parsed places names from that file)
- `matchmakingRanks` (If the demo is from MM, then the ranks)
- `gameRounds` (A list of game rounds, with the associated actions in each)

##### Parser Parameters
This dictionary contains the parsing parameters sent via the `DemoParser` class. It looks like:

```
{
    'parseRate': 128, 
    'parseFrames': False, 
    'tradeTime': 5, 
    'roundBuyStyle': 'hltv', 
    'damagesRolledUp': False
}
```

##### Server Variables
These are the parsed server variables, which corresponds to the rules of the game. The round time is either in `roundTime` or `roundTimeDefuse`. Sometimes, these may parse improperly.

```
{
    'cashBombDefused': 0, 
    'cashBombPlanted': 0, 
    'cashTeamTWinBomb': 0, 
    'cashWinDefuse': 3500, 
    'cashWinTimeRunOut': 0, 
    'cashWinElimination': 0, 
    'cashPlayerKilledDefault': 0, 
    'cashTeamLoserBonus': 0, 
    'cashTeamLoserBonusConsecutive': 0, 
    'roundTime': 0, // Either use this or roundTimeDefuse
    'roundTimeDefuse': 2, 
    'roundRestartDelay': 5, // This is the time between round end (when the round winner has been decided) and round end official (when the game proceeds to the next round)
    'freezeTime': 20, 
    'buyTime': 20, 
    'bombTimer': 0, 
    'maxRounds': 30, 
    'timeoutsAllowed': 4, 
    'coachingAllowed': 0
}
```

##### Match Phases
We include the ticks of each important match phase, as to help users clean the demofiles. Sometimes, you'll see multiple match starts, or missing roundEnds and so on. Using this information can help in the parsed demo cleaning process.

```
{
    'announcementLastRoundHalf': [232247], 
    'announcementFinalRound': None, 
    'announcementMatchStarted': None, 
    'roundStarted': [889, 6259, 6765, 6982, 33439, 42952, 64823, 86002, 94352, 115848, 128292, 151302, 162103, 181224, 198030, 208898, 221375, 232247, 248146, 284658, 299667, 305570, 311121, 330375, 340967, 352281, 358577, 378166, 396418, 423229, 445714], 
    'roundEnded': [32798, 42312, 64183, 85363, 93711, 115208, 127651, 150662, 161464, 180582, 197389, 208257, 220736, 231606, 246226, 284018, 299025, 304929, 310480, 329735, 340327, 351639, 357936, 377526, 395779, 422589, 445074, 460082], 
    'roundFreezetimeEnded': [3448, 6514, 29610, 35999, 45512, 67383, 88562, 96912, 118408, 135942, 153862, 170397, 183784, 200590, 211458, 228816, 234807, 272952, 287218, 302227, 308130, 313681, 332935, 343527, 354841, 365365, 380726, 410017, 430493, 448274, 460082], 'roundEndedOfficial': [33439, 42952, 64823, 86002, 94352, 115848, 128292, 151302, 162103, 181224, 198030, 208898, 221375, 232247, 248146, 284658, 299667, 305570, 311121, 330375, 340967, 352281, 358577, 378166, 396418, 423229, 445714], 
    'gameHalfEnded': [246226], 
    'matchStart': [889, 6988], 
    'matchStartedChanged': [0, 889, 6854, 6988, 460082],
    'warmupChanged': [0, 889, 6259, 6765], 
    'teamSwitch': [248146]
}
```

## Game Rounds
The `gameRounds` top-level key is the meat of the parser. This is where all player position and event data gets parsed. This section will describe each section in-depth. The value of this field is a list, where each element is a round. Each round has the following keys:

```
{
    'roundNum': 8, // Parsed round number, but NOT the round number in game
    'isWarmup': False, // determined at the freezeTimeEndTick
    'startTick': 86002, 
    'freezeTimeEndTick': 88562, 
    'endTick': 93712, 
    'endOfficialTick': 94352, 
    'bombPlantTick': 91529, // null if there is no bomb plant
    'tScore': 2, 
    'ctScore': 2, 
    'endTScore': 3, 
    'endCTScore': 2, 
    'ctTeam': 'Team Liquid', 
    'tTeam': 'Astralis', 
    'winningSide': 'T', 
    'winningTeam': 'Astralis', 
    'losingTeam': 'Team Liquid', 
    'roundEndReason': 'TerroristsWin', // Usually empty for rounds that are not part of the real match.
    // The only possible outcomes for a real match are: 
    //    TargetBombed (T win), TerroristsWin (T win), BombDefused (CT win), CTWin (CT win) or TargetSaved (CT win)
    'ctStartEqVal': 1700, 
    'ctRoundStartEqVal': 1000, // RoundStartEqVal parsed slightly after freezeTimeEndTick
    'ctRoundStartMoney': 10850, 
    'ctBuyType': 'Full Eco', 
    'ctSpend': 700, 
    'tStartEqVal': 21250, 
    'tRoundStartEqVal': 8650, 
    'tRoundStartMoney': 20050, 
    'tBuyType': 'Full Buy', 
    'tSpend': 12600, 
    'kills': [...], // This field, and below, are all events that happened in the round
    'damages': [...],
    'grenades': [...],
    'bombEvents': [...],
    'weaponFires': [...],
    'flashes': [...],
    'frames': [...]
}
```

##### Kills
```
{
    'tick': 74156, 
    'seconds': 52.9140625, 
    'attackerSteamID': 76561197999004010, 
    'attackerName': 'Stewie2K', 
    'attackerTeam': 'Team Liquid', 
    'attackerSide': 'CT', 
    'attackerX': 467.9614562988281, 
    'attackerY': -188.7003173828125, 
    'attackerZ': -287.96875, 
    'attackerAreaID': 3598, 
    'attackerAreaName': 'BombsiteB', 
    'attackerViewX': 96.2237548828125, 
    'attackerViewY': 16.798095703125, 
    'victimSteamID': 76561198004854956, 
    'victimName': 'dupreeh', 
    'victimTeam': 'Astralis', 
    'victimSide': 'T', 
    'victimX': 409.064697265625, 
    'victimY': 184.4791259765625, 
    'victimZ': -415.96875, 
    'victimAreaID': 3515, 
    'victimAreaName': 'Ramp', 
    'victimViewX': 293.9337158203125, 
    'victimViewY': 358.055419921875, 
    'assisterSteamID': None, 
    'assisterName': None, 
    'assisterTeam': None, 
    'assisterSide': None, 
    'isSuicide': False, 
    'isTeamkill': False, 
    'isWallbang': False, // Should be true if penetratedObjects > 0
    'penetratedObjects': 0, 
    'isFirstKill': True, 
    'isHeadshot': True, 
    'victimBlinded': False, 
    'attackerBlinded': False, 
    'flashThrowerSteamID': None, 
    'flashThrowerName': None, 
    'flashThrowerTeam': None, 
    'flashThrowerSide': None, 
    'noScope': False, 
    'thruSmoke': False, 
    'distance': 398.8931249979475, // Uses in game units
    'isTrade': False, 
    'playerTradedName': None, 
    'playerTradedTeam': None, 
    'playerTradedSteamID': None, 
    'weapon': 'Desert Eagle'
}
```

##### Damages
```
{
    'tick': 72762, 
    'seconds': 42.0234375, 
    'attackerSteamID': 76561198010511021, 
    'attackerName': 'gla1ve', 
    'attackerTeam': 'Astralis', 
    'attackerSide': 'T', 
    'attackerX': 1071.789794921875, 
    'attackerY': -1843.035888671875, 
    'attackerZ': -416.50506591796875, 
    'attackerAreaID': 3558, 
    'attackerAreaName': 'Outside', 
    'attackerViewX': 90.8514404296875, 
    'attackerViewY': 352.8863525390625, 
    'attackerStrafe': False, // Was the attacker moving when he damaged?
    'victimSteamID': 76561198001151695, 
    'victimName': 'NAF', 
    'victimTeam': 'Team Liquid', 
    'victimSide': 'CT', 
    'victimX': 1045.416259765625, 
    'victimY': -541.6353149414062, 
    'victimZ': -239.96875, 
    'victimAreaID': 3459, 
    'victimAreaName': 'Hell', 
    'victimViewX': 273.1585693359375, 
    'victimViewY': 10.9039306640625, 
    'weapon': 'AK-47', 
    'hpDamage': 26, // Damage can be greater than 100, like an AWP to the head
    'hpDamageTaken': 26, // This value is capped to 100
    'armorDamage': 3, 
    'armorDamageTaken': 3, 
    'hitGroup': 'Chest'
}
```

##### Grenades
```
{
    'throwTick': 68455, 
    'destroyTick': 71116, // This is when the grenade is destroyed
    'throwSeconds': 8.375, 
    'destroySeconds': 29.1640625, 
    'throwerSteamID': 76561197999004010, 
    'throwerName': 'Stewie2K', 
    'throwerTeam': 'Team Liquid', 
    'throwerSide': 'CT', 
    'throwerX': 981.75, 
    'throwerY': 35.65625, 
    'throwerZ': -348.15625, 
    'throwerAreaID': 2915, 
    'throwerAreaName': 'Admin', 
    'grenadeType': 'Smoke Grenade', 
    'grenadeX': 93.75, 
    'grenadeY': -227.96875, 
    'grenadeZ': -414, 
    'grenadeAreaID': 4009, 
    'grenadeAreaName': 'Control', 
    'UniqueID': 6643715706064775031
}
```

##### Bomb Events
```
{
    'tick': 81550, 
    'seconds': 110.6796875, 
    'playerSteamID': 76561197990682262, 
    'playerName': 'Xyp9x', 
    'playerTeam': 'Astralis', 
    'playerX': 340.03125, 
    'playerY': -823.4887084960938, 
    'playerZ': -771.96875, 
    'bombAction': 'plant_begin', // Can either be plant_begin/abort, or defused or planted
    'bombSite': 'B'
}
```

##### Flashes
```
{
    'tick': 73475, 
    'seconds': 47.59375, 
    'attackerSteamID': 76561197983956651, 
    'attackerName': 'Magisk', 
    'attackerTeam': 'Astralis', 
    'attackerSide': 'T', 
    'attackerX': 144.73223876953125, 
    'attackerY': -264.7706298828125, 
    'attackerZ': -415.96875, 
    'attackerAreaID': 491, 
    'attackerAreaName': 'Trophy', 
    'attackerViewX': 329.4195556640625, 
    'attackerViewY': 10.008544921875, 
    'playerSteamID': 76561197999004010, 
    'playerName': 'Stewie2K', 
    'playerTeam': 'Team Liquid', 
    'playerSide': 'CT', 
    'playerX': 447.8232421875, 
    'playerY': -218.9803009033203, 
    'playerZ': -287.96875, 
    'playerAreaID': 3598, 
    'playerAreaName': 'BombsiteB', 
    'playerViewX': 242.90771484375, 
    'playerViewY': 25.4937744140625, 
    'flashDuration': 0.278546976
}
```

##### Frames
```
{
    'tick': 67465, 
    'seconds': 0.640625, 
    // Token is a unique identifier for the number of each side's players in a specific place.
    // Described in "ggViz: Accelerating Large-Scale Esports Game Analysis" (https://arxiv.org/pdf/2107.06495.pdf)
    'positionToken': '0000000000000000000000005000000000000000000000000000000000', 
    'tToken': '00000000000000000000000050000', 
    'ctToken': '00000000000000000000000000000', 
    't': {
        'side': 'T', 
        'teamName': 'Astralis', 
        'teamEqVal': 21600, 
        'positionToken': '00000000000000000000000050000', 
        'alivePlayers': 5, 
        'totalUtility': 12, 
        'players': [
            {
                'steamID': 76561197990682262, 
                'name': 'Xyp9x', 
                'team': 'Astralis', 
                'side': 'T', 
                'x': -1755.138427734375, 
                'y': -1086.612548828125, 
                'z': -415.0366516113281, 
                'viewX': 354.90234375, 
                'viewY': 7.7838134765625, 
                'areaID': 3018, 
                'areaName': 'TSpawn', 
                'hp': 100, 
                'armor': 87, 
                'activeWeapon': 'Knife', 
                'totalUtility': 4, 
                'isAlive': True, 
                'isBlinded': False, 
                'isAirborne': False, 
                'isDucking': False, 
                'isDuckingInProgress': False, 
                'isUnDuckingInProgress': False, 
                'isDefusing': False, 
                'isPlanting': False, 
                'isReloading': False, 
                'isInBombZone': False, 
                'isInBuyZone': True, 
                'isStanding': True, 
                'isScoped': False, 
                'isWalking': False, 
                'isUnknown': False, 
                'inventory': [
                    {
                        'weaponName': 'Molotov', 
                        'weaponClass': 'Grenade', 
                        'ammoInMagazine': 1, 
                        'ammoInReserve': 0
                    }, ...
                ], 
                'equipmentValue': 5050, 
                'cash': 0, 
                'hasHelmet': False, 
                'hasDefuse': False, 
                'ping': 5`
            },  ...
        ],
    },
    "ct": {...},
    'world': [
        {
            'objectType': 'bomb', 
            'x': -1694.0751953125, 
            'y': -1096.5224609375, 
            'z': -414.490478515625, 
            'areaID': 138, 
            'areaName': 'TSpawn'
        }
    ], 
    'bombPlanted': False, 
    'bombsite': ''
}
```

