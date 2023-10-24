from enum import Enum


class GameState(Enum):
    """GameState as defined by demoparser2"""

    TEAM_ROUNDS_TOTAL = "team_rounds_total"  # m_iScore
    TEAM_SURRENDERED = "team_surrendered"  # m_bSurrendered
    TEAM_NAME = "team_name"  # m_szTeamname
    TEAM_SCORE_OVERTIME = "team_score_overtime"  # m_scoreOvertime
    TEAM_MATCH_STAT = "team_match_stat"  # m_szTeamMatchStat
    TEAM_NUM_MAP_VICTORIES = "team_num_map_victories"  # m_numMapVictories
    TEAM_SCORE_FIRST_HALF = "team_score_first_half"  # m_scoreFirstHalf
    TEAM_SCORE_SECOND_HALF = "team_score_second_half"  # m_scoreSecondHalf
    TEAM_CLAN_NAME = "team_clan_name"  # m_szClanTeamname
    IS_FREEZE_PERIOD = "is_freeze_period"  # m_bFreezePeriod
    IS_WARMUP_PERIOD = "is_warmup_period"  # m_bWarmupPeriod
    WARMUP_PERIOD_END = "warmup_period_end"  # m_fWarmupPeriodEnd
    WARMUP_PERIOD_START = "warmup_period_start"  # m_fWarmupPeriodStart
    IS_TERRORIST_TIMEOUT = "is_terrorist_timeout"  # m_bTerroristTimeOutActive
    IS_CT_TIMEOUT = "is_ct_timeout"  # m_bCTTimeOutActive
    TERRORIST_TIMEOUT_REMAINING = (
        "terrorist_timeout_remaining"  # m_flTerroristTimeOutRemaining
    )
    CT_TIMEOUT_REMAINING = "ct_timeout_remaining"  # m_flCTTimeOutRemaining
    NUM_TERRORIST_TIMEOUTS = "num_terrorist_timeouts"  # m_nTerroristTimeOuts
    NUM_CT_TIMEOUTS = "num_ct_timeouts"  # m_nCTTimeOuts
    IS_TECHNICAL_TIMEOUT = "is_technical_timeout"  # m_bTechnicalTimeOut
    IS_WAITING_FOR_RESUME = "is_waiting_for_resume"  # m_bMatchWaitingForResume
    MATCH_START_TIME = "match_start_time"  # m_fMatchStartTime
    ROUND_START_TIME = "round_start_time"  # m_fRoundStartTime
    RESTART_ROUND_TIME = "restart_round_time"  # m_flRestartRoundTime
    IS_GAME_RESTART = "is_game_restart"  # m_bGameRestart
    GAME_START_TIME = "game_start_time"  # m_flGameStartTime
    TIME_UNTIL_NEXT_PHASE_START = (
        "time_until_next_phase_start"  # m_timeUntilNextPhaseStarts
    )
    GAME_PHASE = "game_phase"  # m_gamePhase
    TOTAL_ROUNDS_PLAYED = "total_rounds_played"  # m_totalRoundsPlayed
    ROUNDS_PLAYED_THIS_PHASE = "rounds_played_this_phase"  # m_nRoundsPlayedThisPhase
    HOSTAGES_REMAINING = "hostages_remaining"  # m_iHostagesRemaining
    ANY_HOSTAGES_REACHED = "any_hostages_reached"  # m_bAnyHostageReached
    HAS_BOMBITES = "has_bombites"  # m_bMapHasBombTarget
    HAS_RESCUE_ZONE = "has_rescue_zone"  # m_bMapHasRescueZone
    HAS_BUY_ZONE = "has_buy_zone"  # m_bMapHasBuyZone
    IS_MATCHMAKING = "is_matchmaking"  # m_bIsQueuedMatchmaking
    MATCH_MAKING_MODE = "match_making_mode"  # m_nQueuedMatchmakingMode
    IS_VALVE_DEDICATED_SERVER = "is_valve_dedicated_server"  # m_bIsValveDS
    GUNGAME_PROG_WEAP_CT = "gungame_prog_weap_ct"  # m_iNumGunGameProgressiveWeaponsCT
    GUNGAME_PROG_WEAP_T = "gungame_prog_weap_t"  # m_iNumGunGameProgressiveWeaponsT
    SPECTATOR_SLOT_COUNT = "spectator_slot_count"  # m_iSpectatorSlotCount
    IS_MATCH_STARTED = "is_match_started"  # m_bHasMatchStarted
    N_BEST_OF_MAPS = "n_best_of_maps"  # m_numBestOfMaps
    IS_BOMB_DROPPED = "is_bomb_dropped"  # m_bBombDropped
    IS_BOMB_PLANED = "is_bomb_planed"  # m_bBombPlanted
    ROUND_WIN_STATUS = "round_win_status"  # m_iRoundWinStatus
    ROUND_WIN_REASON = "round_win_reason"  # m_eRoundWinReason
    TERRORIST_CANT_BUY = "terrorist_cant_buy"  # m_bTCantBuy
    CT_CANT_BUY = "ct_cant_buy"  # m_bCTCantBuy
    NUM_PLAYER_ALIVE_CT = "num_player_alive_ct"  # m_iMatchStats_PlayersAlive_CT
    NUM_PLAYER_ALIVE_T = "num_player_alive_t"  # m_iMatchStats_PlayersAlive_T
    CT_LOSING_STREAK = "ct_losing_streak"  # m_iNumConsecutiveCTLoses
    T_LOSING_STREAK = "t_losing_streak"  # m_iNumConsecutiveTerroristLoses
    SURVIVAL_START_TIME = "survival_start_time"  # m_flSurvivalStartTime
    ROUND_IN_PROGRESS = "round_in_progress"  # m_bRoundInProgress
