# CSGO Python Library Parser

###### Table of Contents
[Parser Parameters](#parser-parameters)

[Server Variables](#server-variables)

[Match Phases](#match-phases)

[Game Rounds](#game-rounds)

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

