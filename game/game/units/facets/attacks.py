from game.game.core import MeleeAttackFacet, RangedAttackFacet


class Peck(MeleeAttackFacet):
    movement_cost = 0
    damage = 1


class MarshmallowFist(MeleeAttackFacet):
    movement_cost = 0
    damage = 2


class LightBow(RangedAttackFacet):
    movement_cost = 1
    range = 3
    damage = 1
