"""Converters for index-based fields."""

import awpy.constants

# Taken from https://github.com/markus-wa/demoinfocs-golang/blob/master/pkg/demoinfocs/events/events.go#L423
HITGROUP_MAP = {
    0: "generic",
    1: "head",
    2: "chest",
    3: "stomach",
    4: "left arm",
    5: "right arm",
    6: "left leg",
    7: "right leg",
    8: "neck",
    10: "gear",
}

# Taken from https://github.com/markus-wa/demoinfocs-golang/blob/master/pkg/demoinfocs/events/events.go
ROUND_END_REASON_MAP = {
    0: "still in progress",
    1: "target bombed",
    2: "vip escaped",
    3: "vip killed",
    4: "t escaped",
    5: "ct stopped escape",
    6: "t stopped",
    7: "bomb defused",
    8: "t eliminated",
    9: "ct eliminated",
    10: "draw",
    11: "hostages rescued",
    12: "target saved",
    13: "hostages not rescued",
    14: "t not escaped",
    15: "vip not escaped",
    16: "game start",
    17: "t surrender",
    18: "ct surrender",
    19: "t planted",
    20: "ct reached hostage",
}

# Taken from https://github.com/markus-wa/demoinfocs-golang/blob/master/pkg/demoinfocs/common/common.go#L20
TEAM_MAP = {0: "unassigned", 1: "spectator", 2: awpy.constants.T_SIDE, 3: awpy.constants.CT_SIDE}
