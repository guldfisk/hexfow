import dataclasses

from events.eventsystem import HookEffect, Event
from game.game.core import MeleeAttackFacet, RangedAttackFacet, Unit, GS
from game.game.events import TurnUpkeep
from game.game.values import Size


class Peck(MeleeAttackFacet):
    movement_cost = 0
    damage = 1


class BuglingClaw(MeleeAttackFacet):
    combinable = True
    movement_cost = 0
    damage = 2


class GiantClub(MeleeAttackFacet):
    movement_cost = 0
    damage = 5


@dataclasses.dataclass(eq=False)
class AdjacencyHook(HookEffect[TurnUpkeep]):
    unit: Unit
    adjacent_units: list[Unit] = dataclasses.field(default_factory=list)

    def resolve_hook_call(self, event: Event):
        self.adjacent_units = list(GS().map.get_neighboring_units_off(self.unit))


class Gore(MeleeAttackFacet):
    movement_cost = 0
    damage = 4

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.owner)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def get_damage_against(self, unit: Unit) -> int:
        return 4 if unit in self.adjacency_hook.adjacent_units else 6


class MarshmallowFist(MeleeAttackFacet):
    damage = 2


class GnomeSpear(MeleeAttackFacet):
    damage = 2


class RazorTusk(MeleeAttackFacet):
    damage = 3


class Blaster(RangedAttackFacet):
    damage = 3
    range = 2
    movement_cost = 1


class LightBlaster(RangedAttackFacet):
    damage = 2
    range = 3


class Strafe(RangedAttackFacet):
    damage = 2
    range = 2
    movement_cost = 1
    combinable = True


class Bayonet(MeleeAttackFacet):
    damage = 3


class Pinch(MeleeAttackFacet):
    damage = 2
    movement_cost = 1


class Chainsaw(MeleeAttackFacet):
    movement_cost = 1
    damage = 3

    def get_damage_against(self, unit: Unit) -> int:
        return 3 if unit.armor.g() > 0 else 5


class LightBow(RangedAttackFacet):
    # TODO in notes or how should this be done?
    movement_cost = 0
    range = 3
    damage = 1


class APGun(RangedAttackFacet):
    # TODO should be "no movement"
    movement_cost = 2
    range = 3
    ap = 1

    def get_damage_against(self, unit: Unit) -> int:
        return 4 if unit.size.g() > Size.MEDIUM else 3


class HurlBoulder(RangedAttackFacet):
    # TODO should be "no movement"
    movement_cost = 3
    range = 2
    #     +1 damage on rock terrain
    damage = 5


class HiddenBlade(MeleeAttackFacet):
    movement_cost = 0
    damage = 1

    def get_damage_against(self, unit: Unit) -> int:
        return 2 if unit.exhausted else 1


class Bite(MeleeAttackFacet):
    movement_cost = 0
    damage = 3
