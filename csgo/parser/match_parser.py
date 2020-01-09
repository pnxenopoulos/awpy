import logging
import os
import re
import subprocess
import pandas as pd

from csgo.base import BombEvent, Footstep, Round, Kill, Damage


class CSGOMatchParser:
    """ This class can parse a CSGO match to output events in a logical structure

    Attributes:
        demofile: A string denoting the path to the demo file, which ends in .dem
        logfile: A string denoting the path to the output log file
        match_start: An integer denoting at what line the match starts the parsed text
        rounds: A list of Round objects in the match
    """

    def __init__(self, demofile="", logfile="parser.log", competition=""):
        """ Initialize a CSGOMatchParser object
        """
        self.demofile = demofile
        self.competition = competition
        self.match_start = 0
        self.rounds = []
        self.logfile = logfile
        logging.basicConfig(
            filename=logfile,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.match_name = demofile[:-4]
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
        path = os.path.join(os.path.dirname(__file__), "parse_demofile.go")
        proc = subprocess.Popen(
            ["go", "run", path, "-demo", self.demofile], stdout=subprocess.PIPE
        )
        self.parsed_text = proc.stdout.read().splitlines()
        self.parsed_text = [event.decode("utf-8") for event in self.parsed_text]
        self.parsed_text = [event[:-1] for event in self.parsed_text]
        self.logger.info("Demofile parsing complete")

    def find_match_start(self):
        """ Determine the match start line in our txt file, since it is not found in our Go parser.
        """
        self.logger.info("Finding match start line")
        for i, event in enumerate(self.parsed_text):
            if "ROUND START" in event and "[0, 0]" in event:
                self.match_start = i
        if self.match_start == 0:
            for i, line in enumerate(self.parsed_text):
                if "MATCH START" in line:
                    self.match_start = i
        self.parsed_text = self.parsed_text[self.match_start :]
        if self.match_start == 0:
            self.logger.warning("Match start at 0...likely wrong")
        else:
            self.logger.info("Match start line found at " + str(self.match_start))

    def parse_match(self):
        """ Parse match event text data and structure it in logical format
        """
        self.logger.info("Parsing match text")
        for i, event in enumerate(self.parsed_text):
            if self.match_start == 0 and i == 0:
                current_round = Round()
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
                current_round.start_tick = 0
            if "[MATCH START]" in event:
                current_round = Round()
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
                parsed_line = event.split("] [")[1].replace("]", "").split(",")
                current_round.map_name = parsed_line[0]
                current_round.start_tick = int(parsed_line[1].strip())
            if "[ROUND START]" in event:
                current_round = Round()
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
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
                current_round.footsteps = current_footstep_list
                current_round.kills = current_kills_list
                current_round.damages = current_damages_list
                current_round.bomb_events = current_bomb_events_list
                current_footstep_list = []
                current_kills_list = []
                current_damages_list = []
                current_bomb_events_list = []
                self.rounds.append(current_round)
                self.logger.info("Parsed round " + str(len(self.rounds)))
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
                current_footstep.y_viz = float(third_block[4].strip())
                current_footstep.view_x = float(third_block[5].strip())
                current_footstep.view_y = float(third_block[6].strip())
                current_footstep.area_id = int(third_block[7].strip())
                current_footstep.area_name = third_block[8].replace("]", "").strip()
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
                current_damage.victim_y_viz = float(second_block[4].strip())
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
                current_damage.attacker_y_viz = float(third_block[4].strip())
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
                current_damage.armor_damage = int(sixth_block[1].strip())
                current_damage.weapon_id = CSGOMatchParser.get_weapon(
                    int(sixth_block[2].strip())
                )
                current_damage.hit_group = CSGOMatchParser.get_hit_group(
                    int(sixth_block[3].replace("]", "").strip())
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
                current_kill.victim_y_viz = float(second_block[4].strip())
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
                current_kill.attacker_y_viz = float(third_block[4].strip())
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
                current_kill.weapon_id = CSGOMatchParser.get_weapon(int(sixth_block[0]))
                current_kill.is_wallshot = int(sixth_block[1].strip())
                current_kill.is_headshot = sixth_block[2].replace("]", "").strip()
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
                current_bomb_events_list.append(current_bomb_event)

    def write_bomb_events(self):
        """ Write bomb events to a Pandas dataframe
        """
        bomb_df_list = []
        for i, round in enumerate(self.rounds):
            bomb_events = round.bomb_events
            for be in bomb_events:
                bomb_df_list.append(
                    [
                        self.competition,
                        self.match_name,
                        round.map_name,
                        i,
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
                "CompetitionName",
                "MatchName",
                "MapName",
                "Round",
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
        for i, round in enumerate(self.rounds):
            footsteps = round.footsteps
            for f in footsteps:
                footstep_df_list.append(
                    [
                        self.competition,
                        self.match_name,
                        round.map_name,
                        i,
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
                    ]
                )
        self.footsteps_df = pd.DataFrame(
            footstep_df_list,
            columns=[
                "CompetitionName",
                "MatchName",
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
            ],
        )
        # self.footstep_df.to_csv("player_traj.csv", index=False)

    def write_kills(self):
        """ Write kills to a Pandas dataframe
        """
        kills_df_list = []
        for i, round in enumerate(self.rounds):
            kills = round.kills
            for f in kills:
                kills_df_list.append(
                    [
                        self.competition,
                        self.match_name,
                        round.map_name,
                        i,
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
                "CompetitionName",
                "MatchName",
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
        for i, round in enumerate(self.rounds):
            damages = round.damages
            for f in damages:
                damages_df_list.append(
                    [
                        self.competition,
                        self.match_name,
                        round.map_name,
                        i,
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
                        f.armor_damage,
                        f.weapon_id,
                        f.hit_group,
                    ]
                )
        self.damages_df = pd.DataFrame(
            damages_df_list,
            columns=[
                "CompetitionName",
                "MatchName",
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
        for i, round in enumerate(self.rounds):
            round_df_list.append(
                [
                    self.competition,
                    self.match_name,
                    round.map_name,
                    i,
                    round.start_tick,
                    round.end_tick,
                    round.end_ct_score,
                    round.end_t_score,
                    round.start_t_score,
                    round.start_ct_score,
                    round.round_winner_side,
                    round.round_winner,
                    round.round_loser,
                    round.reason,
                ]
            )
        self.rounds_df = pd.DataFrame(
            round_df_list,
            columns=[
                "CompetitionName",
                "MatchName",
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
            ],
        )
