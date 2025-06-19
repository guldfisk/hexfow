from enum import StrEnum, auto

from dns.enum import IntEnum


class Size(IntEnum):
    SMALL = 0
    MEDIUM = 1
    LARGE = 2


class DamageType(StrEnum):
    MELEE = auto()
    RANGED = auto()
    AOE = auto()
    PHYSICAL = auto()
    PURE = auto()


class Resistance(IntEnum):
    NONE = auto()
    MINOR = auto()
    NORMAL = auto()
    MAJOR = auto()
    IMMUNE = auto()


class VisionObstruction(IntEnum):
    NONE = auto()
    HIGH_GROUND = auto()
    FULL = auto()


class StatusIntention(StrEnum):
    BUFF = auto()
    DEBUFF = auto()
    NEUTRAL = auto()
