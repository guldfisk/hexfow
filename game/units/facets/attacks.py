from events.eventsystem import ES
from game.core import (
    DamageSignature,
    ExclusiveCost,
    MeleeAttackFacet,
    MovementCost,
    RangedAttackFacet,
    Unit,
    UnitStatus,
    UnitStatusSignature,
)
from game.effects.hooks import AdjacencyHook
from game.events import ApplyStatus, Damage
from game.statuses.unit_statuses import BellStruck, Staggered, Stumbling
from game.values import DamageType, Size, StatusIntention


class Peck(MeleeAttackFacet):
    damage = 1


class BuglingClaw(MeleeAttackFacet):
    cost = MovementCost(1)
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

        self.adjacency_hook = AdjacencyHook(self.parent)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def get_damage_modifier_against(self, unit: Unit) -> int:
        if unit not in self.adjacency_hook.adjacent_units:
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
    """
    Applies 1 stack of <stunned> to this unit.
    """

    damage = 4
    range = 4
    cost = ExclusiveCost()

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                self.parent,
                UnitStatusSignature(UnitStatus.get("stunned"), self, stacks=1),
            )
        )


class HammerBlow(MeleeAttackFacet):
    damage = 4


class MightyBlow(MeleeAttackFacet):
    """
    Applies 1 stack of <stunned> to this unit.
    """

    cost = ExclusiveCost()
    damage = 6

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                self.parent,
                UnitStatusSignature(UnitStatus.get("stunned"), self, stacks=1),
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
    cost = ExclusiveCost()


class SnappingBeak(MeleeAttackFacet):
    damage = 2
    cost = MovementCost(1)


class Chainsaw(MeleeAttackFacet):
    """
    +2 damage against unarmored units.
    """

    cost = MovementCost(2)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.armor.g() <= 0:
            return 2


class LightBow(RangedAttackFacet):
    range = 3
    damage = 1


class APGun(RangedAttackFacet):
    """
    +1 damage against large. Ignores 1 armor.
    """

    cost = ExclusiveCost()
    range = 3
    ap = 1
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.size.g() > Size.MEDIUM:
            return 1


class Rifle(RangedAttackFacet):
    cost = MovementCost(2)
    range = 3
    damage = 3


class RifleSalvo(RangedAttackFacet):
    cost = MovementCost(1)
    range = 3
    damage = 3


class TongueLash(RangedAttackFacet):
    """
    Deals melee damage.
    """

    cost = ExclusiveCost()
    range = 2
    damage = 3
    damage_type = DamageType.MELEE


class Slice(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 3


class Spew(RangedAttackFacet):
    """
    Applies <slimed> for 2 rounds.
    """

    cost = ExclusiveCost()
    range = 1
    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                defender,
                UnitStatusSignature(UnitStatus.get("slimed"), self, duration=2),
            )
        )


class CommandersPistol(RangedAttackFacet):
    cost = MovementCost(1)
    range = 2
    damage = 2


class HurlBoulder(RangedAttackFacet):
    cost = ExclusiveCost()
    range = 2
    damage = 5


class HiddenBlade(MeleeAttackFacet):
    """
    +2 damage against exhausted units.
    """

    damage = 1

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.exhausted:
            return 2


class Bite(MeleeAttackFacet):
    damage = 3


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

    cost = MovementCost(1)
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
    """
    +2 damage against large units.
    """

    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.size.g() >= Size.LARGE:
            return 2


class Tackle(MeleeAttackFacet):
    """
    Applies <stumbling>.
    """

    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(ApplyStatus(defender, UnitStatusSignature(Stumbling, self)))


class FromTheTopRope(MeleeAttackFacet):
    """
    +1 damage against stumbling units. Deals 2 non-lethal damage to this unit as well.
    """

    damage = 4
    cost = MovementCost(1)

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if any(isinstance(status, Stumbling) for status in unit.statuses):
            return 1

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(Damage(self.parent, DamageSignature(2, self, lethal=False)))


class TwinRevolvers(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 2
    range = 3
    max_activations = 2


class InfernalBlade(MeleeAttackFacet):
    """
    Applies 2 <burn>.
    """

    cost = MovementCost(2)
    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                defender, UnitStatusSignature(UnitStatus.get("burn"), self, stacks=2)
            )
        )


class BellHammer(MeleeAttackFacet):
    """
    Applies status <bell_struck> for 2 rounds.
    """

    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(defender, UnitStatusSignature(BellStruck, self, duration=2))
        )


class DeathLaser(RangedAttackFacet):
    cost = ExclusiveCost()
    damage = 4
    range = 4


class MiniGun(RangedAttackFacet):
    cost = ExclusiveCost()
    damage = 3
    range = 3


class Wrench(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 2


class SlingShot(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 2
    range = 1


class Chomp(MeleeAttackFacet):
    cost = ExclusiveCost()
    damage = 3
