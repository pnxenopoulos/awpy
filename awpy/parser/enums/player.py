from enum import Enum


class PlayerData(Enum):
    """PlayerData as defined by demoparser2"""

    X = "X"  # m_vec + m_cell
    Y = "Y"  # m_vec + m_cell
    Z = "Z"  # m_vec + m_cell
    HEALTH = "health"  # m_iHealth
    SCORE = "score"  # m_iScore
    MVPS = "mvps"  # m_iMVPs
    IS_ALIVE = "is_alive"  # m_bPawnIsAlive
    BALANCE = "balance"  # m_iAccount
    INVENTORY = "inventory"  # _
    LIFE_STATE = "life_state"  # m_lifeState
    PITCH = "pitch"  # m_angEyeAngles[0]
    YAW = "yaw"  # m_angEyeAngles[1]
    IS_AUTO_MUTED = "is_auto_muted"  # m_bHasCommunicationAbuseMute
    CROSSHAIR_CODE = "crosshair_code"  # m_szCrosshairCodes
    PENDING_TEAM_NUM = "pending_team_num"  # m_iPendingTeamNum
    PLAYER_COLOR = "player_color"  # m_iCompTeammateColor
    EVER_PLAYED_ON_TEAM = "ever_played_on_team"  # m_bEverPlayedOnTeam
    CLAN_NAME = "clan_name"  # m_szClan
    IS_COACH_TEAM = "is_coach_team"  # m_iCoachingTeam
    RANK = "rank"  # m_iCompetitiveRanking
    RANK_IF_WIN = "rank_if_win"  # m_iCompetitiveRankingPredicted_Win
    RANK_IF_LOSS = "rank_if_loss"  # m_iCompetitiveRankingPredicted_Loss
    RANK_IF_TIE = "rank_if_tie"  # m_iCompetitiveRankingPredicted_Tie
    COMP_WINS = "comp_wins"  # m_iCompetitiveWins
    COMP_RANK_TYPE = "comp_rank_type"  # m_iCompetitiveRankType
    IS_CONTROLLING_BOT = "is_controlling_bot"  # m_bControllingBot
    HAS_CONTROLLED_BOT_THIS_ROUND = (
        "has_controlled_bot_this_round"  # m_bHasControlledBotThisRound
    )
    CAN_CONTROL_BOT = "can_control_bot"  # m_bCanControlObservedBot
    ARMOR = "armor"  # m_iPawnArmor
    HAS_DEFUSER = "has_defuser"  # m_bPawnHasDefuser
    HAS_HELMET = "has_helmet"  # m_bPawnHasHelmet
    SPAWN_TIME = "spawn_time"  # m_iPawnLifetimeStart
    DEATH_TIME = "death_time"  # m_iPawnLifetimeEnd
    GAME_TIME = "game_time"  # net_tick
    IS_CONNECTED = "is_connected"  # m_iConnected
    PLAYER_NAME = "player_name"  # m_iszPlayerName
    PLAYER_STEAMID = "player_steamid"  # m_steamID
    FOV = "fov"  # m_iDesiredFOV
    START_BALANCE = "start_balance"  # m_iStartAccount
    TOTAL_CASH_SPENT = "total_cash_spent"  # m_iTotalCashSpent
    CASH_SPENT_THIS_ROUND = "cash_spent_this_round"  # m_iCashSpentThisRound
    MUSIC_KIT_ID = "music_kit_id"  # m_unMusicID
    LEADER_HONORS = "leader_honors"  # m_nPersonaDataPublicCommendsLeader
    TEACHER_HONORS = "teacher_honors"  # m_nPersonaDataPublicCommendsTeacher
    FRIENDLY_HONORS = "friendly_honors"  # m_nPersonaDataPublicCommendsFriendly
    PING = "ping"  # m_iPing
    MOVE_COLLIDE = "move_collide"  # m_MoveCollide
    MOVE_TYPE = "move_type"  # m_MoveType
    TEAM_NUM = "team_num"  # m_iTeamNum
    ACTIVE_WEAPON = "active_weapon"  # m_hActiveWeapon
    LOOKING_AT_WEAPON = "looking_at_weapon"  # m_bIsLookingAtWeapon
    HOLDING_LOOK_AT_WEAPON = "holding_look_at_weapon"  # m_bIsHoldingLookAtWeapon
    NEXT_ATTACK_TIME = "next_attack_time"  # m_flNextAttack
    DUCK_TIME_MS = "duck_time_ms"  # m_nDuckTimeMsecs
    MAX_SPEED = "max_speed"  # m_flMaxspeed
    MAX_FALL_VELO = "max_fall_velo"  # m_flMaxFallVelocity
    DUCK_AMOUNT = "duck_amount"  # m_flDuckAmount
    DUCK_SPEED = "duck_speed"  # m_flDuckSpeed
    DUCK_OVERRDIE = "duck_overrdie"  # m_bDuckOverride
    OLD_JUMP_PRESSED = "old_jump_pressed"  # m_bOldJumpPressed
    JUMP_UNTIL = "jump_until"  # m_flJumpUntil
    JUMP_VELO = "jump_velo"  # m_flJumpVel
    FALL_VELO = "fall_velo"  # m_flFallVelocity
    IN_CROUCH = "in_crouch"  # m_bInCrouch
    CROUCH_STATE = "crouch_state"  # m_nCrouchState
    DUCKED = "ducked"  # m_bDucked
    DUCKING = "ducking"  # m_bDucking
    IN_DUCK_JUMP = "in_duck_jump"  # m_bInDuckJump
    ALLOW_AUTO_MOVEMENT = "allow_auto_movement"  # m_bAllowAutoMovement
    JUMP_TIME_MS = "jump_time_ms"  # m_nJumpTimeMsecs
    LAST_DUCK_TIME = "last_duck_time"  # m_flLastDuckTime
    IS_RESCUING = "is_rescuing"  # m_bIsRescuing
    WEAPON_PURCHASES_THIS_MATCH = (
        "weapon_purchases_this_match"  # m_iWeaponPurchasesThisMatch
    )
    WEAPON_PURCHASES_THIS_ROUND = (
        "weapon_purchases_this_round"  # m_iWeaponPurchasesThisRound
    )
    SPOTTED = "spotted"  # m_bSpotted
    APPROXIMATE_SPOTTED_BY = "approximate_spotted_by"  # m_bSpottedByMask
    TIME_LAST_INJURY = "time_last_injury"  # m_flTimeOfLastInjury
    DIRECTION_LAST_INJURY = "direction_last_injury"  # m_nRelativeDirectionOfLastInjury
    PLAYER_STATE = "player_state"  # m_iPlayerState
    PASSIVE_ITEMS = "passive_items"  # m_passiveItems
    IS_SCOPED = "is_scoped"  # m_bIsScoped
    IS_WALKING = "is_walking"  # m_bIsWalking
    RESUME_ZOOM = "resume_zoom"  # m_bResumeZoom
    IS_DEFUSING = "is_defusing"  # m_bIsDefusing
    IS_GRABBING_HOSTAGE = "is_grabbing_hostage"  # m_bIsGrabbingHostage
    BLOCKING_USE_IN_PROGESS = (
        "blocking_use_in_progess"  # m_iBlockingUseActionInProgress
    )
    MOLOTOV_DAMAGE_TIME = "molotov_damage_time"  # m_fMolotovDamageTime
    MOVED_SINCE_SPAWN = "moved_since_spawn"  # m_bHasMovedSinceSpawn
    IN_BOMB_ZONE = "in_bomb_zone"  # m_bInBombZone
    IN_BUY_ZONE = "in_buy_zone"  # m_bInBuyZone
    IN_NO_DEFUSE_AREA = "in_no_defuse_area"  # m_bInNoDefuseArea
    KILLED_BY_TASER = "killed_by_taser"  # m_bKilledByTaser
    MOVE_STATE = "move_state"  # m_iMoveState
    WHICH_BOMB_ZONE = "which_bomb_zone"  # m_nWhichBombZone
    IN_HOSTAGE_RESCUE_ZONE = "in_hostage_rescue_zone"  # m_bInHostageRescueZone
    STAMINA = "stamina"  # m_flStamina
    DIRECTION = "direction"  # m_iDirection
    SHOTS_FIRED = "shots_fired"  # m_iShotsFired
    ARMOR_VALUE = "armor_value"  # m_ArmorValue
    VELO_MODIFIER = "velo_modifier"  # m_flVelocityModifier
    GROUND_ACCEL_LINEAR_FRAC_LAST_TIME = (
        "ground_accel_linear_frac_last_time"  # m_flGroundAccelLinearFracLastTime
    )
    FLASH_DURATION = "flash_duration"  # m_flFlashDuration
    FLASH_MAX_ALPHA = "flash_max_alpha"  # m_flFlashMaxAlpha
    WAIT_FOR_NO_ATTACK = "wait_for_no_attack"  # m_bWaitForNoAttack
    LAST_PLACE_NAME = "last_place_name"  # m_szLastPlaceName
    IS_STRAFING = "is_strafing"  # m_bStrafing
    ROUND_START_EQUIP_VALUE = "round_start_equip_value"  # m_unRoundStartEquipmentValue
    CURRENT_EQUIP_VALUE = "current_equip_value"  # m_unCurrentEquipmentValue
    TIME = "time"  # m_flSimulationTime
