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
    TRUE = auto()
