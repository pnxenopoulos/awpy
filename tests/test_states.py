"""Tests state parsing."""
from awpy.analytics.states import (
    generate_graph_state,
    generate_set_state,
    generate_vector_state,
)
from awpy.parser import DemoParser


class TestStates:
    """Class to test the state parsing.

    Uses:
    www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser."""
        self.parser = DemoParser(demofile="tests/default.dem", log=True, parse_rate=256)
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none."""
        self.parser = None
        self.data = None

    def test_vector_output(self):
        """Tests that vector output is a dict with 3 keys."""
        game_state = generate_vector_state(
            self.data["gameRounds"][7]["frames"][0], self.data["mapName"]
        )
        assert isinstance(game_state, dict)
        assert "ctAlive" in game_state
        assert game_state["ctAlive"] == 5
        game_state = generate_vector_state(
            self.data["gameRounds"][7]["frames"][6], self.data["mapName"]
        )
        assert game_state["ctAlive"] == 2
        assert game_state["tAlive"] == 4

        test_frame = {
            "isKillFrame": False,
            "tick": 79362,
            "seconds": 0.3464566929133858,
            "clockTime": "01:55",
            "t": {
                "side": "T",
                "teamName": "team_Sunk3r",
                "teamEqVal": 28450,
                "alivePlayers": 5,
                "totalUtility": 19,
                "players": [
                    {
                        "steamID": 76561198853008998,
                        "name": "yngtired",
                        "team": "team_Sunk3r",
                        "side": "T",
                        "x": -1526.9036865234375,
                        "y": 496.540771484375,
                        "z": -63.96875,
                        "velocityX": 3.0111472606658936,
                        "velocityY": -218.1503143310547,
                        "velocityZ": 0,
                        "viewX": 265.5120849609375,
                        "viewY": 23.6700439453125,
                        "hp": 100,
                        "armor": 100,
                        "activeWeapon": "Knife",
                        "totalUtility": 3,
                        "isAlive": True,
                        "isBlinded": False,
                        "isAirborne": False,
                        "isDucking": False,
                        "isDuckingInProgress": False,
                        "isUnDuckingInProgress": False,
                        "isDefusing": False,
                        "isPlanting": False,
                        "isReloading": False,
                        "isInBombZone": True,
                        "isInBuyZone": True,
                        "isStanding": True,
                        "isScoped": False,
                        "isWalking": False,
                        "isUnknown": False,
                        "inventory": [
                            {
                                "weaponName": "P250",
                                "weaponClass": "Pistols",
                                "ammoInMagazine": 13,
                                "ammoInReserve": 26,
                            },
                            {
                                "weaponName": "AK-47",
                                "weaponClass": "Rifle",
                                "ammoInMagazine": 30,
                                "ammoInReserve": 90,
                            },
                            {
                                "weaponName": "Molotov",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 0,
                            },
                            {
                                "weaponName": "Smoke Grenade",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 0,
                            },
                            {
                                "weaponName": "Flashbang",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 0,
                            },
                        ],
                        "spotters": [],
                        "equipmentValue": 4900,
                        "equipmentValueFreezetimeEnd": 4900,
                        "equipmentValueRoundStart": 6050,
                        "cash": 6950,
                        "cashSpendThisRound": 900,
                        "cashSpendTotal": 11550,
                        "hasHelmet": True,
                        "hasDefuse": False,
                        "hasBomb": False,
                        "ping": 8,
                        "zoomLevel": 0,
                    },
                ],
            },
            "ct": {
                "side": "CT",
                "teamName": "team_-Fuchshenger",
                "teamEqVal": 22050,
                "alivePlayers": 5,
                "totalUtility": 11,
                "players": [
                    {
                        "steamID": 76561199002916187,
                        "name": "-Fuchshenger",
                        "team": "team_-Fuchshenger",
                        "side": "CT",
                        "x": 2359.920654296875,
                        "y": 2116.4208984375,
                        "z": 128.03125,
                        "velocityX": -79.87870025634766,
                        "velocityY": 188.94065856933594,
                        "velocityZ": 0,
                        "viewX": 125.3485107421875,
                        "viewY": 3.3453369140625,
                        "hp": 100,
                        "armor": 100,
                        "activeWeapon": "Knife",
                        "totalUtility": 3,
                        "isAlive": True,
                        "isBlinded": False,
                        "isAirborne": False,
                        "isDucking": False,
                        "isDuckingInProgress": False,
                        "isUnDuckingInProgress": False,
                        "isDefusing": False,
                        "isPlanting": False,
                        "isReloading": False,
                        "isInBombZone": True,
                        "isInBuyZone": True,
                        "isStanding": True,
                        "isScoped": False,
                        "isWalking": False,
                        "isUnknown": False,
                        "inventory": [
                            {
                                "weaponName": "USP-S",
                                "weaponClass": "Pistols",
                                "ammoInMagazine": 12,
                                "ammoInReserve": 24,
                            },
                            {
                                "weaponName": "M4A1",
                                "weaponClass": "Rifle",
                                "ammoInMagazine": 25,
                                "ammoInReserve": 75,
                            },
                            {
                                "weaponName": "Incendiary Grenade",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 0,
                            },
                            {
                                "weaponName": "HE Grenade",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 0,
                            },
                            {
                                "weaponName": "Flashbang",
                                "weaponClass": "Grenade",
                                "ammoInMagazine": 1,
                                "ammoInReserve": 1,
                            },
                        ],
                        "spotters": [],
                        "equipmentValue": 5400,
                        "equipmentValueFreezetimeEnd": 5400,
                        "equipmentValueRoundStart": 200,
                        "cash": 0,
                        "cashSpendThisRound": 5200,
                        "cashSpendTotal": 15100,
                        "hasHelmet": True,
                        "hasDefuse": False,
                        "hasBomb": False,
                        "ping": 7,
                        "zoomLevel": 0,
                    },
                ],
            },
            "bombPlanted": False,
            "bombsite": "",
            "bomb": {"x": -449.28125, "y": 667.375, "z": -31.5},
            "projectiles": [
                {
                    "projectileType": "HE Grenade",
                    "x": 187.59375,
                    "y": 1437.125,
                    "z": 203.0625,
                },
                {
                    "projectileType": "HE Grenade",
                    "x": 271.9375,
                    "y": 1605.3125,
                    "z": 266.15625,
                },
            ],
            "smokes": [],
            "fires": [
                {
                    "uniqueID": 5219776352469082857,
                    "x": 1202.21875,
                    "y": 33.71875,
                    "z": 258.03125,
                },
                {
                    "uniqueID": 7620914220791404896,
                    "x": 155.90625,
                    "y": 1504.90625,
                    "z": 110.09375,
                },
                {
                    "uniqueID": 5806921737724242314,
                    "x": 468.03125,
                    "y": 2108.28125,
                    "z": 134.75,
                },
            ],
        }

        game_state = generate_vector_state(test_frame, "de_inferno")
        assert game_state["ctBombZone"] == 1
        assert game_state["tBombZone"] == 1

    def test_graph_output(self):
        """Tests that vector output is a dict with 3 keys."""
        game_state = generate_graph_state(self.data["gameRounds"][7]["frames"][0])
        assert isinstance(game_state, dict)

        assert "ct" in game_state
        assert isinstance(game_state["ct"], list)
        assert "t" in game_state
        assert isinstance(game_state["t"], list)
        assert "global" in game_state
        assert isinstance(game_state["global"], list)

    def test_set_output(self):
        """Tests that set output is a dict with 3 keys."""
        game_state = generate_set_state(self.data["gameRounds"][7]["frames"][0])
        assert isinstance(game_state, dict)

        assert "ct" in game_state
        assert isinstance(game_state["ct"], list)
        assert "t" in game_state
        assert isinstance(game_state["t"], list)
        assert "global" in game_state
        assert isinstance(game_state["global"], list)
