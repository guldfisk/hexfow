from events.eventsystem import ES
from game.game.core import (
    NoTargetActivatedAbility,
    GS,
    Unit,
    SingleAllyActivatedAbility,
    SingleEnemyActivatedAbility,
    SingleTargetActivatedAbility,
    ActivatedAbilityFacet,
    Hex,
    OneOfHexes,
    UnitBlueprint,
    SelectConsecutiveAdjacentHexes,
    SelectRadiatingLine,
    RangedAttackFacet,
    MeleeAttackFacet,
    StatusSignature,
    MovementCost,
    EnergyCost,
    ExclusiveCost,
    SingleHexTargetActivatedAbility,
    HexStatusSignature,
    DamageSignature,
)
from game.game.decisions import TargetProfile, O
from game.game.events import (
    Kill,
    Heal,
    ApplyStatus,
    MoveUnit,
    SpawnUnit,
    Damage,
    QueueUnitForActivation,
    SimpleAttack,
    ApplyHexStatus,
)
from game.game.hex_statuses import Shrine, Soot, BurningTerrain
from game.game.statuses import (
    Panicked,
    BurstOfSpeed,
    Staggered,
    Ephemeral,
    Rooted,
    LuckyCharm,
    Terror,
    Burn,
)
from game.game.units.facets.hooks import AdjacencyHook
from game.game.values import DamageType, Size


class Bloom(NoTargetActivatedAbility):
    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        for unit in GS().map.get_neighboring_units_off(self.owner):
            ES.resolve(Heal(unit, 1))
        ES.resolve(Kill(self.owner))


class Grow(NoTargetActivatedAbility):
    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        ES.resolve(Heal(self.owner, 1))


class HealBeam(SingleAllyActivatedAbility):
    cost = MovementCost(1) | EnergyCost(2)
    range = 2
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 3))


class Suicide(NoTargetActivatedAbility):
    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.owner))


class InducePanic(SingleEnemyActivatedAbility):
    range = 3
    cost = MovementCost(1) | EnergyCost(3)

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=target,
                by=self.owner.controller,
                signature=StatusSignature(Panicked, duration=3),
            )
        )


class LeapFrog(SingleTargetActivatedAbility):
    cost = MovementCost(1) | EnergyCost(1)
    range = 1
    combinable = True
    max_activations = None

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        target_position = GS().map.position_off(target)
        difference = target_position - GS().map.position_off(self.owner)
        target_hex = GS().map.hexes.get(target_position + difference)
        if target_hex and target_hex.can_move_into(self.owner):
            if (
                any(
                    e.result
                    for e in ES.resolve(MoveUnit(self.owner, target_hex)).iter_type(
                        MoveUnit
                    )
                )
                and target.controller != self.owner.controller
            ):

                ES.resolve(
                    ApplyStatus(
                        unit=target,
                        by=self.parent.controller,
                        signature=StatusSignature(Staggered),
                    )
                )


class BatonPass(SingleTargetActivatedAbility):
    range = 1
    cost = EnergyCost(1)

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.owner)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def can_target_unit(self, unit: Unit) -> bool:
        return (
            unit.controller == self.owner.controller
            and unit != self.owner
            and unit not in self.adjacency_hook.adjacent_units
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=target,
                by=self.owner.controller,
                signature=StatusSignature(BurstOfSpeed, stacks=1),
            )
        )


class SummonScarab(SingleHexTargetActivatedAbility):
    cost = MovementCost(2) | EnergyCost(3)
    range = 3

    # TODO common logic? or flag on SingleHexTargetActivatedAbility?
    def can_target_hex(self, hex_: Hex) -> bool:
        return (unit := GS().map.unit_on(hex_)) is None or unit.is_hidden_for(
            self.owner.controller
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["scarab"],
                controller=self.owner.controller,
                space=target,
                exhausted=True,
                with_statuses=[StatusSignature(Ephemeral, duration=3)],
            )
        )


# cyclops {15gg} x1
# health 11, movement 3, sight 1, L
# club
#     melee attack
#     5 damage
# sweep
#     aoe attack
#     aoe type 3 consecutive adjacent hexes
#     4 melee damage, -1 movement
# stare
#     combinable aoe ability
#         aoe type radiating line length 4 FoV propagation
#         reveals hexes this action


class Sweep(ActivatedAbilityFacet[list[Hex]]):
    cost = MovementCost(1)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return SelectConsecutiveAdjacentHexes(GS().map.hex_off(self.owner), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS().map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.MELEE)))


class Stare(ActivatedAbilityFacet[list[Hex]]):
    combinable = True

    def get_target_profile(self) -> TargetProfile[O] | None:
        return SelectRadiatingLine(GS().map.hex_off(self.owner), 4)

    def perform(self, target: list[Hex]) -> None:
        # TODO reveal em'
        pass


class Jaunt(ActivatedAbilityFacet[Hex]):
    cost = EnergyCost(3)
    combinable = True

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := list(GS().map.get_hexes_within_range_off(self.owner, 4)):
            return OneOfHexes(hexes)

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.owner, target))


# telepath {7pp} x1
# health 5, movement 3, sight 0, energy 5, M
# rouse
#     ability 3 energy
#     target other unit 3 range NLoS
#     -1 movement
#     activates target
# pacify
#     ability 3 energy
#     target other unit 3 range NLoS
#     -2 movement
#     applies pacified for 1 round
#         disarmed
#         +1 energy regen
# turn outwards
#     ability 3 energy
#     target other unit 2 range NLoS
#     -1 movement
#     applies far gazing for 2 rounds
#         +1 sight
#         cannot see adjacent hexes
# - adjacent enemy units also provide vision for this units controller


class Rouse(SingleTargetActivatedAbility):
    cost = MovementCost(1) | EnergyCost(3)
    range = 3
    requires_los = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        # TODO make it not able to skip?
        ES.resolve(QueueUnitForActivation(target))


# bee shaman {7wrp} x2
# health 4, movement 3, sight 2, energy 3, S
# summon bees
#     ability 2 energy
#     target hex 2 range LoS, -2 movement
#     summons bee swarm with ephemeral duration 1 round
# royal jelly
#     ability 2 energy
#     target different allied unit 2 range LoS, -1 movement
#     heals 2 and restores 1 energy


class SummonBees(SingleHexTargetActivatedAbility):
    cost = MovementCost(2) | EnergyCost(2)
    range = 2

    def can_target_hex(self, hex_: Hex) -> bool:
        return (unit := GS().map.unit_on(hex_)) is None or unit.is_hidden_for(
            self.owner.controller
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["bee_swarm"],
                controller=self.owner.controller,
                space=target,
                with_statuses=[StatusSignature(Ephemeral, duration=1)],
            )
        )


class StimulatingInjection(SingleTargetActivatedAbility):
    range = 1
    cost = EnergyCost(3)

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.TRUE)))
        # TODO event
        target.exhausted = False
        ES.resolve(Kill(self.owner))


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


class Suplex(SingleTargetActivatedAbility):
    range = 1
    cost = MovementCost(2) | EnergyCost(3)

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner and unit.size.g() < Size.LARGE

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(3, self, DamageType.MELEE)))
        own_position = GS().map.position_off(self.owner)
        if target_hex := GS().map.hexes.get(
            own_position + (own_position - GS().map.position_off(target))
        ):
            ES.resolve(MoveUnit(target, target_hex))


# notorious outlaw
# health 5, movement 3, sight 2, energy 3, M
# twin revolvers
#     2x repeatable ranged attack
#     2 damage, 3 range, -1 movement
# lasso
#     combineable ability 3 energy
#     target enemy unit 2 range LoS
#     -2 movement
#     applies rooted for 1 round
# showdown
#     ability 3 energy
#     target enemy unit 3 range LoS
#     no movement
#     hits the targeted unit with primary ranged attack twice
#     if it is still alive, it will first try to hit with it's primary ranged attack if it has one, if it doesn't or can't,
#     it will try to hit with it's primary melee attack.
#     if it hits this way, exhaust it
# - dash
#     when this unit ends it's turn, it may move one space (irregardless of movement points)


class Lasso(SingleEnemyActivatedAbility):
    range = 2
    cost = MovementCost(2) | EnergyCost(3)
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=target,
                by=self.owner.controller,
                signature=StatusSignature(Rooted, duration=1),
            )
        )


class Showdown(SingleEnemyActivatedAbility):
    range = 3
    cost = ExclusiveCost() | EnergyCost(3)

    def perform(self, target: Unit) -> None:
        if attack := self.owner.get_primary_attack(RangedAttackFacet):
            for _ in range(2):
                ES.resolve(
                    SimpleAttack(attacker=self.owner, defender=target, attack=attack)
                )

        if not target.exhausted:
            for attack_type in (RangedAttackFacet, MeleeAttackFacet):
                if (
                    defender_attack := target.get_primary_attack(attack_type)
                ) and self.owner in defender_attack.get_legal_targets(None):
                    ES.resolve(
                        SimpleAttack(
                            attacker=target, defender=self.owner, attack=defender_attack
                        )
                    )
                    # TODO
                    target.exhausted = True
                    break


# shrine keeper {5pp} x1
# health 4, movement 3, sight 2, 4 energy, S
# raise shrine
#     ability 3 energy, -2 movement
#     target hex 1 range
#     applies status shrine to terrain
#         units on this hex has +1 mana regen
#         whenever a unit within 1 range skips, heal it 1
#         whenever a unit enters this hex, apply buff fortified for 4 rounds
#             unstackable, refreshable
#             +1 max health
# lucky charm
#     ability 1 energy
#     target different allied unit 1 range
#     applies buff lucky charm for 3 rounds
#         unstackable, refreshable
#         if this unit would suffer exactly one damage, instead remove this buff
# clean up
#     combinable ability 2 energy, -2 movement
#     target hex 1 range
#     removes all statuses from hex


class RaiseShrine(SingleHexTargetActivatedAbility):
    cost = MovementCost(2) | EnergyCost(3)

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(target, self.owner.controller, HexStatusSignature(Shrine))
        )


class GrantCharm(SingleAllyActivatedAbility):
    can_target_self = False
    cost = EnergyCost(1)

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, self.owner.controller, StatusSignature(LuckyCharm, duration=3)
            )
        )


# TODO should be an aoe target
class ChokingSoot(SingleHexTargetActivatedAbility):
    range = 2
    cost = MovementCost(1) | EnergyCost(4)
    requires_los = False
    requires_vision = False

    def perform(self, target: Hex) -> None:
        for _hex in GS().map.get_hexes_within_range_off(target, 1):
            ES.resolve(
                ApplyHexStatus(
                    _hex, self.owner.controller, HexStatusSignature(Soot, duration=3)
                )
            )


class Terrorize(SingleEnemyActivatedAbility):
    range = 4
    cost = ExclusiveCost()

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, self.owner.controller, StatusSignature(Terror, duration=2)
            )
        )


# TODO should be an aoe target and attack
class Scorch(SingleHexTargetActivatedAbility):
    cost = MovementCost(1)

    def can_target_hex(self, hex_: Hex) -> bool:
        return hex_ != GS().map.hex_off(self.owner)

    def perform(self, target: Hex) -> None:
        hexes = list(GS().map.get_neighbors_off(self.owner))
        target_index = hexes.index(target)

        for offset in range(-1, 2):
            if unit := GS().map.unit_on(hexes[(target_index + offset) % len(hexes)]):
                ES.resolve(Damage(unit, DamageSignature(3, self, type=DamageType.AOE)))
                ES.resolve(
                    ApplyStatus(
                        unit, self.owner.controller, StatusSignature(Burn, stacks=2)
                    )
                )


# TODO should be an aoe target
class FlameWall(SingleHexTargetActivatedAbility):
    cost = MovementCost(1) | EnergyCost(3)

    def can_target_hex(self, hex_: Hex) -> bool:
        return hex_ != GS().map.hex_off(self.owner)

    def perform(self, target: Hex) -> None:
        difference = target.position - GS().map.position_off(self.owner)
        for i in range(3):
            if _hex := GS().map.hexes.get(target.position + difference * i):
                # TODO should it also apply burn to units in aoe initially?
                #  hard to figure out how to balance numbers, especially with
                #  order of triggers...
                ES.resolve(
                    ApplyHexStatus(
                        _hex,
                        self.owner.controller,
                        HexStatusSignature(BurningTerrain, stacks=2, duration=3),
                    )
                )
