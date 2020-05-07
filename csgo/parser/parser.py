""" Parsing class for demofile
"""

import logging
import os
import re
import subprocess

from csgo.entities import Game, Round

class MatchParser:
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
        """ Initialize a MatchParser object
        """
        self.demofile = demofile
        self.competition_name = competition_name
        self.match_name = match_name
        self.game_date = game_date
        self.game_time = game_time
        self.game_id = (
            competition_name + "_" + match_name + "_" + game_date + "_" + game_time
        )
        self.game = Game(game_id=self.game_id)
        self.demo_error = False
        self.logfile = logfile
        logging.basicConfig(
            filename=self.logfile,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("MatchParser")
        self.logger.info("Initialized MatchParser with demofile " + self.demofile)

    @staticmethod
    def get_round_reason(reason):
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
        return round_reasons.get(reason, "NA")

    def parse_demofile(self):
        """ Parse a demofile using the Go script parse_demo.go
        """
        self.logger.info(
            "Starting CSGO Go demofile parser on " + self.demofile
        )
        path = os.path.join(os.path.dirname(__file__), "")
        proc = subprocess.Popen(
            [
                "go",
                "run",
                "parse_demo.go",
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
        # Get map from first print
        self.game.map_name = self.parsed_text[0].split("] [")[1][:-1]
        # Set default round params
        current_round = Round()
        current_round.start_tick = 0
        for event in self.parsed_text[1:]:
            if "[MATCH START]" in event:
                current_round = Round()
                split_line = event.split("] [")[1].replace("]", "").split(",")
                current_round.start_tick = int(split_line[0].strip())
            if "[ROUND START]" in event:
                current_round = Round()
                split_line = event.split("] [")
                # First block
                current_round.start_tick = int(split_line[1])
                # Second block
                second_block = split_line[2].replace("]", "").split(",")
                current_round.start_t_score = int(second_block[0])
                current_round.start_ct_score = int(second_block[1].strip())
            if "[ROUND END]" in event and "DRAW" not in event:
                split_line = event.split("] [")
                # First block
                current_round.end_tick = int(split_line[1])
                # Second block
                second_block = split_line[2].split(",")
                current_round.end_t_score = int(second_block[0])
                current_round.end_ct_score = int(second_block[1].strip())
                # Third block
                third_block = split_line[3].replace("]", "").split(",")
                current_round.round_winner_side = third_block[0]
                current_round.round_winner = third_block[1].strip()
                current_round.round_loser = third_block[2].strip()
                current_round.reason = MatchParser.get_round_reason(
                    int(third_block[3].strip())
                )
                # Add round to list
                self.game.rounds.append(current_round)
                self.logger.info("Parsed round end " + str(len(self.game.rounds)))
            if "[ROUND PURCHASE]" in event:
                split_line = event.split("] [")
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
                current_round.end_tick = int(split_line[1].replace("]", "").strip())
                # Add round to list
                if len(self.game.rounds) > 0:
                    self.game.rounds[-1] = current_round
                self.logger.info("Parsed round end official " + str(len(self.game.rounds)))
            if "[NEW PLAYER]" in event:
                player_info = split_line[1].replace("]", "").strip()
                player_info_list = player_info.split(" ")
                self.game.players[player_info_list[0]]["Name"] = player_info_list[1]
                self.game.players[player_info_list[0]]["Team"] = player_info_list[2]
