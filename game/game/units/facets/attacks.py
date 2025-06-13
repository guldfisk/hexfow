from events.eventsystem import ES
from game.game.core import (
    MeleeAttackFacet,
    RangedAttackFacet,
    Unit,
    StatusSignature,
    MovementCost,
    ExclusiveCost,
    DamageSignature,
)
from game.game.events import Damage, ApplyStatus
from game.game.statuses import Staggered, Stumbling, Parasite, BellStruck
from game.game.units.facets.hooks import AdjacencyHook
from game.game.values import Size


class Peck(MeleeAttackFacet):
    damage = 1


class BuglingClaw(MeleeAttackFacet):
    combinable = True
    damage = 2


class GiantClub(MeleeAttackFacet):
    damage = 5


class Gore(MeleeAttackFacet):
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


class Inject(MeleeAttackFacet):
    cost = MovementCost(1)
    damage = 4

    def resolve_pre_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=defender,
                by=self.owner.controller,
                signature=StatusSignature(Parasite),
            )
        )


class Sting(MeleeAttackFacet):
    damage = 2


class RoundhouseKick(MeleeAttackFacet):
    damage = 3

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if any(isinstance(status, Staggered) for status in unit.statuses):
            return 1


# # bee swarm {-}
# # health 2, movement 3, sight 1, S
# # sting
# #     melee attack
# #     2 damage
# #     ignores terrain protection
# # - flying
# # - greater melee/ranged resistant


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


# legendary wrestler {11pg} x1
# health 7, movement 3, sight 2, energy 4, M
# tackle
#     melee attack
#     2 damage
#     applies stumble
#         -1 movement point next activation
# from the top rope
#     melee attack
#     4 damage, -1 movement
#     +1 damage against units with stumble debuff
#     deals 2 non-lethal physical damage to this unit
# supplex
#     ability 3 energy, -2 movement
#     target M- adjacent unit
#     deals 3 melee damage and moves the target to the other side of this unit, if able.
# - caught in the match
#     enemies disengageging this units suffers -1 movement point
# - heel turn
#     when this unit receives 4 or more damage in a single instance, it gets, "they've got a still chari"
#         unstackable
#         +1 attack power


class Tackle(MeleeAttackFacet):
    damage = 2

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=defender,
                by=self.owner.controller,
                signature=StatusSignature(Stumbling),
            )
        )


class FromTheTopRope(MeleeAttackFacet):
    damage = 4
    cost = MovementCost(1)

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        if any(isinstance(status, Stumbling) for status in unit.statuses):
            return 1

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(Damage(self.owner, DamageSignature(2, lethal=False)))


class TwinRevolvers(RangedAttackFacet):
    cost = MovementCost(1)
    damage = 2
    range = 3
    max_activations = 2


class BellHammer(MeleeAttackFacet):
    damage = 4

    def resolve_post_damage_effects(self, defender: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=defender,
                by=self.owner.controller,
                signature=StatusSignature(BellStruck, duration=2),
            )
        )
