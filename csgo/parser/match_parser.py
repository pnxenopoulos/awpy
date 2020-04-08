""" Parsing class for demofile
"""

import logging
import os
import re
import subprocess
import pandas as pd

from csgo.events import BombEvent, Footstep, Round, Kill, Damage, Grenade


class CSGOMatchParser:
    """ This class can parse a CSGO match to output events in a logical structure

    Attributes:
        demofile: A string denoting the path to the demo file, which ends in .dem
        logfile: A string denoting the path to the output log file
        competition_name: A string denoting the competition name of the demo
        match_name: A string denoting the match name of the demo
        game_date: A string denoting the date of the demo
        game_time: A string denoting the time of day of the demo
    """

    def __init__(
        self,
        demofile="",
        logfile="parser.log",
        competition_name="",
        match_name="",
        game_date="",
        game_time="",
    ):
        """ Initialize a CSGOMatchParser object
        """
        self.demofile = demofile
        self.competition_name = competition_name
        self.match_name = match_name
        self.game_date = game_date
        self.game_time = game_time
        self.game_id = (
            competition_name + "_" + match_name + "_" + game_date + "_" + game_time
        )
        self.rounds = []
        self.demo_error = False
        self.logfile = logfile
        logging.basicConfig(
            filename=self.logfile,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("CSGOMatchParser")
        self.logger.info("Initialized CSGOMatchParser with demofile " + self.demofile)

    @staticmethod
    def get_hit_group(x):
        """ Return hitgroup in string
        """
        hit_groups = {
            1: "Generic",
            2: "Head",
            3: "Chest",
            4: "Stomach",
            5: "LeftArm",
            6: "RightArm",
            7: "LeftLeg",
            8: "RightLeg",
            9: "Gear",
        }
        return hit_groups.get(x, "NA")

    @staticmethod
    def get_weapon(x):
        """ Return weapon name
        """
        weapon_ids = {
            0: "Unknown",
            1: "P2000",
            2: "Glock",
            3: "P250",
            4: "Deagle",
            5: "FiveSeven",
            6: "DualBerettas",
            7: "Tec9",
            8: "CZ",
            9: "USP",
            10: "Revolver",
            101: "MP7",
            102: "MP9",
            103: "Bizon",
            104: "Mac10",
            105: "UMP",
            106: "P90",
            107: "MP5",
            201: "SawedOff",
            202: "Nova",
            203: "Swag7",
            204: "XM1014",
            205: "M249",
            206: "Negev",
            301: "Galil",
            302: "Famas",
            303: "AK47",
            304: "M4A4",
            305: "M4A1",
            306: "Scout",
            307: "SG556",
            308: "AUG",
            309: "AWP",
            310: "Scar20",
            311: "G3SG1",
            401: "Zeus",
            402: "Kevlar",
            403: "Helmet",
            404: "Bomb",
            405: "Knife",
            406: "DefuseKit",
            407: "World",
            501: "Decoy",
            502: "Molotov",
            503: "Incendiary",
            504: "Flash",
            505: "Smoke",
            506: "HE",
        }
        return weapon_ids.get(x, "NA")

    @staticmethod
    def get_round_reason(x):
        """ Return round reason name
        """
        round_reasons = {
            1: "TargetBombed",
            7: "BombDefused",
            8: "CTWin",
            9: "TerroristsWin",
            10: "Draw",
            12: "TargetSaved",
        }
        return round_reasons.get(x, "NA")

    def parse_demofile(self):
        """ Parse a demofile using the Go script parse_demofile.go
        """
        self.logger.info(
            "Starting CSGO Go demofile parser, reading in " + self.demofile
        )
        self.match_event_id = self.demofile[self.demofile.rfind("/") + 1 : -4]
        path = os.path.join(os.path.dirname(__file__), "")
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_demofile.go",
                "-demo",
                os.getcwd() + "/" + self.demofile,
            ],
            stdout=subprocess.PIPE,
            cwd=path,
        )
        self.parsed_text = proc.stdout.read().splitlines()
        self.parsed_text = [event.decode("utf-8") for event in self.parsed_text]
        self.parsed_text = [event[:-1] for event in self.parsed_text]
        if "[ERROR]" in self.parsed_text[0]:
            self.demo_error = True
        self.logger.info("Demofile parsing complete")

    def parse_match(self):
        """ Parse match event text data and structure it in logical format
        """
        self.logger.info("Parsing match text")
        self.rounds = []
        # Set default round stuff
        current_round = Round()
        current_footstep_list = []
        current_kills_list = []
        current_damages_list = []
        current_bomb_events_list = []
        current_grenade_list = []
        current_round.start_tick = 0
        for event in self.parsed_text:
            if "[MATCH START]" in event:
                current_round = Round()
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
                current_grenade_list = []
                parsed_line = event.split("] [")[1].replace("]", "").split(",")
                current_round.map_name = parsed_line[0]
                current_round.start_tick = int(parsed_line[1].strip())
            if "[ROUND START]" in event:
                current_round = Round()
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
                current_grenade_list = []
                split_line = event.split("] [")
                # First block
                first_block = split_line[1].split(",")
                current_round.map_name = first_block[0]
                current_round.start_tick = int(first_block[1].strip())
                # Second block
                second_block = split_line[2].replace("]", "").split(",")
                current_round.start_t_score = int(second_block[0])
                current_round.start_ct_score = int(second_block[1].strip())
            if "[ROUND END]" in event and "DRAW" not in event:
                split_line = event.split("] [")
                # First block
                first_block = split_line[1].split(",")
                current_round.map_name = first_block[0]
                current_round.end_tick = int(first_block[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_round.end_t_score = int(second_block[0])
                current_round.end_ct_score = int(second_block[1].strip())
                # Third block
                third_block = split_line[3].replace("]", "").split(",")
                current_round.round_winner_side = third_block[0]
                current_round.round_winner = third_block[1].strip()
                current_round.round_loser = third_block[2].strip()
                current_round.reason = CSGOMatchParser.get_round_reason(
                    int(third_block[3].strip())
                )
                # Add events to round
                current_round.footsteps = current_footstep_list
                current_round.kills = current_kills_list
                current_round.damages = current_damages_list
                current_round.bomb_events = current_bomb_events_list
                current_round.grenades = current_grenade_list
                # Add round to list
                self.rounds.append(current_round)
                self.logger.info("Parsed round end " + str(len(self.rounds)))
            if "[ROUND PURCHASE]" in event:
                split_line = event.split("] [")
                # First block
                first_block = split_line[1].split(",")
                current_round.map_name = first_block[0]
                # Second block
                second_block = split_line[2].split(",")
                current_round.t_cash_spent_total = int(second_block[1])
                current_round.t_cash_spent_round = int(second_block[2])
                current_round.t_eq_val = int(second_block[3])
                # Third block
                third_block = split_line[3].replace("]", "").split(",")
                current_round.ct_cash_spent_total = int(third_block[1])
                current_round.ct_cash_spent_round = int(third_block[2])
                current_round.ct_eq_val = int(third_block[3])
            if "[ROUND END OFFICIAL]" in event:
                split_line = event.split("] [")
                # First block
                first_block = split_line[1].split(",")
                current_round.map_name = first_block[0]
                current_round.end_tick = int(first_block[1].replace("]", "").strip())
                # Add events to round
                current_round.footsteps = current_footstep_list
                current_round.kills = current_kills_list
                current_round.damages = current_damages_list
                current_round.bomb_events = current_bomb_events_list
                current_round.grenades = current_grenade_list
                # Add round to list
                if len(self.rounds) > 0:
                    self.rounds[-1] = current_round
                self.logger.info("Parsed round end official " + str(len(self.rounds)))
            if "[FOOTSTEP]" in event:
                current_footstep = Footstep()
                split_line = event.split("] [")
                # First block
                current_footstep.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_footstep.steam_id = int(second_block[0])
                current_footstep.player_name = second_block[1].strip()
                current_footstep.team = second_block[2].strip()
                current_footstep.side = second_block[3].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_footstep.x = float(third_block[0])
                current_footstep.y = float(third_block[1].strip())
                current_footstep.z = float(third_block[2].strip())
                current_footstep.x_viz = float(third_block[3].strip())
                current_footstep.y_viz = float(third_block[4].strip()) * -1
                current_footstep.view_x = float(third_block[5].strip())
                current_footstep.view_y = float(third_block[6].strip())
                current_footstep.area_id = int(third_block[7].strip())
                current_footstep.area_name = third_block[8].strip()
                current_footstep.distance_bombsite_a = int(third_block[9].strip())
                current_footstep.distance_bombsite_b = int(
                    third_block[10].replace("]", "").strip()
                )
                current_footstep_list.append(current_footstep)
            if "[DAMAGE]" in event:
                current_damage = Damage()
                split_line = event.split("] [")
                # First block
                current_damage.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_damage.victim_x = float(second_block[0])
                current_damage.victim_y = float(second_block[1].strip())
                current_damage.victim_z = float(second_block[2].strip())
                current_damage.victim_x_viz = float(second_block[3].strip())
                current_damage.victim_y_viz = float(second_block[4].strip()) * -1
                current_damage.victim_view_x = float(second_block[5].strip())
                current_damage.victim_view_y = float(second_block[6].strip())
                current_damage.victim_area_id = int(second_block[7].strip())
                current_damage.victim_area_name = second_block[8].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_damage.attacker_x = float(third_block[0])
                current_damage.attacker_y = float(third_block[1].strip())
                current_damage.attacker_z = float(third_block[2].strip())
                current_damage.attacker_x_viz = float(third_block[3].strip())
                current_damage.attacker_y_viz = float(third_block[4].strip()) * -1
                current_damage.attacker_view_x = float(third_block[5].strip())
                current_damage.attacker_view_y = float(third_block[6].strip())
                current_damage.attacker_area_id = int(third_block[7].strip())
                current_damage.attacker_area_name = third_block[8].strip()
                # Fourth block
                fourth_block = split_line[4].split(",")
                current_damage.victim_id = int(fourth_block[0])
                current_damage.victim_name = fourth_block[1].strip()
                current_damage.victim_team = fourth_block[2].strip()
                current_damage.victim_side = fourth_block[3].strip()
                current_damage.victim_team_eq_val = int(fourth_block[4].strip())
                # Fifth block
                fifth_block = split_line[5].split(",")
                current_damage.attacker_id = int(fifth_block[0])
                current_damage.attacker_name = fifth_block[1].strip()
                current_damage.attacker_team = fifth_block[2].strip()
                current_damage.attacker_side = fifth_block[3].strip()
                current_damage.attacker_team_eq_val = int(fifth_block[4].strip())
                # Sixth block
                sixth_block = split_line[6].split(",")
                current_damage.hp_damage = int(sixth_block[0])
                current_damage.kill_hp_damage = int(sixth_block[1])
                current_damage.armor_damage = int(sixth_block[2].strip())
                current_damage.weapon_id = CSGOMatchParser.get_weapon(
                    int(sixth_block[3].strip())
                )
                current_damage.hit_group = CSGOMatchParser.get_hit_group(
                    int(sixth_block[4].replace("]", "").strip())
                )
                # Add current damage to round
                current_damages_list.append(current_damage)
            if "[KILL]" in event:
                current_kill = Kill()
                split_line = event.split("] [")
                # First block
                current_kill.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_kill.victim_x = float(second_block[0])
                current_kill.victim_y = float(second_block[1].strip())
                current_kill.victim_z = float(second_block[2].strip())
                current_kill.victim_x_viz = float(second_block[3].strip())
                current_kill.victim_y_viz = float(second_block[4].strip()) * -1
                current_kill.victim_view_x = float(second_block[5].strip())
                current_kill.victim_view_y = float(second_block[6].strip())
                current_kill.victim_area_id = int(second_block[7].strip())
                current_kill.victim_area_name = second_block[8].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_kill.attacker_x = float(third_block[0])
                current_kill.attacker_y = float(third_block[1].strip())
                current_kill.attacker_z = float(third_block[2].strip())
                current_kill.attacker_x_viz = float(third_block[3].strip())
                current_kill.attacker_y_viz = float(third_block[4].strip()) * -1
                current_kill.attacker_view_x = float(third_block[5].strip())
                current_kill.attacker_view_y = float(third_block[6].strip())
                current_kill.attacker_area_id = int(third_block[7].strip())
                current_kill.attacker_area_name = third_block[8].strip()
                # Fourth block
                fourth_block = split_line[4].split(",")
                current_kill.victim_id = int(fourth_block[0])
                current_kill.victim_name = fourth_block[1].strip()
                current_kill.victim_team = fourth_block[2].strip()
                current_kill.victim_side = fourth_block[3].strip()
                current_kill.victim_team_eq_val = int(fourth_block[4].strip())
                # Fifth block
                fifth_block = split_line[5].split(",")
                current_kill.attacker_id = int(fifth_block[0])
                current_kill.attacker_name = fifth_block[1].strip()
                current_kill.attacker_team = fifth_block[2].strip()
                current_kill.attacker_side = fifth_block[3].strip()
                current_kill.attacker_team_eq_val = int(fifth_block[4].strip())
                # Sixth block
                sixth_block = split_line[6].split(",")
                current_kill.assister_id = int(sixth_block[0])
                current_kill.assister_name = sixth_block[1].strip()
                current_kill.assister_team = sixth_block[2].strip()
                current_kill.assister_side = sixth_block[3].strip()
                # Seventh block
                seventh_block = split_line[7].split(",")
                current_kill.weapon_id = CSGOMatchParser.get_weapon(int(seventh_block[0]))
                current_kill.is_wallshot = int(seventh_block[1].strip())
                current_kill.is_headshot = seventh_block[2].replace("]", "").strip()
                if current_kill.is_headshot == "true":
                    current_kill.is_headshot = 1
                else:
                    current_kill.is_headshot = 0
                # Add current damage to round
                current_kills_list.append(current_kill)
            if "[BOMB PLANT]" in event:
                current_bomb_event = BombEvent()
                split_line = event.split("] [")
                # First block
                current_bomb_event.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_bomb_event.steam_id = int(second_block[0])
                current_bomb_event.player_name = second_block[1].strip()
                current_bomb_event.team = second_block[2].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_bomb_event.x = float(third_block[0])
                current_bomb_event.y = float(third_block[1].strip())
                current_bomb_event.z = float(third_block[2].strip())
                current_bomb_event.area_id = int(third_block[3].strip())
                current_bomb_event.bomb_site = third_block[4].replace("]", "").strip()
                current_bomb_event.event_type = "Plant"
                if len(current_bomb_events_list) < 2:
                    current_bomb_events_list.append(current_bomb_event)
            if "[BOMB DEFUSE]" in event:
                current_bomb_event = BombEvent()
                split_line = event.split("] [")
                # First block
                current_bomb_event.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_bomb_event.steam_id = int(second_block[0])
                current_bomb_event.player_name = second_block[1].strip()
                current_bomb_event.team = second_block[2].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_bomb_event.x = float(third_block[0])
                current_bomb_event.y = float(third_block[1].strip())
                current_bomb_event.z = float(third_block[2].strip())
                current_bomb_event.area_id = int(third_block[3].strip())
                current_bomb_event.bomb_site = third_block[4].replace("]", "").strip()
                current_bomb_event.event_type = "Defuse"
                if len(current_bomb_events_list) < 2:
                    current_bomb_events_list.append(current_bomb_event)
            if "[BOMB EXPLODE]" in event:
                current_bomb_event = BombEvent()
                split_line = event.split("] [")
                # First block
                current_bomb_event.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_bomb_event.steam_id = int(second_block[0])
                current_bomb_event.player_name = second_block[1].strip()
                current_bomb_event.team = second_block[2].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_bomb_event.x = float(third_block[0])
                current_bomb_event.y = float(third_block[1].strip())
                current_bomb_event.z = float(third_block[2].strip())
                current_bomb_event.area_id = int(third_block[3].strip())
                current_bomb_event.bomb_site = third_block[4].replace("]", "").strip()
                current_bomb_event.event_type = "Explode"
                if len(current_bomb_events_list) < 2:
                    current_bomb_events_list.append(current_bomb_event)
            if "[GRENADE]" in event:
                current_grenade = Grenade()
                split_line = event.split("] [")
                # First block
                current_grenade.tick = int(split_line[1].split(",")[1].strip())
                # Second block
                second_block = split_line[2].split(",")
                current_grenade.steam_id = int(second_block[0])
                current_grenade.player_name = second_block[1].strip()
                current_grenade.team = second_block[2].strip()
                current_grenade.side = second_block[3].strip()
                # Third block
                third_block = split_line[3].split(",")
                current_grenade.x = float(third_block[0])
                current_grenade.y = float(third_block[1].strip())
                current_grenade.z = float(third_block[2].strip())
                current_grenade.x_viz = float(third_block[3].strip())
                current_grenade.y_viz = float(third_block[4].strip()) * -1
                current_grenade.area_id = int(third_block[5].strip())
                current_grenade.area_name = third_block[6].strip()
                current_grenade.grenade_type = CSGOMatchParser.get_weapon(
                    int(third_block[7].replace("]", "").strip())
                )
                # Add current grenades to round
                current_grenade_list.append(current_grenade)
        # Clean the rounds info
        self.clean_rounds()

    def parse(self):
        """ Parse wrapper function
        """
        self.parse_demofile()
        if not self.demo_error:
            self.parse_match()
            self.write_data()
            return self.dataframes
        else:
            return "Match has parsing error"

    def clean_rounds(self):
        """ Function to clean the rounds list
        """
        # Round cleaning
        round_score_total = []
        for i, r in enumerate(self.rounds):
            round_score_total.append(r.end_ct_score + r.end_t_score)
        start_round_idx = 0
        for i, score in enumerate(round_score_total):
            if i == 0 and (score == 1 or score == 0) and round_score_total[i + 1] == 2:
                start_round_idx = i
            else:
                if (
                    i != len(round_score_total) - 1
                    and (score == 1 or score == 0)
                    and round_score_total[i + 1] == 1
                ):
                    start_round_idx = i
        self.rounds = self.rounds[start_round_idx:]
        total_popped = 0
        for i, r in enumerate(self.rounds):
            score = r.end_ct_score + r.end_t_score
            if (score == 0 or score == 1) and i > 0:
                self.rounds.pop(i - total_popped)
                total_popped = total_popped + 1

    def write_grenades(self):
        """ Write grenade events to a Pandas dataframe
        """
        grenade_df_list = []
        for i, r in enumerate(self.rounds):
            grenades = r.grenades
            for g in grenades:
                grenade_df_list.append(
                    [
                        self.game_id,
                        self.competition_name,
                        self.match_name,
                        self.game_date,
                        self.game_time,
                        r.map_name,
                        i + 1,
                        g.tick,
                        g.steam_id,
                        g.player_name,
                        g.team,
                        g.side,
                        g.x,
                        g.y,
                        g.z,
                        g.x_viz,
                        g.y_viz,
                        g.area_id,
                        g.area_name,
                        g.grenade_type,
                    ]
                )
        self.grenades_df = pd.DataFrame(
            grenade_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "Tick",
                "SteamID",
                "PlayerName",
                "Team",
                "Side",
                "X",
                "Y",
                "Z",
                "XViz",
                "YViz",
                "AreaID",
                "AreaName",
                "GrenadeType",
            ],
        )

    def write_bomb_events(self):
        """ Write bomb events to a Pandas dataframe
        """
        bomb_df_list = []
        for i, r in enumerate(self.rounds):
            bomb_events = r.bomb_events
            for be in bomb_events:
                bomb_df_list.append(
                    [
                        self.game_id,
                        self.competition_name,
                        self.match_name,
                        self.game_date,
                        self.game_time,
                        r.map_name,
                        i + 1,
                        be.tick,
                        be.steam_id,
                        be.player_name,
                        be.team,
                        be.area_id,
                        be.bomb_site,
                        be.event_type,
                    ]
                )
        self.bomb_df = pd.DataFrame(
            bomb_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "Tick",
                "SteamID",
                "PlayerName",
                "Team",
                "AreaID",
                "BombSite",
                "EventType",
            ],
        )

    def write_footsteps(self):
        """ Write footsteps to a Pandas dataframe
        """
        footstep_df_list = []
        for i, r in enumerate(self.rounds):
            footsteps = r.footsteps
            for f in footsteps:
                footstep_df_list.append(
                    [
                        self.game_id,
                        self.competition_name,
                        self.match_name,
                        self.game_date,
                        self.game_time,
                        r.map_name,
                        i + 1,
                        f.tick,
                        f.steam_id,
                        f.player_name,
                        f.team,
                        f.side,
                        f.x,
                        f.y,
                        f.z,
                        f.x_viz,
                        f.y_viz,
                        f.view_x,
                        f.view_y,
                        f.area_id,
                        f.area_name,
                        f.distance_bombsite_a,
                        f.distance_bombsite_b,
                    ]
                )
        self.footsteps_df = pd.DataFrame(
            footstep_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "Tick",
                "SteamID",
                "PlayerName",
                "Team",
                "Side",
                "X",
                "Y",
                "Z",
                "XViz",
                "YViz",
                "ViewX",
                "ViewY",
                "AreaID",
                "AreaName",
                "DistanceBombsiteA",
                "DistanceBombsiteB",
            ],
        )
        # self.footstep_df.to_csv("player_traj.csv", index=False)

    def write_kills(self):
        """ Write kills to a Pandas dataframe
        """
        kills_df_list = []
        for i, r in enumerate(self.rounds):
            kills = r.kills
            for f in kills:
                kills_df_list.append(
                    [
                        self.game_id,
                        self.competition_name,
                        self.match_name,
                        self.game_date,
                        self.game_time,
                        r.map_name,
                        i + 1,
                        f.tick,
                        f.victim_x,
                        f.victim_y,
                        f.victim_z,
                        f.victim_x_viz,
                        f.victim_y_viz,
                        f.victim_view_x,
                        f.victim_view_y,
                        f.victim_area_id,
                        f.victim_area_name,
                        f.attacker_x,
                        f.attacker_y,
                        f.attacker_z,
                        f.attacker_x_viz,
                        f.attacker_y_viz,
                        f.attacker_view_x,
                        f.attacker_view_y,
                        f.attacker_area_id,
                        f.attacker_area_name,
                        f.victim_id,
                        f.victim_name,
                        f.victim_team,
                        f.victim_side,
                        f.victim_team_eq_val,
                        f.attacker_id,
                        f.attacker_name,
                        f.attacker_team,
                        f.attacker_side,
                        f.attacker_team_eq_val,
                        f.weapon_id,
                        f.is_wallshot,
                        f.is_headshot,
                    ]
                )
        self.kills_df = pd.DataFrame(
            kills_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "Tick",
                "VictimX",
                "VictimY",
                "VictimZ",
                "VictimXViz",
                "VictimYViz",
                "VictimViewX",
                "VictimViewY",
                "VictimAreaID",
                "VictimAreaName",
                "AttackerX",
                "AttackerY",
                "AttackerZ",
                "AttackerXViz",
                "AttackerYViz",
                "AttackerViewX",
                "AttackerViewY",
                "AttackerAreaID",
                "AttackerAreaName",
                "VictimID",
                "VictimName",
                "VictimTeam",
                "VictimSide",
                "VictimTeamEqVal",
                "AttackerID",
                "AttackerName",
                "AttackerTeam",
                "AttackerSide",
                "AttackerTeamEqVal",
                "WeaponID",
                "IsWallshot",
                "IsHeadshot",
            ],
        )
        # self.kills_df.to_csv("kills.csv", index=False)

    def write_damages(self):
        """ Write damages to a Pandas dataframe
        """
        damages_df_list = []
        for i, r in enumerate(self.rounds):
            damages = r.damages
            for f in damages:
                damages_df_list.append(
                    [
                        self.game_id,
                        self.competition_name,
                        self.match_name,
                        self.game_date,
                        self.game_time,
                        r.map_name,
                        i + 1,
                        f.tick,
                        f.victim_x,
                        f.victim_y,
                        f.victim_z,
                        f.victim_x_viz,
                        f.victim_y_viz,
                        f.victim_view_x,
                        f.victim_view_y,
                        f.victim_area_id,
                        f.victim_area_name,
                        f.attacker_x,
                        f.attacker_y,
                        f.attacker_z,
                        f.attacker_x_viz,
                        f.attacker_y_viz,
                        f.attacker_view_x,
                        f.attacker_view_y,
                        f.attacker_area_id,
                        f.attacker_area_name,
                        f.victim_id,
                        f.victim_name,
                        f.victim_team,
                        f.victim_side,
                        f.victim_team_eq_val,
                        f.attacker_id,
                        f.attacker_name,
                        f.attacker_team,
                        f.attacker_side,
                        f.attacker_team_eq_val,
                        f.hp_damage,
                        f.kill_hp_damage,
                        f.armor_damage,
                        f.weapon_id,
                        f.hit_group,
                    ]
                )
        self.damages_df = pd.DataFrame(
            damages_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "Tick",
                "VictimX",
                "VictimY",
                "VictimZ",
                "VictimXViz",
                "VictimYViz",
                "VictimViewX",
                "VictimViewY",
                "VictimAreaID",
                "VictimAreaName",
                "AttackerX",
                "AttackerY",
                "AttackerZ",
                "AttackerXViz",
                "AttackerYViz",
                "AttackerViewX",
                "AttackerViewY",
                "AttackerAreaID",
                "AttackerAreaName",
                "VictimID",
                "VictimName",
                "VictimTeam",
                "VictimSide",
                "VictimTeamEqVal",
                "AttackerID",
                "AttackerName",
                "AttackerTeam",
                "AttackerSide",
                "AttackerTeamEqVal",
                "HpDamage",
                "KillHpDamage",
                "ArmorDamage",
                "WeaponID",
                "HitGroup",
            ],
        )
        # self.damages_df.to_csv("damages.csv", index=False)

    def write_rounds(self):
        """ Write rounds to Pandas dataframe
        """
        round_df_list = []
        for i, r in enumerate(self.rounds):
            round_df_list.append(
                [
                    self.game_id,
                    self.competition_name,
                    self.match_name,
                    self.game_date,
                    self.game_time,
                    r.map_name,
                    i + 1,
                    r.start_tick,
                    r.end_tick,
                    r.end_ct_score,
                    r.end_t_score,
                    r.start_t_score,
                    r.start_ct_score,
                    r.round_winner_side,
                    r.round_winner,
                    r.round_loser,
                    r.reason,
                    r.ct_cash_spent_total,
                    r.ct_cash_spent_round,
                    r.ct_eq_val,
                    r.t_cash_spent_total,
                    r.t_cash_spent_round,
                    r.t_eq_val,
                ]
            )
        self.rounds_df = pd.DataFrame(
            round_df_list,
            columns=[
                "GameID",
                "CompetitionName",
                "MatchName",
                "GameDate",
                "GameTime",
                "MapName",
                "RoundNum",
                "StartTick",
                "EndTick",
                "EndCTScore",
                "EndTScore",
                "StartTScore",
                "StartCTScore",
                "RoundWinnerSide",
                "RoundWinner",
                "RoundLoser",
                "Reason",
                "CTCashSpentTotal",
                "CTCashSpentRound",
                "CTEqVal",
                "TCashSpentTotal",
                "TCashSpentRound",
                "TEqVal",
            ],
        )

    def write_data(self):
        """ Wrapper function to write a dictionary of Pandas dataframes
        """
        self.dataframes = {}
        self.write_rounds()
        self.write_footsteps()
        self.write_damages()
        self.write_kills()
        self.write_bomb_events()
        self.write_grenades()
        self.dataframes["Rounds"] = self.rounds_df
        self.dataframes["Footsteps"] = self.footsteps_df
        self.dataframes["Damages"] = self.damages_df
        self.dataframes["Kills"] = self.kills_df
        self.dataframes["BombEvents"] = self.bomb_df
        self.dataframes["Grenades"] = self.grenades_df
        return self.dataframes
