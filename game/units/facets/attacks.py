from more_itertools.recipes import is_prime

from events.eventsystem import ES
from game.core import (
    GS,
    DamageSignature,
    ExclusiveCost,
    MeleeAttackFacet,
    MovementCost,
    RangedAttackFacet,
    Unit,
)
from game.effects.hooks import AdjacencyHook
from game.events import Damage, Heal
from game.statuses.shortcuts import apply_status_to_unit
from game.values import DamageType, Size, StatusIntention


class Peck(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 1


class BurningSting(MeleeAttackFacet):
    """Applies 1 stack of <burn>."""

    cost = MovementCost(1)
    damage = 1

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "burn", self, stacks=1)


class Scratch(MeleeAttackFacet):
    cost = MovementCost(1)
    combinable = True
    damage = 2


class GiantClub(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 5


class CurvedHorns(MeleeAttackFacet):
    cost = MovementCost(2)
    damage = 3


class DancingSaber(MeleeAttackFacet):
    """
    +2 damage against spawned units.
    """

    cost = MovementCost(1)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.is_spawned:
            return 2


class Gore(MeleeAttackFacet):
    """
    +3 damage against units this unit wasn't adjacent to at the beginning of its turn.
    """

    cost = MovementCost(1)
    damage = 3

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.parent)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def get_damage_modifier_against(self, unit: Unit) -> int:
        if unit not in self.adjacency_hook.adjacent_units:
            return 3


class MarshmallowFist(MeleeAttackFacet):
    damage = 2


class GnomeSpear(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 2


class SerratedBeak(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 2


class RazorTusk(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 3


class StandardIssueBlaster(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 3
    range = 2


class BloodExpunge(RangedAttackFacet):
    """+1 damage for each unique debuff the target has."""

    cost = MovementCost(2)
    damage = 2
    range = 3

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
        apply_status_to_unit(self.parent, "stunned", self, stacks=1)


class HammerBlow(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 4


class MightyBlow(MeleeAttackFacet):
    """
    Applies 1 stack of <stunned> to this unit.
    """

    cost = ExclusiveCost()
    damage = 6

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(self.parent, "stunned", self, stacks=1)


class LightBlaster(RangedAttackFacet):
    damage = 2
    range = 3


class Strafe(RangedAttackFacet):
    damage = 2
    range = 2
    cost = MovementCost(1)
    combinable = True


class Engage(MeleeAttackFacet):
    cost = MovementCost(2)
    damage = 4


class Pinch(MeleeAttackFacet):
    damage = 2
    cost = ExclusiveCost()


class SnappingBeak(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 2


class FleaBite(MeleeAttackFacet):
    damage = 1


class CrushingFists(MeleeAttackFacet):
    """
    +2 damage against exhausted units.
    """

    cost = ExclusiveCost()
    damage = 4

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.exhausted:
            return 2


class StubbyClaws(MeleeAttackFacet):
    cost = ExclusiveCost()
    damage = 1


class SturdyClaws(MeleeAttackFacet):
    cost = ExclusiveCost()
    damage = 2


class GranGransOlClub(MeleeAttackFacet):
    """
    +1 damage against units with 2 or less speed, or who doesn't have any legal move options.
    """

    name = "Gran Grans Ol' Club"
    cost = ExclusiveCost()
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.speed.g() <= 2 or not unit.get_potential_move_destinations(None):
            return 1


class CrypticClaws(MeleeAttackFacet):
    """
    +2 damage on prime rounds (1 is not prime).
    """

    cost = MovementCost(1)
    damage = 2

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if is_prime(GS.round_counter):
            return 2


class GuillotineAxe(MeleeAttackFacet):
    """
    +3 damage against units with less than or equal health to half their max health, rounded down.
    """

    cost = MovementCost(1)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.health <= unit.max_health.g() // 2:
            return 3


class AnkleBite(MeleeAttackFacet):
    """Applies <stumbling>."""

    damage = 1
    combinable = True

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "stumbling", self)


class Frostbite(MeleeAttackFacet):
    """
    Applies <chill> for 3 rounds.
    """

    cost = MovementCost(1)
    damage = 1
    combinable = True

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "chill", self, duration=3)


class FinalSting(MeleeAttackFacet):
    """
    Applies 1 <poison>. Deals 1 pure damage to this unit.
    """

    cost = MovementCost(1)
    damage = 1

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "poison", self, stacks=1)
        ES.resolve(Damage(self.parent, DamageSignature(1, self, DamageType.PURE)))


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
    +1 damage against small units.
    """

    cost = ExclusiveCost()
    range = 2
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.size.g() == Size.SMALL:
            return 1


class Slice(MeleeAttackFacet):
    cost = MovementCost(2)
    damage = 2


class Spew(RangedAttackFacet):
    """
    Applies <slimed> for 2 rounds.
    """

    cost = ExclusiveCost()
    range = 1
    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "slimed", self, duration=2)


class CommandersPistol(RangedAttackFacet):
    cost = MovementCost(1)
    range = 2
    damage = 2


class ServicePistol(RangedAttackFacet):
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
    cost = MovementCost(1)
    damage = 3


class OtterBite(MeleeAttackFacet):
    damage = 2


class HammerCannon(RangedAttackFacet):
    range = 2
    damage = 5


class SerratedClaws(MeleeAttackFacet):
    """+1 damage against damaged units."""

    cost = MovementCost(2)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.damage > 0:
            return 1


class EtherealSting(MeleeAttackFacet):
    """Deals pure damage."""

    cost = MovementCost(1)
    damage = 2
    damage_type = DamageType.PURE


class ViciousBite(MeleeAttackFacet):
    """+1 damage against damaged units."""

    cost = MovementCost(1)
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.damage > 0:
            return 1


class RoundhouseKick(MeleeAttackFacet):
    """+1 damage against staggered units."""

    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.has_status("staggered"):
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
    cost = MovementCost(1)
    damage = 3


class DiamondFist(MeleeAttackFacet):
    damage = 4


class Slay(MeleeAttackFacet):
    """
    +2 damage against large units.
    """

    cost = MovementCost(1)
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
        apply_status_to_unit(defender, "stumbling", self)


class FromTheTopRope(MeleeAttackFacet):
    """
    +1 damage against stumbling units. Deals 2 non-lethal damage to this unit as well.
    """

    damage = 4
    cost = MovementCost(2)

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.has_status("stumbling"):
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
        apply_status_to_unit(defender, "burn", self, stacks=2)


class Gnaw(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 2


class DrainingGrasp(MeleeAttackFacet):
    """
    Heals this unit 1.
    """

    cost = MovementCost(1)
    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(Heal(self.parent, 1, self))


class BellHammer(MeleeAttackFacet):
    """
    Applies status <bell_struck> for 2 rounds.
    """

    cost = MovementCost(1)
    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "bell_struck", self, duration=2)


class DeathLaser(RangedAttackFacet):
    cost = ExclusiveCost()
    damage = 4
    range = 4


class MiniGun(RangedAttackFacet):
    cost = ExclusiveCost()
    damage = 3
    range = 3


class Wrench(MeleeAttackFacet):
    """
    +2 damage against units with 1 or more base armor.
    """

    cost = MovementCost(2)
    damage = 2

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.armor.get_base() > 0:
            return 2


class SlingShot(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 2
    range = 1


class Lance(MeleeAttackFacet):
    cost = MovementCost(3)
    damage = 3


class Swelter(RangedAttackFacet):
    """Applies <parched> for 2 rounds."""

    cost = MovementCost(2)
    damage = 2
    range = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "parched", self, duration=2)


class SniperRifle(RangedAttackFacet):
    """
    +2 damage against exhausted units.
    """

    cost = ExclusiveCost()
    damage = 2
    range = 4

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if unit.exhausted:
            return 2


class Chomp(MeleeAttackFacet):
    cost = ExclusiveCost()
    damage = 4


class CrushingMandibles(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 3


class Grapple(MeleeAttackFacet):
    """
    Applies <rooted> for 1 round.
    """

    cost = ExclusiveCost()
    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        apply_status_to_unit(defender, "rooted", self, duration=1)
