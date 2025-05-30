from game.game.core import MeleeAttackFacet, RangedAttackFacet, Unit
from game.game.values import Size


class Peck(MeleeAttackFacet):
    movement_cost = 0
    damage = 1


# TODO combineable
class BuglingClaw(MeleeAttackFacet):
    combineable = True
    movement_cost = 0
    damage = 2


class GiantClub(MeleeAttackFacet):
    movement_cost = 0
    damage = 5


class MarshmallowFist(MeleeAttackFacet):
    movement_cost = 0
    damage = 2


class LightBow(RangedAttackFacet):
    movement_cost = 1
    range = 3
    damage = 1
    ap = 1


# ap rifle squad {6r} x2
# health 5, movement 2, sight 2, M
# ap rifle
#     ranged attack
#     3 damage, 3 range
#     1 ap
#     +1 damage against large
#     -1 damage against air
#     no movement


class APGun(RangedAttackFacet):
    # TODO should be "no movement"
    movement_cost = 2
    range = 3
    # damage = 3
    ap = 1

    def get_damage_against(self, unit: Unit) -> int:
        return 4 if unit.size.g() > Size.MEDIUM else 3


class HurlBoulder(RangedAttackFacet):
    # TODO should be "no movement"
    movement_cost = 3
    range = 2
    #     +1 damage on rock terrain
    damage = 5
