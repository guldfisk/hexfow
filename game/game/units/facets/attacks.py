from typing import ClassVar

from game.game.units.unit import AttackFacet


class MeleeAttackFacet(AttackFacet):
    damage: ClassVar[int]


class Peck(MeleeAttackFacet):
    damage = 1
