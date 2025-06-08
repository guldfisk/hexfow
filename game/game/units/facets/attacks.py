import dataclasses
from typing import ClassVar

from events.eventsystem import TriggerEffect, ES
from game.game.core import MeleeAttackFacet, RangedAttackFacet, Unit
from game.game.events import MeleeAttackAction, SimpleAttack, Damage, ApplyStatus
from game.game.statuses import Parasite, Staggered
from game.game.units.facets.hooks import AdjacencyHook
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


class SerratedBeak(MeleeAttackFacet):
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


# horror {12wp} x1
# health 7, movement 4, sight 2, energy 4, M
# inject
#     melee attack
#     4 damage, -1 movement
#     applies horror parasite to damaged target
#         unstackable
#         when this unit dies, summon exhausted horror spawn under debuff controllers control on this hex. if hex is occupied by just followed up attacker, instead spawns on hex attacker attacked from.
# venomous spine
#     ability 3 energy
#     target enemy unit 2 range LoS, -1 movement
#     applies horror parasite and (debilitating venom for 2 rounds) to target.
#         unstackable, refreshable
#         +1 move penalty
#         -1 attack power


@dataclasses.dataclass(eq=False)
class InjectTrigger(TriggerEffect[SimpleAttack]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: SimpleAttack) -> bool:
        return event.attacker == self.unit and any(
            e.unit == event.defender for e in event.iter_type(Damage)
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        ES.resolve(
            ApplyStatus(
                unit=event.defender,
                status_type=Parasite,
                by=self.unit.controller,
            )
        )


class Inject(MeleeAttackFacet):
    movement_cost = 1
    damage = 4

    def create_effects(self) -> None:
        self.register_effects(InjectTrigger(self.owner))


class RoundhouseKick(MeleeAttackFacet):
    damage = 3

    def get_damage_against(self, unit: Unit) -> int:
        return (
            4 if any(isinstance(status, Staggered) for status in unit.statuses) else 3
        )
