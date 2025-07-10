from events.eventsystem import ES
from game.core import (
    MeleeAttackFacet,
    RangedAttackFacet,
    Unit,
    StatusSignature,
    MovementCost,
    ExclusiveCost,
    DamageSignature,
    UnitStatus,
)
from game.effects.hooks import AdjacencyHook
from game.events import Damage, ApplyStatus
from game.statuses.unit_statuses import Staggered, Stumbling, BellStruck
from game.values import Size, DamageType, StatusIntention


class Peck(MeleeAttackFacet):
    damage = 1


class BuglingClaw(MeleeAttackFacet):
    combinable = True
    damage = 2


class GiantClub(MeleeAttackFacet):
    damage = 5


class Gore(MeleeAttackFacet):
    """
    +2 damage against units this unit wasn't adjacent to at the beginning of its turn.
    """

    damage = 4

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.owner)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def get_damage_modifier_against(self, unit: Unit) -> int:
        if not unit in self.adjacency_hook.adjacent_units:
            return 2


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
    cost = MovementCost(1)


class BloodExpunge(RangedAttackFacet):
    """+1 damage for each unique debuff the target has."""

    damage = 2
    range = 3
    cost = MovementCost(2)

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        return len(
            [
                status
                for status in unit.statuses
                if status.intention == StatusIntention.DEBUFF
            ]
        )


class SolidMunition(RangedAttackFacet):
    """Stuns this unit."""

    damage = 4
    range = 4
    cost = ExclusiveCost()

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                self.owner, StatusSignature(UnitStatus.get("stunned"), self, stacks=1)
            )
        )


class HammerBlow(MeleeAttackFacet):
    damage = 4


class MightyBlow(MeleeAttackFacet):
    """Stuns this unit."""

    cost = ExclusiveCost()
    damage = 6

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                self.owner, StatusSignature(UnitStatus.get("stunned"), self, stacks=1)
            )
        )


class LightBlaster(RangedAttackFacet):
    damage = 2
    range = 3


class Strafe(RangedAttackFacet):
    damage = 2
    range = 2
    cost = MovementCost(1)
    combinable = True


class Bayonet(MeleeAttackFacet):
    damage = 3


class Pinch(MeleeAttackFacet):
    damage = 2
    cost = MovementCost(1)


class SnappingBeak(MeleeAttackFacet):
    damage = 2
    cost = MovementCost(1)


class Chainsaw(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.armor.g() <= 0:
            return 2


class LightBow(RangedAttackFacet):
    # TODO in notes or how should this be done?
    range = 3
    damage = 1


class APGun(RangedAttackFacet):
    cost = ExclusiveCost()
    range = 3
    ap = 1
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.size.g() > Size.MEDIUM:
            return 1


class HurlBoulder(RangedAttackFacet):
    cost = ExclusiveCost()
    range = 2
    #     +1 damage on rock terrain
    damage = 5


class HiddenBlade(MeleeAttackFacet):
    damage = 1

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.exhausted:
            return 1


class Bite(MeleeAttackFacet):
    damage = 3


# TODO xd, simple facet factory please
class OtterBite(MeleeAttackFacet):
    damage = 2


class HammerCannon(RangedAttackFacet):
    range = 2
    damage = 5


class SerratedClaws(MeleeAttackFacet):
    """+1 damage against damages units."""

    cost = MovementCost(1)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.damage > 0:
            return 1


class EtherealSting(MeleeAttackFacet):
    """Deals pure damage."""

    damage = 2
    damage_type = DamageType.PURE


class RoundhouseKick(MeleeAttackFacet):
    """+1 damage against staggered units."""

    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if any(isinstance(status, Staggered) for status in unit.statuses):
            return 1


class ScratchAndBite(MeleeAttackFacet):
    damage = 2


class Shiv(MeleeAttackFacet):
    """Doesn't follow up."""

    damage = 2
    combinable = True

    def should_follow_up(self) -> bool:
        return False


class Stinger(MeleeAttackFacet):
    damage = 2


class GlassFist(MeleeAttackFacet):
    damage = 3


class DiamondFist(MeleeAttackFacet):
    damage = 4


class Slay(MeleeAttackFacet):
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.size.g() >= Size.LARGE:
            return 2


class Tackle(MeleeAttackFacet):
    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(ApplyStatus(defender, StatusSignature(Stumbling, self)))


class FromTheTopRope(MeleeAttackFacet):
    damage = 4
    cost = MovementCost(1)

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if any(isinstance(status, Stumbling) for status in unit.statuses):
            return 1

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(Damage(self.owner, DamageSignature(2, self, lethal=False)))


class TwinRevolvers(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 2
    range = 3
    max_activations = 2


class BellHammer(MeleeAttackFacet):
    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(ApplyStatus(defender, StatusSignature(BellStruck, self, duration=2)))


class DeathLaser(RangedAttackFacet):
    cost = ExclusiveCost()
    damage = 4
    range = 4
