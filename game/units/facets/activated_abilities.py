from events.eventsystem import ES
from game.core import (
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
    ConsecutiveAdjacentHexes,
    RadiatingLine,
    RangedAttackFacet,
    MeleeAttackFacet,
    StatusSignature,
    MovementCost,
    EnergyCost,
    ExclusiveCost,
    SingleHexTargetActivatedAbility,
    HexStatusSignature,
    DamageSignature,
    line_of_sight_obstructed_for_unit,
    NOfUnits,
    HexHexes,
    UnitStatus,
    HexStatus,
    Cone,
    TreeNode,
    Tree,
    HexRing,
)
from game.decisions import TargetProfile, O
from game.effects.hooks import AdjacencyHook
from game.events import (
    Kill,
    Heal,
    ApplyStatus,
    MoveUnit,
    SpawnUnit,
    Damage,
    QueueUnitForActivation,
    Hit,
    ApplyHexStatus,
    GainEnergy,
    ModifyMovementPoints,
    ReadyUnit,
    ExhaustUnit,
)
from game.statuses.hexes import Shrine, Soot, BurningTerrain, Smoke, Glimpse
from game.statuses.units import (
    Panicked,
    BurstOfSpeed,
    Staggered,
    Ephemeral,
    Rooted,
    LuckyCharm,
    Terror,
    Burn,
)
from game.values import DamageType, Size, VisionObstruction


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
    """
    Target other allied unit within 2 range LoS. Heals 3.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 3))


class GreaseTheGears(SingleAllyActivatedAbility):
    """
    Target other allied unit 1 range. Kills the target. If it does, heal this unit 2, and it restores 2 energy.
    If the target unit was ready, this unit gains +1 movement point.
    """

    range = 1
    can_target_self = False
    combinable = True
    max_activations = None

    def perform(self, target: Unit) -> None:
        movement_bonus = 1 if not target.exhausted and GS().active_unit_context else 0
        if any(
            kill_event.unit == target
            for kill_event in ES.resolve(Kill(target)).iter_type(Kill)
        ):
            ES.resolve(Heal(self.owner, 2))
            ES.resolve(GainEnergy(self.owner, 2))
            ES.resolve(ModifyMovementPoints(self.owner, movement_bonus))


class NothingStopsTheMail(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.owner))


class SelfDestruct(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.owner))


class InducePanic(SingleEnemyActivatedAbility):
    range = 3
    cost = MovementCost(1) | EnergyCost(5)

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, StatusSignature(Panicked, self, duration=2)))


class Vault(SingleTargetActivatedAbility):
    """
    Moves this unit to the other side of target adjacent unit. If it did, and the target unit was
    an enemy, apply staggered to it.
    """

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
                ES.resolve(ApplyStatus(target, StatusSignature(Staggered, self)))


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
        ES.resolve(ApplyStatus(target, StatusSignature(BurstOfSpeed, self, stacks=1)))


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
                with_statuses=[StatusSignature(Ephemeral, self, duration=3)],
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
        return ConsecutiveAdjacentHexes(GS().map.hex_off(self.owner), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS().map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.MELEE)))


class Stare(ActivatedAbilityFacet[list[Hex]]):
    combinable = True

    def get_target_profile(self) -> TargetProfile[O] | None:
        return RadiatingLine(
            GS().map.hex_off(self.owner),
            list(GS().map.get_neighbors_off(self.owner)),
            4,
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(ApplyHexStatus(h, HexStatusSignature(Glimpse, self)))
            # TODO handle highground
            if h.blocks_vision_for(self.owner.controller) != VisionObstruction.NONE:
                break


class Jaunt(ActivatedAbilityFacet[Hex]):
    """Teleports to target hex within 4 range NLoS."""

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
                with_statuses=[StatusSignature(Ephemeral, self, duration=1)],
            )
        )


class StimulatingInjection(SingleTargetActivatedAbility):
    """
    Target other unit within 1 range.
    Deals 1 pure damage and readies the target.
    This unit dies.
    """

    range = 1
    cost = EnergyCost(3)

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.PURE)))
        ES.resolve(ReadyUnit(target))
        # TODO sacrifice as a cost?
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
        ES.resolve(ApplyStatus(target, StatusSignature(Rooted, self, duration=1)))


class Showdown(SingleEnemyActivatedAbility):
    range = 3
    cost = ExclusiveCost() | EnergyCost(3)

    def perform(self, target: Unit) -> None:
        if attack := self.owner.get_primary_attack(RangedAttackFacet):
            for _ in range(2):
                ES.resolve(Hit(attacker=self.owner, defender=target, attack=attack))

        if not target.exhausted:
            for attack_type in (RangedAttackFacet, MeleeAttackFacet):
                if (
                    defender_attack := target.get_primary_attack(attack_type)
                ) and self.owner in defender_attack.get_legal_targets(None):
                    ES.resolve(
                        Hit(
                            attacker=target, defender=self.owner, attack=defender_attack
                        )
                    )
                    ES.resolve(ExhaustUnit(target))
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
        ES.resolve(ApplyHexStatus(target, HexStatusSignature(Shrine, self)))


class GrantCharm(SingleAllyActivatedAbility):
    can_target_self = False
    cost = EnergyCost(1)

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, StatusSignature(LuckyCharm, self, duration=3)))


class ChokingSoot(ActivatedAbilityFacet[list[Hex]]):
    cost = MovementCost(1) | EnergyCost(4)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS().map.get_hexes_within_range_off(self.owner, 2)
        ]:
            return HexHexes(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(ApplyHexStatus(_hex, HexStatusSignature(Soot, self, duration=2)))


# TODO should be an aoe target
class SmokeCanister(SingleHexTargetActivatedAbility):
    range = 2
    cost = EnergyCost(3)
    requires_los = False
    requires_vision = False
    combinable = True

    def perform(self, target: Hex) -> None:
        for _hex in GS().map.get_hexes_within_range_off(target, 1):
            ES.resolve(
                ApplyHexStatus(_hex, HexStatusSignature(Smoke, self, duration=2))
            )


class Terrorize(SingleEnemyActivatedAbility):
    range = 4
    cost = MovementCost(2) | EnergyCost(5)

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, StatusSignature(Terror, self, duration=2)))


# TODO should be an attack
class Scorch(ActivatedAbilityFacet[list[Hex]]):
    cost = MovementCost(1)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return ConsecutiveAdjacentHexes(GS().map.hex_off(self.owner), 1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS().map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.AOE)))
                ES.resolve(ApplyStatus(unit, StatusSignature(Burn, self, stacks=2)))


class FlameWall(ActivatedAbilityFacet[list[Hex]]):
    cost = MovementCost(1) | EnergyCost(3)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return RadiatingLine(
            GS().map.hex_off(self.owner),
            list(GS().map.get_neighbors_off(self.owner)),
            3,
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(
                ApplyHexStatus(
                    h,
                    HexStatusSignature(BurningTerrain, self, stacks=1, duration=3),
                )
            )
            if unit := GS().map.unit_on(h):
                ES.resolve(ApplyStatus(unit, StatusSignature(Burn, self, stacks=2)))


class FlameThrower(ActivatedAbilityFacet[list[Hex]]):
    cost = EnergyCost(3)

    # TODO variable length cone?
    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return Cone(
            GS().map.hex_off(self.owner),
            list(GS().map.get_neighbors_off(self.owner)),
            [0, 0, 1],
        )

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(
                ApplyHexStatus(
                    h,
                    HexStatusSignature(BurningTerrain, self, stacks=1, duration=2),
                )
            )
            if unit := GS().map.unit_on(h):
                ES.resolve(ApplyStatus(unit, StatusSignature(Burn, self, stacks=1)))


class VitalityTransfer(ActivatedAbilityFacet):
    """
    Target two allied units within 3 range LoS.
    Transfers health from the second to the first unit.
    Amount transferred is the minimum of 3, how much the recipient is missing, and how much the donor can give without dying.
    """

    cost = MovementCost(1) | EnergyCost(2)

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if (
            len(
                # TODO some common logic for this trash
                units := [
                    unit
                    for unit in GS().map.get_units_within_range_off(self.owner, 3)
                    if unit.controller == self.owner.controller
                    and unit.is_visible_to(self.owner.controller)
                    and not line_of_sight_obstructed_for_unit(
                        self.owner,
                        GS().map.position_off(self.owner),
                        GS().map.position_off(unit),
                    )
                ]
            )
            >= 2
        ):
            return NOfUnits(units, 2, ["select recipient", "select donor"])

    def perform(self, target: list[Unit]) -> None:
        recipient, donor = target
        available_health = min(donor.health - 1, recipient.damage, 3)
        if available_health:
            # TODO yikes should be an event, but unclear what it should be,
            #  since we don't want it to be damage i think.
            donor.damage += available_health
            ES.resolve(Heal(recipient, available_health))


class Shove(SingleTargetActivatedAbility):
    """
    Moves target adjacent unit one space away from this unit. If it is staggered, this unit gains 1 movement point.
    """

    cost = MovementCost(1) | EnergyCost(2)
    range = 1
    combinable = True

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.owner

    def perform(self, target: Unit) -> None:
        target_position = GS().map.position_off(target)
        ES.resolve(
            MoveUnit(
                target,
                GS().map.hexes.get(
                    target_position
                    + (target_position - GS().map.position_off(self.owner))
                ),
            )
        )
        if any(isinstance(status, Staggered) for status in target.statuses):
            ES.resolve(ModifyMovementPoints(self.owner, 1))


class Poof(SingleHexTargetActivatedAbility):
    """Applies Smoke to the current position of this unit for 1 round, and moves this unit to target adjacent hex."""

    cost = EnergyCost(2)
    combinable = True
    requires_los = False
    requires_vision = False

    def can_target_hex(self, hex_: Hex) -> bool:
        return hex_.can_move_into(self.owner)

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                GS().map.hex_off(self.owner),
                HexStatusSignature(Smoke, self, duration=1),
            )
        )
        ES.resolve(MoveUnit(self.owner, target))


class VenomousSpine(SingleEnemyActivatedAbility):
    """
    Target enemy unit 2 range LoS. Applies debilitating venom for 2 rounds and parasite.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, StatusSignature(UnitStatus.get("parasite"), self))
        )
        ES.resolve(
            ApplyStatus(
                target,
                StatusSignature(UnitStatus.get("debilitating_venom"), self, duration=2),
            )
        )


# TODO this has the same problem as glimpse with round ending.
class Scry(SingleHexTargetActivatedAbility):
    """
    Target hex within 6 range NLoS. Applies revealed for 1 round.
    """

    cost = ExclusiveCost() | EnergyCost(2)
    range = 6
    requires_los = False
    requires_vision = False

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                target, HexStatusSignature(HexStatus.get("revealed"), self, duration=1)
            )
        )


class ShrinkRay(SingleTargetActivatedAbility):
    cost = MovementCost(1) | EnergyCost(3)
    range = 2

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.RANGED)))
        ES.resolve(
            ApplyStatus(
                target,
                StatusSignature(UnitStatus.get("shrunk"), self, stacks=1, duration=2),
            )
        )


class AssembleTheDoombot(SingleHexTargetActivatedAbility):
    cost = ExclusiveCost() | EnergyCost(4)
    range = 1

    def can_target_hex(self, hex_: Hex) -> bool:
        return not GS().map.unit_on(hex_)

    def perform(self, target: Hex) -> None:
        if statuses := target.get_statuses(HexStatus.get("doombot_scaffold")):
            # TODO dispell etc
            for status in statuses:
                status.remove()
            ES.resolve(
                SpawnUnit(
                    UnitBlueprint.registry["doombot_3000"],
                    self.owner.controller,
                    target,
                    exhausted=True,
                    with_statuses=[
                        StatusSignature(UnitStatus.get("ephemeral"), self, duration=4)
                    ],
                )
            )
        else:
            ES.resolve(
                ApplyHexStatus(
                    target, HexStatusSignature(HexStatus.get("doombot_scaffold"), self)
                )
            )


class Translocate(ActivatedAbilityFacet):
    cost = EnergyCost(2)
    combinable = True

    def get_target_profile(self) -> TargetProfile[list[Unit | Hex]] | None:
        if units := [
            (
                unit,
                TreeNode(
                    [(h, None) for h in GS().map.get_neighbors_off(unit)], "select hex"
                ),
            )
            for unit in GS().map.get_units_within_range_off(self.owner, 1)
            if unit.is_visible_to(self.owner.controller)
        ]:
            return Tree(TreeNode(units, "select unit"))

    def perform(self, target: list[Hex | Unit]) -> None:
        unit, to_ = target
        ES.resolve(MoveUnit(unit, to_))


class InkRing(ActivatedAbilityFacet):
    cost = EnergyCost(3)

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS().map.get_hexes_within_range_off(self.owner, 2)
        ]:
            return HexRing(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for unit in GS().map.units_on(target):
            ES.resolve(
                ApplyStatus(
                    unit, StatusSignature(UnitStatus.get("blinded"), self, duration=3)
                )
            )


class MalevolentStare(SingleEnemyActivatedAbility):
    cost = EnergyCost(3) | MovementCost(2)
    range = 3

    def perform(self, target: Unit) -> None:
        # TODO should also dispell buffs
        ES.resolve(
            ApplyStatus(
                target, StatusSignature(UnitStatus.get("silenced"), self, duration=2)
            )
        )
