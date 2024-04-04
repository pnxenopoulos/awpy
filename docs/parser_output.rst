Example Parser JSON
===================

When using `awpy.DemoParser`, you create a `JSON` output file. This is generally a large file, and is described by the JSON structure contained in this documentation.

**Contents**

- :ref:`Top level keys`
- :ref:`Rounds`
- :ref:`Kills`
- :ref:`Damages`
- :ref:`Grenades`
- :ref:`Bomb Events`
- :ref:`Weapon Fires`
- :ref:`Flashes`
- :ref:`Frames`



Top level keys
--------------

.. code-block:: json

    {
        "matchID": "003486831536689381471_0732641554",  # Set to be the name of the demo file
        "clientName": "GOTV Demo",                      # Client which recorded the demo
        "mapName": "de_inferno",
        "tickRate": 64,                                 # Server tick rate
        "playbackTicks": 161695,                        # Total ticks in the demo
        "playbackFramesCount": 80775,                   # Total number of frames
        "parsedToFrameIdx": 80790,                      # Parsed until X frame
        "parserParameters": {                           # All the below parameters are set in DemoParser
            "parseRate": 256,                           # Parse rate set in DemoParser. Represents spacing between recorded frames.
            "parseFrames": false,     
            "parseKillFrames": true,                    # If set to true, a frame is recorded every kill. Doesn"t require parseFrames == true                   
            "tradeTime": 5,                             
            "roundBuyStyle": "hltv",                    # HLTV represents round buys (e.g., full eco, full buy, etc.) as they do in HLTV.
            "damagesRolledUp": false                    # Sometimes damages can happen in the same tick. This option means they are combined.
        },
        "serverVars": {                                 # Server cvars
            "cashBombDefused": 0,
            "cashBombPlanted": 0,
            "cashTeamTWinBomb": 0,
            "cashWinDefuse": 3500,
            "cashWinTimeRunOut": 0,
            "cashWinElimination": 0,
            "cashPlayerKilledDefault": 0,
            "cashTeamLoserBonus": 0,
            "cashTeamLoserBonusConsecutive": 0,
            "roundTime": 0,
            "roundTimeDefuse": 0,
            "roundRestartDelay": 0,
            "freezeTime": 15,
            "buyTime": 20,
            "bombTimer": 0,
            "maxRounds": 30,
            "timeoutsAllowed": 0,
            "coachingAllowed": 0
        },
        "matchPhases": {                                # Contains lists with the ticks on which certain round/phase events happened
            "announcementLastRoundHalf": [...],
            "announcementFinalRound": [...],
            "announcementMatchStarted": [...],
            "roundStarted": [...],
            "roundEnded": [...],
            "roundFreezetimeEnded": [...],
            "roundEndedOfficial": [...],
            "gameHalfEnded": [...],
            "matchStart": [...],
            "matchStartedChanged": [...],
            "warmupChanged": [...],
            "teamSwitch": [...]
        },
        "matchmakingRanks": [                           # Contains a list of players and their win counts and rank info. Only for MM demos.
            {
                "steamID": 76561198060045535,
                "rankChange": 0,
                "rankOld": "The Global Elite",
                "rankNew": "The Global Elite",
                "winCount": 629
            },
            ...
        ],
        "playerConnections": [                          # List of player connect/disconnect events
            {
                "tick": 0,
                "action": "connect",
                "steamID": 76561198000441323
            },
            {
                "tick": 161259,
                "action": "disconnect",
                "steamID": 76561198043315625
            },
            ...
        ],
        "gameRounds": [{...}]                           # Game rounds
    }

Rounds
------

This object contains round information and events. The possible round end reasons are `TargetBombed`, `VIPEscaped`, `VIPKilled`, `TerroristsEscaped`, `CTStoppedEscape`, `TerroristsStopped`, `BombDefused`, `CTWin`, `TerroristsWin`, `Draw`, `HostagesRescued`, `TargetSaved`, `HostagesNotRescued`, `TerroristsNotEscaped`, `VIPNotEscaped`, `GameStart`, `TerroristsSurrender`, `CTSurrender`.

Keep in mind that due to dropped guns which aren't equipped at FreezeTimeEnd, the FreezeTimeEndEqVal may not equal StartEqVal + Spend.

.. code-block:: json

    {
        "roundNum": 1,                         
        "isWarmup": false,                  # true if the round is a warmup round
        "startTick": 6980,
        "freezeTimeEndTick": 7936,          
        "endTick": 14512,                   # Tick when end condition is reached, but round is not officialy over
        "endOfficialTick": 14832,
        "bombPlantTick": 12450,
        "tScore": 0,
        "ctScore": 0,
        "endTScore": 1,
        "endCTScore": 0,
        "ctTeam": "",
        "tTeam": "",
        "winningSide": "T",
        "winningTeam": "",
        "losingTeam": "",
        "roundEndReason": "TerroristsWin",
        "ctFreezeTimeEndEqVal": 3650,        # Eq value at the end of freezetime
        "ctRoundStartEqVal": 1000,           # Eq value at the beginning of the round
        "ctRoundSpendMoney": 2650,           # Money spent in the round
        "ctBuyType": "Full Eco",             # Determined by the FreezeTimeEnd eq value
        "tFreezeTimeEndEqVal": 4400,
        "tRoundStartEqVal": 1000,
        "tRoundSpendMoney": 3400,
        "tBuyType": "Full Eco",
        "ctSide": {                          # Players who were on the CT side at FreezeTimeEnd
            "teamName": "...",
            "players": [{
                "playerName": "...",
                "steamID": 12345
            }, ...]
        },
        "tSide": {...},                      # Players who were on the T side at FreezeTimeEnd
        "kills": [...],                      # Kills
        "damages": [...],                    # Damages
        "grenades": [...],                   # Grenade throws
        "bombEvents": [...],                 # Bomb events (plants, defuses, etc.)
        "weaponFires": [...],                # Shots
        "flashes": [...],                    # Flashes
        "frames": [...]                      # Frames (game snapshots)
    }

Kills
-----

.. code-block:: json

    {
        "tick": 9582, 
        "seconds": 25.71875, 
        "clockTime": "01:30", 
        "attackerSteamID": 76561198088580941, 
        "attackerName": "febix", 
        "attackerTeam": "", 
        "attackerSide": "T", 
        "attackerX": 509.1275939941406, 
        "attackerY": 630.7955322265625, 
        "attackerZ": 86.98412322998047, 
        "attackerViewX": 327.601318359375, 
        "attackerViewY": 1.9775390625, 
        "victimSteamID": 76561198084596669, 
        "victimName": "Rullaan Spotil KANDALFWOZ ;)", 
        "victimTeam": "", 
        "victimSide": "CT", 
        "victimX": 781.4129638671875, 
        "victimY": 491.81201171875, 
        "victimZ": 87.30707550048828, 
        "victimViewX": 153.6328125, 
        "victimViewY": 1.0711669921875, 
        "assisterSteamID": None,                       # If there is an assister, this data will not be None
        "assisterName": None, 
        "assisterTeam": None, 
        "assisterSide": None, 
        "isSuicide": false, 
        "isTeamkill": false, 
        "isWallbang": false, 
        "penetratedObjects": 0, 
        "isFirstKill": true, 
        "isHeadshot": true, 
        "victimBlinded": false, 
        "attackerBlinded": false, 
        "flashThrowerSteamID": None, 
        "flashThrowerName": None, 
        "flashThrowerTeam": None, 
        "flashThrowerSide": None, 
        "noScope": false, 
        "thruSmoke": false, 
        "distance": 305.7054888578491,                 # Distance between attacker and victim in ingame units
        "isTrade": false,                              # Trades determined through the parser parameters. Default is 5 second time window.
        "playerTradedName": None, 
        "playerTradedTeam": None, 
        "playerTradedSteamID": None, 
        "weapon": "Glock-18"
        "weaponClass": "Pistols"
    }

Damages
-------

The possible hit groups are `Generic`, `Head`, `Chest`, `Stomach`, `LeftArm`, `RightArm`, `LeftLeg`, `RightLeg`, `Gear`.

.. code-block:: json

    {
        "tick": 8172, 
        "seconds": 3.6875, 
        "clockTime": "01:52", 
        "attackerSteamID": 76561198035759667, 
        "attackerName": "alo0o0o0o0", 
        "attackerTeam": "", 
        "attackerSide": "T", 
        "attackerX": -1184.6986083984375, 
        "attackerY": 477.1373596191406, 
        "attackerZ": -55.96875, 
        "attackerViewX": 56.79931640625, 
        "attackerViewY": 3.3837890625, 
        "attackerStrafe": false,                 # Was the attacker moving when they shot
        "victimSteamID": 76561197960742750, 
        "victimName": "howl", 
        "victimTeam": "", 
        "victimSide": "T", 
        "victimX": -1125.4398193359375, 
        "victimY": 520.9878540039062, 
        "victimZ": -51.978607177734375, 
        "victimViewX": 9.2230224609375, 
        "victimViewY": 0.6097412109375, 
        "weapon": "Knife", 
        "weaponClass": "Equipment",
        "hpDamage": 61,                          # Can be over 100 (e.g., AWP headshots)
        "hpDamageTaken": 61,                     # Damage actually taken by the victim
        "armorDamage": 5, 
        "armorDamageTaken": 5, 
        "hitGroup": "Generic", 
        "isFriendlyFire": true, 
        "distance": 73.82676464998524, 
        "zoomLevel": 0                           # 0 for no zoom, 1 for half zoom, 2 for full zoom
    }

Grenades
--------

.. code-block:: json

    {
        "throwTick": 8500, 
        "destroyTick": 8860,                  # When was the entity destroyed
        "throwSeconds": 8.8125, 
        "throwClockTime": "01:47", 
        "destroySeconds": 14.4375, 
        "destroyClockTime": "01:41", 
        "throwerSteamID": 76561198098005932, 
        "throwerName": "aidan", 
        "throwerTeam": "", 
        "throwerSide": "CT", 
        "throwerX": 1330.09375, 
        "throwerY": 570.0625, 
        "throwerZ": 200.96875, 
        "grenadeType": "HE Grenade",
        "grenadeX": 53.96875, 
        "grenadeY": 671.5, 
        "grenadeZ": 68.09375, 
        "entityID": 5031578313293207366        # entity ID of the grenade
    }

Bomb Events
-----------

The bomb action can be `defuse`, `defuse_start`, `defuse_aborted`, `plant`, `plant_start`, `plant_aborted`.

.. code-block:: json

    {
        "tick": 12250, 
        "seconds": 67.40625, 
        "clockTime": "00:48", 
        "playerSteamID": 76561198043315625, 
        "playerName": "Beach", 
        "playerTeam": "", 
        "playerX": 2160.965576171875, 
        "playerY": 144.39041137695312, 
        "playerZ": 160.03125, 
        "bombAction": "plant_begin",
        "bombSite": "A"
    }

Weapon Fires
------------

.. code-block:: json

    {
        "tick": 8492, 
        "seconds": 8.6875, 
        "clockTime": "01:47", 
        "playerSteamID": 76561198098005932, 
        "playerName": "aidan", 
        "playerTeam": "", 
        "playerSide": "CT", 
        "playerX": 1377.0318603515625, 
        "playerY": 566.3394775390625, 
        "playerZ": 131.50010681152344, 
        "playerViewX": 175.49560546875, 
        "playerViewY": 355.4901123046875, 
        "playerStrafe": false, 
        "weapon": "HE Grenade",
        "weaponClass": "Grenades", 
        "zoomLevel": 0
    }

Flashes
-------

.. code-block:: json

    {
        "tick": 9518, 
        "seconds": 24.71875, 
        "clockTime": "01:31", 
        "attackerSteamID": 76561198098005932, 
        "attackerName": "aidan", 
        "attackerTeam": "", 
        "attackerSide": "CT", 
        "attackerX": 1434.30224609375, 
        "attackerY": 2835.972412109375, 
        "attackerZ": 127.61480712890625, 
        "attackerViewX": 154.5062255859375, 
        "attackerViewY": 317.7081298828125, 
        "playerSteamID": 76561198060045535, 
        "playerName": "Daniel", 
        "playerTeam": "", 
        "playerSide": "CT", 
        "playerX": 923.0872192382812, 
        "playerY": 2777.9443359375, 
        "playerZ": 128.74525451660156, 
        "playerViewX": 239.095458984375, 
        "playerViewY": 358.2037353515625, 
        "flashDuration": 2.676444416
    }

Frames
------

.. code-block:: json

    {
        "parseKillFrame": true                         # true if the frame was parsed due to a kill
        "tick": 8174, 
        "seconds": 3.71875, 
        "clockTime": "01:52", 
        "t": {
            "side": "T", 
            "teamName": "", 
            "teamEqVal": 3550, 
            "alivePlayers": 5, 
            "totalUtility": 1, 
            "players": [{                              # List of player objects with the following structure
                "steamID": 76561198035759667, 
                "name": "alo0o0o0o0", 
                "team": "", 
                "side": "T", 
                "x": -1179.1435546875, 
                "y": 483.21026611328125, 
                "z": -55.96875, 
                "velocityX": 109.83319854736328, 
                "velocityY": 91.87308502197266, 
                "velocityZ": 0, 
                "viewX": 56.84326171875, 
                "viewY": 3.33984375, 
                "hp": 100, 
                "armor": 0, 
                "activeWeapon": "Knife",               # Weapon the player is currently holding
                "totalUtility": 0, 
                "isAlive": true, 
                "isBlinded": false, 
                "isAirborne": false, 
                "isDucking": false, 
                "isDuckingInProgress": false, 
                "isUnDuckingInProgress": false, 
                "isDefusing": false, 
                "isPlanting": false, 
                "isReloading": false, 
                "isInBombZone": false, 
                "isInBuyZone": false, 
                "isStanding": true, 
                "isScoped": false, 
                "isWalking": false, 
                "isUnknown": false, 
                "inventory": [{                        # List of weapons
                    "weaponName": "Glock-18", 
                    "weaponClass": "Pistols", 
                    "ammoInMagazine": 20, 
                    "ammoInReserve": 120
                }], 
                "spotters": [...],                     # SteamIDs of players that the current player has spotted
                "equipmentValue": 200, 
                "equipmentValueFreezetimeEnd": 200, 
                "equipmentValueRoundStart": 200, 
                "cash": 800, 
                "cashSpendThisRound": 0, 
                "cashSpendTotal": 0,                   # Cash spent the entire game
                "hasHelmet": false, 
                "hasDefuse": false, 
                "hasBomb": false, 
                "ping": 32, 
                "zoomLevel": 0
                }]
            }, 
            "ct": {...},                               # Same structure as "t"
            
            "projectiles": [{...}, ...],               # List of grenade objects
            "smokes": [{...}, ...],                    # List of current smokes
            "fires": [{...}, ...],                     # List of current fires
            "bomb": {"x": 1.23, "y": 4.56, "z": 7.89}, # Bomb position
            "bombPlanted": false, 
            "bombsite": ""
    }