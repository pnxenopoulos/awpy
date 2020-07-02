class Grenade:
    """ 
    Detail a grenade event. Does not include damage information.

    Attributes:
        tick (int)            : Game tick at time of event
        sec (float)           : Seconds since round start
        player_name (string)  : Player's username
        player_id (int)       : Player's steam id
        team (string)         : Player's team/clan name
        side (string)         : Player's side (T or CT)
        x (float)             : X position of grenade
        y (float)             : Y position of grenade
        z (float)             : Z position of grenade
        x_viz (float)         : Grenade's X position for visualization
        y_viz (float)         : Grenade's Y position for visualization
        area_id (int)         : Grenade's location as nav file area id
        area_name (string)    : Grenade's location as area name from nav file
        grenade_type (string) : Grenade type
    """

    def __init__(
        self,
        tick=0,
        sec=0,
        player_name="",
        player_id=0,
        team="",
        side="",
        x=0,
        y=0,
        z=0,
        x_viz=0,
        y_viz=0,
        area_id=0,
        area_name="",
        grenade_type="",
    ):
        self.tick = tick
        self.sec = sec
        self.player_name = player_name
        self.player_id = player_id
        self.team = team
        self.side = side
        self.x = x
        self.y = y
        self.z = z
        self.x_viz = x_viz
        self.y_viz = y_viz
        self.area_id = area_id
        self.area_name = area_name
        self.grenade_type = grenade_type


class BombEvent:
    """ 
    Detail a Bomb Plant/Defuse event

    Attributes:
        tick (int)          : Game tick at time of event
        sec (float)         : Seconds since round start
        player_name (string): Player's username
        player_id (int)     : Player's steam id
        team (string)       : Player's team/clan name
        x (float)           : X position of bomb event
        y (float)           : Y position of bomb event
        z (float)           : Z position of bomb event
        area_id (int)       : Location of event as nav file area id
        bomb_site (string)  : Bomb site (A or B)
        event_type (string) : Plant, defuse, explode
    """

    def __init__(
        self,
        tick=0,
        sec=0,
        player_name="",
        player_id=0,
        team="",
        x=0,
        y=0,
        z=0,
        x_viz=0,
        y_viz=0,
        area_id=0,
        bomb_site="",
        event_type="",
    ):
        self.tick = tick
        self.sec = sec
        self.player_name = player_name
        self.player_id = player_id
        self.team = team
        self.x = x
        self.y = y
        self.z = z
        self.x = x_viz
        self.y = y_viz
        self.area_id = area_id
        self.bomb_site = bomb_site
        self.event_type = event_type


class Footstep:
    """ Detail a Footstep event

    Attributes:
        tick (int)                : Game tick at time of step
        sec (float)               : Seconds since round start
        player_name (string)      : Player's username
        player_id (int)           : Player's steam id
        team (string)             : Player's team/clan name
        side (string)             : Player's side (T or CT)
        x (float)                 : Player's X position
        y (float)                 : Player's Y position
        z (float)                 : Player's Z position
        x_viz (float)             : Player's X position for visualization
        y_viz (float)             : Player's Y position for visualization
        view_x (float)            : Player's view X direction
        view_y (float)            : Player's view Y direction
        area_id (int)             : Player's location as nav file area id
        area_name (string)        : Player's location as area name from nav file
        distance_bombsite_a (int) : Player's graph distance from bombsite A
        distance_bombsite_b (int) : Player's graph distance from bombsite B
    """

    def __init__(
        self,
        tick=0,
        sec=0,
        player_name="",
        player_id=0,
        team="",
        side="",
        x=0,
        y=0,
        z=0,
        x_viz=0,
        y_viz=0,
        view_x=0,
        view_y=0,
        area_id=0,
        area_name="",
        distance_bombsite_a=999,
        distance_bombsite_b=999,
    ):
        self.tick = tick
        self.sec = sec
        self.player_name = player_name
        self.player_id = player_id
        self.team = team
        self.side = side
        self.x = x
        self.y = y
        self.z = z
        self.x_viz = x_viz
        self.y_viz = y_viz
        self.view_x = view_x
        self.view_y = view_y
        self.area_id = area_id
        self.area_name = area_name
        self.distance_bombsite_a = distance_bombsite_a
        self.distance_bombsite_b = distance_bombsite_b


class Round:
    """ Detail a CSGO round

    Attributes:
        map_name (string)          : Round's map
        start_tick (int)           : Tick on ROUND START event
        end_tick (int)             : Tick on ROUND END event
        end_ct_score (int)         : Ending CT score
        end_t_score (int)          : Ending T score
        start_t_score (int)        : Starting T score
        start_ct_score (int)       : Starting CT score
        round_winner_side (string) : T/CT for round winner
        round_winner (string)      : Winning team name
        round_loser (string)       : Losing team name
        reason (int)               : Corresponds to how the team won (defuse, killed other team, etc.)
        ct_cash_spent_total (int)  : CT total cash spent by this point of the game
        ct_cash_spent_round (int)  : CT total cash spent in current round
        ct_eq_val (int)            : CT equipment value at end of freezetime
        t_cash_spent_total (int)   : T total cash spent by this point of the game
        t_cash_spent_round (int)   : T total cash spent in current round
        t_eq_val (int)             : T equipment value at end of freezetime
        ct_round_type (string)     : CT round buy type
        t_round_type (string)      : T round buy type
        bomb_plant_tick            : Bomb plant tick
        bomb_events (list)         : List of BombEvent objects
        damages (list)             : List of Damage objects
        kills (list)               : List of Kill objects
        footstep (list)            : List of Footstep objects
        grenades (list)            : List of Grenade objects
    """

    def __init__(
        self,
        map_name="",
        start_tick=0,
        end_tick=0,
        end_ct_score=0,
        end_t_score=0,
        start_ct_score=0,
        start_t_score=0,
        round_winner_side="",
        round_winner="",
        round_loser="",
        reason=0,
        ct_cash_spent_total=0,
        ct_cash_spent_round=0,
        ct_eq_val=0,
        t_cash_spent_total=0,
        t_cash_spent_round=0,
        t_eq_val=0,
        ct_round_type="",
        t_round_type="",
        bomb_plant_tick=0,
        players=[],
        kills=[],
        damages=[],
        footsteps=[],
        bomb_events=[],
        grenades=[],
    ):
        self.map_name = map_name
        self.start_tick = start_tick
        self.end_tick = end_tick
        self.end_ct_score = end_ct_score
        self.end_t_score = end_t_score
        self.start_ct_score = start_ct_score
        self.start_t_score = start_t_score
        self.round_winner_side = round_winner_side
        self.round_winner = round_winner
        self.round_loser = round_loser
        self.reason = reason
        self.players = players
        self.kills = kills
        self.damages = damages
        self.footsteps = footsteps
        self.bomb_events = bomb_events
        self.grenades = grenades
        self.ct_cash_spent_total = ct_cash_spent_total
        self.ct_cash_spent_round = ct_cash_spent_round
        self.ct_eq_val = ct_eq_val
        self.t_cash_spent_total = t_cash_spent_total
        self.t_cash_spent_round = t_cash_spent_round
        self.t_eq_val = t_eq_val
        self.ct_round_type = ct_round_type
        self.t_round_type = t_round_type
        self.bomb_plant_tick = bomb_plant_tick
        if self.round_winner_side == "CT":
            self.start_ct_score = self.end_ct_score - 1
            self.start_t_score = self.start_t_score
        if self.round_winner_side == "T":
            self.start_ct_score = self.end_ct_score
            self.start_t_score = self.start_t_score - 1


class Kill:
    """ Detail a kill event

    Attributes:
        tick (int)                : Game tick at time of kill
        sec (float)               : Seconds since round start
        victim_x (float)          : Victim's X position
        victim_y (float)          : Victim's Y position
        victim_z (float)          : Victim's Z position
        victim_x_viz (float)      : Victim's X position for visualization
        victim_y_viz (float)      : Victim's Y position for visualization
        victim_view_x (float)     : Victim's X view
        victim_view_y (float)     : Victim's Y view
        victim_area_id (int)      : Victim's area id from nav file
        victim_area_name (int)    : Victim's area name from nav file
        attacker_x (float)        : Attacker's X position
        attacker_y (float)        : Attacker's Y position
        attacker_z (float)        : Attacker's Z position
        attacker_x_viz (float)    : Attacker's X position for visualization
        attacker_y_viz (float)    : Attacker's Y position for visualization
        attacker_view_x (float)   : Attacker's X view
        attacker_view_y (float)   : Attacker's Y view
        attacker_area_id (int)    : Attacker's area id from nav file
        attacker_area_name (int)  : Attacker's area name from nav file
        assister_x (float)        : Assister's X position
        assister_y (float)        : Assister's Y position
        assister_z (float)        : Assister's Z position
        assister_x_viz (float)    : Assister's X position for visualization
        assister_y_viz (float)    : Assister's Y position for visualization
        assister_view_x (float)   : Assister's X view
        assister_view_y (float)   : Assister's Y view
        assister_area_id (int)    : Assister's area id from nav file
        assister_area_name (int)  : Assister's area name from nav file
        victim_id (int)           : Victim's steam id
        victim_name (string)      : Victim's username
        victim_team (string)      : Victim's team/clan name
        victim_side (string)      : Victim's side (T or CT)
        victim_team_eq_val (int)  : Victim team's starting equipment value
        attacker_id (int)         : Attacker's steam id
        attacker_name (int)       : Attacker's username
        attacker_team (string)    : Attacker's team/clan name
        attacker_side (string)    : Attacker's side (T or CT)
        attacker_team_eq_val (int): Attacker team's starting equipment value
        assister_id (int)         : Assister's steam id
        assister_name (int)       : Assister's username
        assister_team (string)    : Assister's team/clan name
        assister_side (string)    : Assister's side (T or CT)
        weapon_id (int)           : Weapon id
        is_wallshot (boolean)     : If kill was a wallshot then 1, 0 otherwise
        is_flashed (boolean)      : If kill victim was flashed then 1, 0 otherwise
        is_headshot (boolean)     : If kill was a headshot then 1, 0 otherwise
    """

    def __init__(
        self,
        tick=0,
        sec=0,
        victim_x=0,
        victim_y=0,
        victim_z=0,
        victim_x_viz=0,
        victim_y_viz=0,
        victim_view_x=0,
        victim_view_y=0,
        victim_area_id=0,
        victim_area_name="",
        attacker_x=0,
        attacker_y=0,
        attacker_z=0,
        attacker_x_viz=0,
        attacker_y_viz=0,
        attacker_view_x=0,
        attacker_view_y=0,
        attacker_area_id=0,
        attacker_area_name="",
        assister_x=0,
        assister_y=0,
        assister_z=0,
        assister_x_viz=0,
        assister_y_viz=0,
        assister_view_x=0,
        assister_view_y=0,
        assister_area_id=0,
        assister_area_name="",
        victim_id=0,
        victim_name="",
        victim_team="",
        victim_side="",
        victim_team_eq_val=0,
        attacker_id=0,
        attacker_name="",
        attacker_team="",
        attacker_side="",
        attacker_team_eq_val=0,
        assister_id=0,
        assister_name="",
        assister_team="",
        assister_side="",
        weapon_id=0,
        is_wallshot=False,
        is_flashed=False,
        is_headshot=False,
    ):
        self.tick = tick
        self.sec = sec
        self.attacker_id = attacker_id
        self.attacker_name = attacker_name
        self.attacker_team = attacker_team
        self.attacker_side = attacker_side
        self.attacker_team_eq_val = attacker_team_eq_val
        self.attacker_x = attacker_x
        self.attacker_y = attacker_y
        self.attacker_z = attacker_z
        self.attacker_x_viz = attacker_x_viz
        self.attacker_y_viz = attacker_y_viz
        self.attacker_view_x = attacker_view_x
        self.attacker_view_y = attacker_view_y
        self.attacker_area_id = attacker_area_id
        self.attacker_area_name = attacker_area_name
        self.victim_id = victim_id
        self.victim_name = victim_name
        self.victim_side = victim_side
        self.victim_team_eq_val = victim_team_eq_val
        self.victim_x = victim_x
        self.victim_y = victim_y
        self.victim_z = victim_z
        self.victim_x_viz = victim_x_viz
        self.victim_y_viz = victim_y_viz
        self.victim_view_x = victim_view_x
        self.victim_view_y = victim_view_y
        self.victim_area_id = victim_area_id
        self.victim_area_name = victim_area_name
        self.assister_id = assister_id
        self.assister_name = assister_name
        self.assister_team = assister_team
        self.assister_side = assister_side
        self.assister_x = assister_x
        self.assister_y = assister_y
        self.assister_z = assister_z
        self.assister_x_viz = assister_x_viz
        self.assister_y_viz = assister_y_viz
        self.assister_view_x = assister_view_x
        self.assister_view_y = assister_view_y
        self.assister_area_id = assister_area_id
        self.assister_area_name = assister_area_name
        self.weapon_id = weapon_id
        self.is_wallshot = is_wallshot
        self.is_flashed = is_flashed
        self.is_headshot = is_headshot


class Damage:
    """ Detail a damage event

    Attributes:
        tick (int)                : Game tick at time of kill
        sec (float)               : Seconds since round start
        victim_x (float)          : Victim's X position
        victim_y (float)          : Victim's Y position
        victim_z (float)          : Victim's Z position
        victim_x_viz (float)      : Victim's X position for visualization
        victim_y_viz (float)      : Victim's Y position for visualization
        victim_view_x (float)     : Victim's X view
        victim_view_y (float)     : Victim's Y view
        victim_area_id (int)      : Victim's area id from nav file
        victim_area_name (int)    : Victim's area name from nav file
        attacker_x (float)        : Attacker's X position
        attacker_y (float)        : Attacker's Y position
        attacker_z (float)        : Attacker's Z position
        attacker_x_viz (float)    : Attacker's X position for visualization
        attacker_y_viz (float)    : Attacker's Y position for visualization
        attacker_view_x (float)   : Attacker's X view
        attacker_view_y (float)   : Attacker's Y view
        attacker_area_id (int)    : Attacker's area id from nav file
        attacker_area_name (int)  : Attacker's area name from nav file
        victim_id (int)           : Victim's steam id
        victim_name (string)      : Victim's username
        victim_team (string)      : Victim's team/clan name
        victim_side (string)      : Victim's side (T or CT)
        victim_team_eq_val (int)  : Victim team's starting equipment value
        attacker_id (int)         : Attacker's steam id
        attacker_name (int)       : Attacker's username
        attacker_team (string)    : Attacker's team/clan name
        attacker_side (string)    : Attacker's side (T or CT)
        attacker_team_eq_val (int): Attacker team's starting equipment value
        hp_damage (int)           : HP damage dealt
        kill_hp_damage (int)      : HP damage dealt normalized to 100.
        armor_damage (int)        : Armor damage dealt
        weapon_id (int)           : Weapon id
        hit_group (int)           : Hit group
    """

    def __init__(
        self,
        tick=0,
        sec=0,
        victim_x=0,
        victim_y=0,
        victim_z=0,
        victim_x_viz=0,
        victim_y_viz=0,
        victim_view_x=0,
        victim_view_y=0,
        victim_area_id=0,
        victim_area_name="",
        attacker_x=0,
        attacker_y=0,
        attacker_z=0,
        attacker_x_viz=0,
        attacker_y_viz=0,
        attacker_view_x=0,
        attacker_view_y=0,
        attacker_area_id=0,
        attacker_area_name="",
        victim_id=0,
        victim_name="",
        victim_team="",
        victim_side="",
        victim_team_eq_val=0,
        attacker_id=0,
        attacker_name="",
        attacker_team="",
        attacker_side="",
        attacker_team_eq_val=0,
        hp_damage=0,
        kill_hp_damage=0,
        armor_damage=0,
        weapon_id=0,
        hit_group=0,
    ):
        self.tick = tick
        self.sec = sec
        self.victim_x = victim_x
        self.victim_y = victim_y
        self.victim_z = victim_z
        self.victim_x_viz = victim_x_viz
        self.victim_y_viz = victim_y_viz
        self.victim_view_x = victim_view_x
        self.victim_view_y = victim_view_y
        self.victim_area_id = victim_area_id
        self.victim_area_name = victim_area_name
        self.attacker_x = attacker_x
        self.attacker_y = attacker_y
        self.attacker_z = attacker_z
        self.attacker_x_viz = attacker_x_viz
        self.attacker_y_viz = attacker_y_viz
        self.attacker_view_x = attacker_view_x
        self.attacker_view_y = attacker_view_y
        self.attacker_area_id = attacker_area_id
        self.attacker_area_name = attacker_area_name
        self.victim_id = victim_id
        self.victim_name = victim_name
        self.victim_team = victim_team
        self.victim_side = victim_side
        self.victim_team_eq_val = victim_team_eq_val
        self.attacker_id = attacker_id
        self.attacker_name = attacker_name
        self.attacker_team = attacker_team
        self.attacker_side = attacker_side
        self.attacker_team_eq_val = attacker_team_eq_val
        self.hp_damage = hp_damage
        self.kill_hp_damage = kill_hp_damage
        self.armor_damage = armor_damage
        self.weapon_id = weapon_id
        self.hit_group = hit_group
