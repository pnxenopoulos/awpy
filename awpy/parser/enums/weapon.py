from enum import Enum


class Weapon(Enum):
    """Weapon as defined by demoparser2"""

    ACTIVE_WEAPON_NAME = "active_weapon_name"  # m_iItemDefinitionIndex + lookup
    ACTIVE_WEAPON_SKIN = "active_weapon_skin"  # m_iRawValue32 + lookup
    ACTIVE_WEAPON_AMMO = "active_weapon_ammo"  # m_iClip1
    ACTIVE_WEAPON_ORIGINAL_OWNER = "active_weapon_original_owner"  # m_OriginalOwnerXuidLow + m_OriginalOwnerXuidHigh
    TOTAL_AMMO_LEFT = "total_ammo_left"  # m_pReserveAmmo
    ITEM_DEF_IDX = "item_def_idx"  # m_iItemDefinitionIndex
    WEAPON_QUALITY = "weapon_quality"  # m_iEntityQuality
    ENTITY_LVL = "entity_lvl"  # m_iEntityLevel
    ITEM_ID_HIGH = "item_id_high"  # m_iItemIDHigh
    ITEM_ID_LOW = "item_id_low"  # m_iItemIDLow
    ITEM_ACCOUNT_ID = "item_account_id"  # m_iAccountID
    INVENTORY_POSITION = "inventory_position"  # m_iInventoryPosition
    IS_INITIALIZED = "is_initialized"  # m_bInitialized
    ECON_ITEM_ATTRIBUTE_DEF_IDX = (
        "econ_item_attribute_def_idx"  # m_iAttributeDefinitionIndex
    )
    INITIAL_VALUE = "initial_value"  # m_flInitialValue
    REFUNDABLE_CURRENCY = "refundable_currency"  # m_nRefundableCurrency
    SET_BONUS = "set_bonus"  # m_bSetBonus
    CUSTOM_NAME = "custom_name"  # m_szCustomName
    ORIG_OWNER_XUID_LOW = "orig_owner_xuid_low"  # m_OriginalOwnerXuidLow
    ORIG_OWNER_XUID_HIGH = "orig_owner_xuid_high"  # m_OriginalOwnerXuidHigh
    FALL_BACK_PAINT_KIT = "fall_back_paint_kit"  # m_nFallbackPaintKit
    FALL_BACK_SEED = "fall_back_seed"  # m_nFallbackSeed
    FALL_BACK_WEAR = "fall_back_wear"  # m_flFallbackWear
    FALL_BACK_STAT_TRACK = "fall_back_stat_track"  # m_nFallbackStatTrak
    M_I_STATE = "m_iState"  # m_iState
    FIRE_SEQ_START_TIME = "fire_seq_start_time"  # m_flFireSequenceStartTime
    FIRE_SEQ_START_TIME_CHANGE = (
        "fire_seq_start_time_change"  # m_nFireSequenceStartTimeChange
    )
    IS_PLAYER_FIRE_EVENT_PRIMARY = (
        "is_player_fire_event_primary"  # m_bPlayerFireEventIsPrimary
    )
    WEAPON_MODE = "weapon_mode"  # m_weaponMode
    ACCURACY_PENALTY = "accuracy_penalty"  # m_fAccuracyPenalty
    I_RECOIL_IDX = "i_recoil_idx"  # m_iRecoilIndex
    FL_RECOIL_IDX = "fl_recoil_idx"  # m_flRecoilIndex
    IS_BURST_MODE = "is_burst_mode"  # m_bBurstMode
    POST_PONE_FIRE_READY_TIME = "post_pone_fire_ready_time"  # m_flPostponeFireReadyTime
    IS_IN_RELOAD = "is_in_reload"  # m_bInReload
    RELOAD_VISUALLY_COMPLETE = "reload_visually_complete"  # m_bReloadVisuallyComplete
    DROPPED_AT_TIME = "dropped_at_time"  # m_flDroppedAtTime
    IS_HAULED_BACK = "is_hauled_back"  # m_bIsHauledBack
    IS_SILENCER_ON = "is_silencer_on"  # m_bSilencerOn
    TIME_SILENCER_SWITCH_COMPLETE = (
        "time_silencer_switch_complete"  # m_flTimeSilencerSwitchComplete
    )
    ORIG_TEAM_NUMBER = "orig_team_number"  # m_iOriginalTeamNumber
    PREV_OWNER = "prev_owner"  # m_hPrevOwner
    LAST_SHOT_TIME = "last_shot_time"  # m_fLastShotTime
    IRON_SIGHT_MODE = "iron_sight_mode"  # m_iIronSightMode
    NUM_EMPTY_ATTACKS = "num_empty_attacks"  # m_iNumEmptyAttacks
    ZOOM_LVL = "zoom_lvl"  # m_zoomLevel
    BURST_SHOTS_REMAINING = "burst_shots_remaining"  # m_iBurstShotsRemaining
    NEEDS_BOLT_ACTION = "needs_bolt_action"  # m_bNeedsBoltAction
    NEXT_PRIMARY_ATTACK_TICK = "next_primary_attack_tick"  # m_nNextPrimaryAttackTick
    NEXT_PRIMARY_ATTACK_TICK_RATIO = (
        "next_primary_attack_tick_ratio"  # m_flNextPrimaryAttackTickRatio
    )
    NEXT_SECONDARY_ATTACK_TICK = (
        "next_secondary_attack_tick"  # m_nNextSecondaryAttackTick
    )
    NEXT_SECONDARY_ATTACK_TICK_RATIO = (
        "next_secondary_attack_tick_ratio"  # m_flNextSecondaryAttackTickRatio
    )
