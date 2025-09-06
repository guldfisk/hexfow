import itertools

from events.eventsystem import ES
from game.core import (
    GS,
    ActivatedAbilityFacet,
    ActiveUnitContext,
    DamageSignature,
    EnergyCost,
    ExclusiveCost,
    Hex,
    HexStatus,
    HexStatusSignature,
    MeleeAttackFacet,
    MovementCost,
    MoveOption,
    NoTarget,
    OneOfHexes,
    RangedAttackFacet,
    SelectOptionAtHexDecisionPoint,
    SelectOptionDecisionPoint,
    SkipOption,
    TargetProfile,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusSignature,
    find_hexs_within_range,
    find_units_within_range,
    is_vision_obstructed_for_unit_at,
)
from game.effects.hooks import AdjacencyHook
from game.events import (
    ApplyHexStatus,
    ApplyStatus,
    Damage,
    DispelStatus,
    ExhaustUnit,
    GainEnergy,
    Heal,
    Hit,
    Kill,
    LoseEnergy,
    ModifyMovementPoints,
    MoveUnit,
    QueueUnitForActivation,
    ReadyUnit,
    SpawnUnit,
)
from game.statuses.dispel import dispel_all, dispel_from_unit
from game.statuses.hex_statuses import BurningTerrain, Glimpse, Shrine, Smoke, Soot
from game.statuses.links import GateLink, TaintedLink
from game.statuses.unit_statuses import (
    Burn,
    BurstOfSpeed,
    Ephemeral,
    LuckyCharm,
    Panicked,
    Rooted,
    Staggered,
    Terror,
)
from game.target_profiles import Cone, HexRing, NOfHexes, NOfUnits, Tree, TreeNode
from game.targeting import (
    ControllerTargetOption,
    NoTargetActivatedAbility,
    TargetHexActivatedAbility,
    TargetHexArcActivatedAbility,
    TargetHexCircleActivatedAbility,
    TargetRadiatingLineActivatedAbility,
    TargetTriHexActivatedAbility,
    TargetUnitActivatedAbility,
)
from game.values import DamageType, StatusIntention


class Bloom(NoTargetActivatedAbility):
    """
    Heals each adjacent allied unit 1. This unit dies.
    """

    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        for unit in GS.map.get_neighboring_units_off(self.parent):
            ES.resolve(Heal(unit, 1))
        ES.resolve(Kill(self.parent))


class Grow(NoTargetActivatedAbility):
    cost = EnergyCost(2)

    def perform(self, target: None) -> None:
        ES.resolve(Heal(self.parent, 1))


class HealBeam(TargetUnitActivatedAbility):
    """
    Heals 2.
    """

    cost = EnergyCost(3)
    range = 2
    can_target_self = False
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 2))


class GreaseTheGears(TargetUnitActivatedAbility):
    """
    Kills the target. If it does, heal this unit 2, and it restores 2 energy.
    If the target unit was ready, this unit gains +1 movement point.
    """

    can_target_self = False
    controller_target_option = ControllerTargetOption.ALLIED
    combinable = True
    max_activations = None

    def perform(self, target: Unit) -> None:
        movement_bonus = 1 if not target.exhausted and GS.active_unit_context else 0
        if any(
            kill_event.unit == target
            for kill_event in ES.resolve(Kill(target)).iter_type(Kill)
        ):
            ES.resolve(Heal(self.parent, 2))
            ES.resolve(GainEnergy(self.parent, 2, source=self))
            ES.resolve(ModifyMovementPoints(self.parent, movement_bonus))


class SelfDestruct(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.parent))


class GrantWish(TargetUnitActivatedAbility):
    """
    The target is exhausted, and its controller chooses one:
    Fortitude - It is healed 3, and gains 3 stacks of <fortified> for 3 rounds.
    Clarity - It gains 4 energy, which can exceed its max.
    Strength - It gains <supernatural_strength> for 3 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    can_target_self = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent and unit.ready

    def perform(self, target: Unit) -> None:
        ES.resolve(ExhaustUnit(target))
        match GS.make_decision(
            target.controller,
            SelectOptionAtHexDecisionPoint(
                GS.map.hex_off(target),
                ["Fortitude", "Clarity", "Strength"],
                explanation="select wish",
            ),
        ):
            case "Fortitude":
                ES.resolve(
                    ApplyStatus(
                        target,
                        UnitStatusSignature(
                            UnitStatus.get("fortified"), self, stacks=3, duration=3
                        ),
                    )
                )
                ES.resolve(Heal(target, 3))
            case "Clarity":
                ES.resolve(GainEnergy(target, 4, self, allow_overflow=True))
            case "Strength":
                ES.resolve(
                    ApplyStatus(
                        target,
                        UnitStatusSignature(
                            UnitStatus.get("supernatural_strength"), self, duration=3
                        ),
                    )
                )


class InducePanic(TargetUnitActivatedAbility):
    """
    Applies <panicked> for 2 rounds.
    """

    range = 2
    cost = MovementCost(2) | EnergyCost(4)
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Panicked, self, duration=2)))


class Vault(TargetUnitActivatedAbility):
    """
    Moves this unit to the other side of the target. If it did, and the target unit was
    an enemy, apply <staggered> to it.
    """

    cost = MovementCost(1)
    combinable = True
    max_activations = None
    can_target_self = False

    def perform(self, target: Unit) -> None:
        target_position = GS.map.position_off(target)
        difference = target_position - GS.map.position_off(self.parent)
        target_hex = GS.map.hexes.get(target_position + difference)
        if target_hex and target_hex.can_move_into(self.parent):
            if (
                any(
                    e.result
                    for e in ES.resolve(MoveUnit(self.parent, target_hex)).iter_type(
                        MoveUnit
                    )
                )
                and target.controller != self.parent.controller
            ):
                ES.resolve(ApplyStatus(target, UnitStatusSignature(Staggered, self)))


class BatonPass(TargetUnitActivatedAbility):
    """
    Applies <burst_of_speed> to the target unit.
    """

    can_target_self = False
    controller_target_option = ControllerTargetOption.ALLIED

    explain_that_filter = (
        "that wasn't adjacent to this unit at the beginning of this units turn"
    )

    # TODO really ugly
    def __init__(self, owner: Unit):
        super().__init__(owner)

        self.adjacency_hook = AdjacencyHook(self.parent)

    def create_effects(self) -> None:
        self.register_effects(self.adjacency_hook)

    def filter_unit(self, unit: Unit) -> bool:
        return unit not in self.adjacency_hook.adjacent_units

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(BurstOfSpeed, self, stacks=1))
        )


class SweatItOut(TargetUnitActivatedAbility):
    """Dispels all statuses."""

    cost = EnergyCost(3) | MovementCost(2)
    can_target_self = False

    def perform(self, target: Unit) -> None:
        dispel_from_unit(target)


class GuidedTrance(TargetUnitActivatedAbility):
    """Exhausts the target and it gains full energy."""

    cost = EnergyCost(3) | MovementCost(2)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    explain_qualifier_filter = "ready"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.ready

    def perform(self, target: Unit) -> None:
        ES.resolve(ExhaustUnit(target))
        ES.resolve(GainEnergy(target, target.max_energy.g() - target.energy, self))


class SpiritProjection(TargetHexActivatedAbility):
    """
    Apply <glimpse> to the target hex. Then up to 3 times, choose another hex adjacent to the last chosen hex,
    and apply <glimpse> to that as well.
    """

    cost = EnergyCost(3) | ExclusiveCost()
    range = 3
    requires_los = False
    requires_vision = False
    hidden_target = True

    def perform(self, target: Hex) -> None:
        current_hex = target
        ES.resolve(
            ApplyHexStatus(
                current_hex, HexStatusSignature(HexStatus.get("glimpse"), self)
            )
        )
        for _ in range(3):
            decision = GS.make_decision(
                self.parent.controller,
                SelectOptionDecisionPoint(
                    [
                        MoveOption(
                            target_profile=OneOfHexes(
                                list(GS.map.get_neighbors_off(current_hex))
                            )
                        ),
                        SkipOption(target_profile=NoTarget()),
                    ],
                    explanation="spirit walk",
                ),
            )
            if isinstance(decision.option, MoveOption):
                current_hex = decision.target
                ES.resolve(
                    ApplyHexStatus(
                        current_hex, HexStatusSignature(HexStatus.get("glimpse"), self)
                    )
                )
            else:
                break


class SummonScarab(TargetHexActivatedAbility):
    """
    Summons an exhausted Scarab (2 health, 2 speed, 1 armor, 1 sight, S, 2 attack damage with 1 movement cost) with <ephemeral> for 3 rounds.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 3
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["scarab"],
                controller=self.parent.controller,
                space=target,
                exhausted=True,
                with_statuses=[UnitStatusSignature(Ephemeral, self, duration=3)],
            )
        )


class Sweep(TargetHexArcActivatedAbility):
    """
    Deals 4 melee damage to units on hexes.
    """

    cost = MovementCost(1)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(4, self, DamageType.MELEE)))


class Stare(TargetRadiatingLineActivatedAbility):
    """
    Applies <glimpse> to hexes sequentially, starting from the hex closest to this unit, until a hex blocks vision.
    """

    length = 4
    combinable = True
    hidden_target = True

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(ApplyHexStatus(h, HexStatusSignature(Glimpse, self)))
            if is_vision_obstructed_for_unit_at(self.parent, h.position):
                break


class Jaunt(TargetHexActivatedAbility):
    """Moves to the target hex."""

    cost = EnergyCost(3)
    combinable = True
    range = 4
    requires_los = False
    requires_vision = False
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.parent, target))


class Jump(TargetHexActivatedAbility):
    """Moves to the target hex."""

    cost = EnergyCost(2) | ExclusiveCost()
    range = 2
    requires_los = False
    requires_vision = False
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(MoveUnit(self.parent, target))


class PsychicCommand(TargetUnitActivatedAbility):
    """Activates it."""

    cost = EnergyCost(2)
    range = 3
    combinable = True
    can_target_self = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        ES.resolve(QueueUnitForActivation(target))


class Riddle(TargetUnitActivatedAbility):
    """Applies <baffled>."""

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(UnitStatus.get("baffled"), self))
        )


class InstilFocus(TargetUnitActivatedAbility):
    """Applies <focused> for 3 rounds."""

    cost = EnergyCost(2) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, UnitStatusSignature(UnitStatus.get("focused"), self, duration=2)
            )
        )


class SummonBees(TargetHexActivatedAbility):
    cost = MovementCost(2) | EnergyCost(2)
    range = 2
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["bee_swarm"],
                controller=self.parent.controller,
                space=target,
                with_statuses=[UnitStatusSignature(Ephemeral, self, duration=1)],
            )
        )


class StimulatingInjection(TargetUnitActivatedAbility):
    """
    Deals 1 pure damage and readies the target.
    This unit dies.
    """

    cost = EnergyCost(3)
    can_target_self = False

    def can_target_unit(self, unit: Unit) -> bool:
        return unit != self.parent

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.PURE)))
        ES.resolve(ReadyUnit(target))
        # TODO sacrifice as a cost?
        ES.resolve(Kill(self.parent))


class EnfeeblingHex(TargetUnitActivatedAbility):
    """
    Applies <enfeebled> for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(UnitStatus.get("enfeebled"), self, duration=2),
            )
        )


class Suplex(TargetUnitActivatedAbility):
    """
    Deals 3 melee damage, and moves the target to the other side of this unit.
    """

    cost = MovementCost(2) | EnergyCost(3)
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(3, self, DamageType.MELEE)))
        own_position = GS.map.position_off(self.parent)
        if target_hex := GS.map.hexes.get(
            own_position + (own_position - GS.map.position_off(target))
        ):
            ES.resolve(MoveUnit(target, target_hex, external=True))


class Lasso(TargetUnitActivatedAbility):
    """
    Applies <rooted> for 1 round.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Rooted, self, duration=1)))


class Showdown(TargetUnitActivatedAbility):
    """
    This unit hits the target with its primary ranged attack twice.
    If the target isn't exhausted, and it has a primary ranged attack, and it can hit this unit with
    that attack, it does and is exhausted. If it does not have a primary ranged attack, but it has
    a primary melee attack that can hit this unit, it uses that instead.
    """

    cost = ExclusiveCost() | EnergyCost(3)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        if attack := self.parent.get_primary_attack(RangedAttackFacet):
            for _ in range(2):
                ES.resolve(Hit(attacker=self.parent, defender=target, attack=attack))

        if not target.exhausted:
            for attack_type in (RangedAttackFacet, MeleeAttackFacet):
                if (
                    (defender_attack := target.get_primary_attack(attack_type))
                    and self.parent
                    in
                    # TODO yikes
                    defender_attack.get_legal_targets(ActiveUnitContext(target, 1))
                ):
                    ES.resolve(
                        Hit(
                            attacker=target,
                            defender=self.parent,
                            attack=defender_attack,
                        )
                    )
                    ES.resolve(ExhaustUnit(target))
                    break


class RaiseShrine(TargetHexActivatedAbility):
    """
    Applies status <shrine>.
    """

    cost = MovementCost(2) | EnergyCost(3)

    def perform(self, target: Hex) -> None:
        ES.resolve(ApplyHexStatus(target, HexStatusSignature(Shrine, self)))


class GrantCharm(TargetUnitActivatedAbility):
    """
    Applies <lucky_charm> for 3 rounds.
    """

    cost = EnergyCost(2)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(LuckyCharm, self, duration=3))
        )


class ChokingSoot(TargetHexCircleActivatedAbility):
    """
    Applies <soot> to hexes for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(4)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(ApplyHexStatus(_hex, HexStatusSignature(Soot, self, duration=2)))


class SmokeCanister(TargetHexCircleActivatedAbility):
    """
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 3
    combinable = True

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(_hex, HexStatusSignature(Smoke, self, duration=2))
            )


class Terrorize(TargetUnitActivatedAbility):
    """
    Applies <terror> for 2 rounds.
    """

    cost = MovementCost(2) | EnergyCost(5)
    range = 4
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        ES.resolve(ApplyStatus(target, UnitStatusSignature(Terror, self, duration=2)))


class Scorch(TargetHexArcActivatedAbility):
    """
    Deals 3 aoe damage and applies 2 stacks of <burn> to units on hexes.
    """

    cost = MovementCost(1) | EnergyCost(3)

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.AOE)))
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=2)))


class FlameWall(TargetRadiatingLineActivatedAbility):
    """
    Applies 2 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 3 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    length = 4

    def perform(self, target: list[Hex]) -> None:
        for h in target:
            ES.resolve(
                ApplyHexStatus(
                    h,
                    HexStatusSignature(BurningTerrain, self, stacks=1, duration=3),
                )
            )
            if unit := GS.map.unit_on(h):
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=2)))


class FlameThrower(ActivatedAbilityFacet[list[Hex]]):
    """
    Applies 1 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 2 rounds.
    """

    cost = EnergyCost(3)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 1-1-3 arc lengths radiating cone."

    # TODO variable length cone?
    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        return Cone(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
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
            if unit := GS.map.unit_on(h):
                ES.resolve(ApplyStatus(unit, UnitStatusSignature(Burn, self, stacks=1)))


class VitalityTransfusion(ActivatedAbilityFacet[list[Unit]]):
    """
    Transfers health from the second to the first unit.
    Amount transferred is the minimum of 3, how much the recipient is missing, and how much the donor can give without dying.
    """

    cost = MovementCost(1) | EnergyCost(2)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target two allied units within 3 range LoS."

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if (
            len(
                units := find_units_within_range(
                    self.parent, 3, with_controller=ControllerTargetOption.ALLIED
                )
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


class FatalBonding(ActivatedAbilityFacet):
    """
    Target 2 units within 4 range LoS.
    Applies linked <tainted_bond> to both units for 2 rounds.
    """

    cost = EnergyCost(3) | ExclusiveCost()

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target two units within 4 range LoS."

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if len(units := find_units_within_range(self.parent, 4)) >= 2:
            return NOfUnits(units, 2, ["select unit"] * 2)

    def perform(self, target: list[Unit]) -> None:
        # TODO common logic
        if statuses := [
            event.result
            for event in itertools.chain(
                *(
                    ES.resolve(
                        ApplyStatus(
                            unit,
                            UnitStatusSignature(
                                UnitStatus.get("tainted_bond"), self, duration=2
                            ),
                        )
                    ).iter_type(ApplyStatus)
                    for unit in target
                )
            )
            if event.result
            and event.unit in target
            and isinstance(event.result, UnitStatus.get("tainted_bond"))
        ]:
            if len(statuses) == 2:
                TaintedLink(statuses)
            else:
                for status in statuses:
                    status.remove()


class Shove(TargetUnitActivatedAbility):
    """
    Moves target one space away from this unit. If it is staggered, this unit gains 1 movement point.
    """

    cost = MovementCost(1) | EnergyCost(2)
    combinable = True
    can_target_self = False

    def perform(self, target: Unit) -> None:
        target_position = GS.map.position_off(target)
        ES.resolve(
            MoveUnit(
                target,
                GS.map.hexes.get(
                    target_position
                    + (target_position - GS.map.position_off(self.parent))
                ),
                external=True,
            )
        )
        if any(isinstance(status, Staggered) for status in target.statuses):
            ES.resolve(ModifyMovementPoints(self.parent, 1))


class Poof(TargetHexActivatedAbility):
    """Applies Smoke to the current position of this unit for 1 round, and moves this unit to the target hex."""

    cost = EnergyCost(2)
    combinable = True
    requires_los = False
    requires_vision = False
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                GS.map.hex_off(self.parent),
                HexStatusSignature(Smoke, self, duration=1),
            )
        )
        ES.resolve(MoveUnit(self.parent, target))


class VenomousSpine(TargetUnitActivatedAbility):
    """
    Applies <debilitating_venom> for 2 rounds and <parasite>.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(UnitStatus.get("parasite"), self))
        )
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("debilitating_venom"), self, duration=2
                ),
            )
        )


class Scry(TargetHexActivatedAbility):
    """
    Applies <revealed> for 1 round.
    """

    cost = EnergyCost(2)
    range = 6
    requires_los = False
    requires_vision = False
    hidden_target = True

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                target, HexStatusSignature(HexStatus.get("revealed"), self, duration=1)
            )
        )


class ShrinkRay(TargetUnitActivatedAbility):
    """
    Deals 1 ranged damage and applies 1 stack of <shrunk> for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2

    def perform(self, target: Unit) -> None:
        ES.resolve(Damage(target, DamageSignature(1, self, DamageType.RANGED)))
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("shrunk"), self, stacks=1, duration=2
                ),
            )
        )


class AssembleTheDoombot(TargetHexActivatedAbility):
    """
    Applies <doombot_scaffold> to hex.
    If it already has <doombot_scaffold>, instead dispel it, and spawn an exhausted Doombot 3000 with <ephemeral> for 4 rounds.
    """

    cost = ExclusiveCost() | EnergyCost(4)
    requires_empty = True

    def perform(self, target: Hex) -> None:
        if GS.map.unit_on(target):
            return
        if statuses := target.get_statuses(HexStatus.get("doombot_scaffold")):
            for status in statuses:
                ES.resolve(DispelStatus(target, status))
            ES.resolve(
                SpawnUnit(
                    UnitBlueprint.registry["doombot_3000"],
                    self.parent.controller,
                    target,
                    exhausted=True,
                    with_statuses=[
                        UnitStatusSignature(
                            UnitStatus.get("ephemeral"), self, duration=4
                        )
                    ],
                )
            )
        else:
            ES.resolve(
                ApplyHexStatus(
                    target, HexStatusSignature(HexStatus.get("doombot_scaffold"), self)
                )
            )


class Translocate(ActivatedAbilityFacet[list[Unit | Hex]]):
    """
    Moves the unit to the hex.
    """

    cost = EnergyCost(2)
    combinable = True

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target unit within 1 range, and an empty hex adjacent to that unit."

    def get_target_profile(self) -> TargetProfile[list[Unit | Hex]] | None:
        if units := [
            (
                unit,
                TreeNode([(h, None) for h in hexes], "select hex"),
            )
            for unit in find_units_within_range(self.parent, 1)
            if (
                hexes := find_hexs_within_range(
                    unit,
                    1,
                    require_empty=True,
                    vision_for_player=self.parent.controller,
                )
            )
        ]:
            return Tree(TreeNode(units, "select unit"))

    def perform(self, target: list[Hex | Unit]) -> None:
        unit, to_ = target
        ES.resolve(MoveUnit(unit, to_, external=unit != self.parent))


class WringEssence(ActivatedAbilityFacet):
    """
    Spawns an exhausted Blood Homunculus (health 6, speed 2, sight 2, medium, 2 damage 1 movement cost melee attack)
    with 4 health on the selected hex with the same controller as the selected unit.
    If a unit is spawned this way, this ability deals 4 pure damage to the selected unit.
    """

    cost = EnergyCost(3) | MovementCost(1)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target unit within 2 range LoS, and an empty hex adjacent to that unit."

    def get_target_profile(self) -> TargetProfile[list[Unit | Hex]] | None:
        if units := [
            (
                unit,
                TreeNode([(h, None) for h in hexes], "select hex"),
            )
            for unit in find_units_within_range(self.parent, 2)
            if (
                hexes := find_hexs_within_range(
                    unit,
                    1,
                    require_empty=True,
                    vision_for_player=self.parent.controller,
                )
            )
        ]:
            return Tree(TreeNode(units, "select unit"))

    def perform(self, target: list[Hex | Unit]) -> None:
        unit, to_ = target
        if any(
            event.result
            for event in ES.resolve(
                SpawnUnit(
                    UnitBlueprint.get_class("blood_homunculus"),
                    unit.controller,
                    to_,
                    exhausted=True,
                    max_health=4,
                )
            ).iter_type(SpawnUnit)
        ):
            ES.resolve(Damage(unit, DamageSignature(4, self, DamageType.PURE)))


class InkRing(ActivatedAbilityFacet[list[Hex]]):
    """
    Applies <blinded> for 3 rounds.
    """

    cost = EnergyCost(3)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target radius 1 hex ring, center within 3 range NloS."

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if hexes := [
            _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 3)
        ]:
            return HexRing(hexes, 1)

    def perform(self, target: list[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(
                ApplyStatus(
                    unit,
                    UnitStatusSignature(UnitStatus.get("blinded"), self, duration=3),
                )
            )


class MalevolentStare(TargetUnitActivatedAbility):
    """
    Dispels all buffs and applies <silenced> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        dispel_from_unit(target, StatusIntention.BUFF)
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(UnitStatus.get("silenced"), self, duration=2),
            )
        )


class IronBlessing(TargetUnitActivatedAbility):
    """
    Applies <armored> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, UnitStatusSignature(UnitStatus.get("armored"), self, duration=2)
            )
        )


class InternalStruggle(TargetUnitActivatedAbility):
    """
    If the unit has a primary attack, it hits itself with it, otherwise it loses 3 energy.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    requires_los = False

    def perform(self, target: Unit) -> None:
        if attack := target.get_primary_attack():
            ES.resolve(Hit(target, target, attack))
        else:
            ES.resolve(LoseEnergy(target, 3, self))


class Hitch(TargetUnitActivatedAbility):
    """
    Applies <hitched>.
    """

    cost = EnergyCost(3)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    combinable = True

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(target, UnitStatusSignature(UnitStatus.get("hitched"), self))
        )


class CoordinatedManeuver(ActivatedAbilityFacet[list[Unit]]):
    """
    Activates them.
    """

    cost = EnergyCost(3) | MovementCost(1)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 1 or 2 other ready allied units within 3 range LoS."

    def get_target_profile(self) -> TargetProfile[list[Unit]] | None:
        if units := find_units_within_range(
            self.parent,
            3,
            with_controller=ControllerTargetOption.ALLIED,
            can_include_self=False,
            additional_filter=lambda u: u.ready,
        ):
            return NOfUnits(units, 2, ["select target"] * 2, min_count=1)

    def perform(self, target: list[Unit]) -> None:
        for unit in target:
            ES.resolve(QueueUnitForActivation(unit))


class LayMine(TargetHexActivatedAbility):
    """
    Applies <mine>.
    """

    cost = EnergyCost(2) | MovementCost(1)
    combinable = True
    requires_empty = True
    hidden_target = True

    def perform(self, target: Hex) -> None:
        if not GS.map.unit_on(target):
            ES.resolve(
                ApplyHexStatus(target, HexStatusSignature(HexStatus.get("mine"), self))
            )


class TidyUp(TargetHexActivatedAbility):
    """Dispels all hex statuses."""

    cost = EnergyCost(2)

    def perform(self, target: Hex) -> None:
        dispel_all(target)


class Vomit(TargetHexActivatedAbility):
    """
    Deals aoe 5 damage.
    """

    cost = MovementCost(2)
    requires_vision = False
    can_target_self = False

    def perform(self, target: Hex) -> None:
        if unit := GS.map.unit_on(target):
            ES.resolve(Damage(unit, DamageSignature(5, self, DamageType.AOE)))


class SludgeBelch(TargetTriHexActivatedAbility):
    """
    Applies <sludge> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(
                    _hex, HexStatusSignature(HexStatus.get("sludge"), self, duration=2)
                )
            )


class FalseCure(TargetTriHexActivatedAbility):
    """
    Heals units 3 and applies 1 stack of <poison>.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: list[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(Heal(unit, 3))
            ES.resolve(
                ApplyStatus(
                    unit, UnitStatusSignature(UnitStatus.get("poison"), self, stacks=1)
                )
            )


class HandGrenade(TargetTriHexActivatedAbility):
    """
    Deals 3 aoe damage.
    """

    cost = EnergyCost(4) | MovementCost(1)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.AOE)))


class FlashBang(TargetTriHexActivatedAbility):
    """
    Applies <blinded> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                ES.resolve(
                    ApplyStatus(
                        unit,
                        UnitStatusSignature(
                            UnitStatus.get("blinded"), self, duration=2
                        ),
                    )
                )


class SmokeGrenade(TargetTriHexActivatedAbility):
    """
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            ES.resolve(
                ApplyHexStatus(
                    _hex, HexStatusSignature(HexStatus.get("smoke"), self, duration=2)
                )
            )


class SowDiscord(TargetTriHexActivatedAbility):
    """
    Applies <paranoia> for 3 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 4

    def perform(self, target: list[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(
                ApplyStatus(
                    unit,
                    UnitStatusSignature(UnitStatus.get("paranoia"), self, duration=3),
                )
            )


class Scorn(TargetUnitActivatedAbility):
    """
    Applies <dishonorable_coward> for 3 rounds.
    If the target unit stands on an objective captured by its controller, neutralize it.
    """

    cost = EnergyCost(2)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(
                    UnitStatus.get("dishonorable_coward"), self, duration=3
                ),
            )
        )
        # TODO event
        if (
            _hex := GS.map.hex_off(target)
        ).is_objective and _hex.captured_by == target.controller:
            _hex.captured_by = None


class SpurIntoRage(TargetUnitActivatedAbility):
    """
    Applies <senseless_rage> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 2
    can_target_self = False

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target,
                UnitStatusSignature(UnitStatus.get("senseless_rage"), self, duration=2),
            )
        )


class SquirtSoot(TargetHexActivatedAbility):
    """
    Applies <soot> for 2 rounds.
    """

    cost = MovementCost(1)

    def perform(self, target: Hex) -> None:
        ES.resolve(
            ApplyHexStatus(
                target,
                HexStatusSignature(HexStatus.get("soot"), self, duration=2),
            )
        )


class ConstructTurret(TargetHexActivatedAbility):
    """
    Summons an exhausted Sentry Turret with <ephemeral> for 4 rounds.
    """

    cost = MovementCost(2) | EnergyCost(4)
    requires_empty = True

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                UnitBlueprint.get_class("sentry_turret"),
                self.parent.controller,
                target,
                exhausted=True,
                with_statuses=[
                    UnitStatusSignature(UnitStatus.get("ephemeral"), self, duration=4)
                ],
            )
        )


class FixErUp(TargetUnitActivatedAbility):
    """
    Heals 2.
    """

    name = "Fix 'er Up"
    cost = EnergyCost(2) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    explain_with_filter = "with 1 or more base armor or Sentry Turret"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.armor.get_base() > 0 or unit.blueprint == UnitBlueprint.get_class(
            "sentry_turret"
        )

    def perform(self, target: Unit) -> None:
        ES.resolve(Heal(target, 2))


class TurboTune(TargetUnitActivatedAbility):
    """
    Applies <turbo> for 2 rounds.
    """

    cost = EnergyCost(2) | MovementCost(2)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    explain_with_filter = "with 1 or more base armor"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.armor.get_base() > 0

    def perform(self, target: Unit) -> None:
        ES.resolve(
            ApplyStatus(
                target, UnitStatusSignature(UnitStatus.get("turbo"), self, duration=2)
            )
        )


class OpenGate(ActivatedAbilityFacet[list[Hex]]):
    """
    Applies <gate> to both hexes for 3 rounds.
    """

    cost = ExclusiveCost() | EnergyCost(4)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 2 hexes within 3 range NLoS."

    def get_target_profile(self) -> TargetProfile[list[Hex]] | None:
        if (
            len(
                hexes := [
                    _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 3)
                ]
            )
            >= 2
        ):
            return NOfHexes(hexes, 2, ["select hex"] * 2)

    def perform(self, target: list[Hex]) -> None:
        if statuses := [
            result.result
            for result in itertools.chain(
                *(
                    ES.resolve(
                        ApplyHexStatus(
                            hex_,
                            HexStatusSignature(HexStatus.get("gate"), self, duration=3),
                        )
                    ).iter_type(ApplyHexStatus)
                    for hex_ in target
                )
            )
            if result.result
            and result.space in target
            and isinstance(result.result, HexStatus.get("gate"))
        ]:
            if len(statuses) == 2:
                GateLink(statuses)
            else:
                for status in statuses:
                    status.remove()
