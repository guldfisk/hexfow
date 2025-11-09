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
    MovementCost,
    MoveOption,
    NoTarget,
    ObjectListResult,
    OneOfHexes,
    RangedAttackFacet,
    SelectOptionAtHexDecisionPoint,
    SelectOptionDecisionPoint,
    SingleObjectResult,
    SkipOption,
    TargetProfile,
    Terrain,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusSignature,
    find_hexs_within_range,
    find_units_within_range,
    is_vision_obstructed_for_unit_at,
    line_of_sight_obstructed_for_unit,
)
from game.effects.hooks import AdjacencyHook
from game.events import (
    ApplyHexStatus,
    ApplyStatus,
    ChangeHexTerrain,
    CheckAlive,
    Damage,
    DispelStatus,
    ExhaustUnit,
    GainEnergy,
    Heal,
    Hit,
    Kill,
    LoseEnergy,
    ModifyMovementPoints,
    MoveAction,
    MoveUnit,
    NeutralizeObjective,
    QueueUnitForActivation,
    ReadyUnit,
    SpawnUnit,
)
from game.map.terrain import Forest
from game.statuses.links import GateLink, TaintedLink
from game.statuses.shortcuts import (
    apply_status_to_hex,
    apply_status_to_unit,
    dispel_all,
    dispel_from_unit,
)
from game.target_profiles import Cone, NOfHexes, NOfUnits, Tree, TreeNode
from game.targeting import (
    ControllerTargetOption,
    NoTargetActivatedAbility,
    TargetHexActivatedAbility,
    TargetHexArcActivatedAbility,
    TargetHexCircleActivatedAbility,
    TargetHexRingActivatedAbility,
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
            ES.resolve(Heal(unit, 1, self))
        ES.resolve(Kill(self.parent, self))


class Charge(TargetUnitActivatedAbility):
    """
    The target gains 2 energy. This unit dies.
    """

    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(GainEnergy(target.value, 2, self))
        ES.resolve(Kill(self.parent, self))


class PatchUp(TargetUnitActivatedAbility):
    """
    Heals 1.
    """

    cost = EnergyCost(2)
    combinable = True
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 1, self))


class HealBeam(TargetUnitActivatedAbility):
    """
    Heals 2.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    can_target_self = False
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 2, self))


class GreaseTheGears(TargetUnitActivatedAbility):
    """
    Kills the target. If it does, heal this unit 2, and it restores 2 energy.
    If the target unit was ready, this unit gains +1 movement point.
    """

    can_target_self = False
    controller_target_option = ControllerTargetOption.ALLIED
    combinable = True
    max_activations = None

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        movement_bonus = (
            1 if not target.value.exhausted and GS.active_unit_context else 0
        )
        if any(
            kill_event.unit == target
            for kill_event in ES.resolve(Kill(target.value, self)).iter_type(Kill)
        ):
            ES.resolve(Heal(self.parent, 2, self))
            ES.resolve(GainEnergy(self.parent, 2, source=self))
            ES.resolve(ModifyMovementPoints(self.parent, movement_bonus))


class SelfDestruct(NoTargetActivatedAbility):
    """Kills this unit."""

    def perform(self, target: None) -> None:
        ES.resolve(Kill(self.parent, self))


class Explode(NoTargetActivatedAbility):
    """
    This unit deals 4 damage to each adjacent unit. It dies.
    """

    cost = MovementCost(1)

    def perform(self, target: None) -> None:
        for unit in GS.map.get_units_within_range_off(self.parent, 1):
            ES.resolve(
                Damage(
                    unit,
                    DamageSignature(4, self, type=DamageType.PHYSICAL),
                )
            )


class GrantWish(TargetUnitActivatedAbility):
    """
    The target is exhausted, and its controller chooses one:
    Fortitude - It is healed 3, and gains 3 stacks of <fortified> for 3 rounds.
    Clarity - It gains 4 energy, which can exceed its max.
    Strength - It gains <supernatural_strength> for 3 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    can_target_self = False
    explain_qualifier_filter = "ready"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.ready

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(ExhaustUnit(target.value))
        match GS.make_decision(
            target.value.controller,
            SelectOptionAtHexDecisionPoint(
                GS.map.hex_off(target),
                ["Fortitude", "Clarity", "Strength"],
                explanation="select wish",
            ),
        ):
            case "Fortitude":
                apply_status_to_unit(
                    target.value, "fortified", self, stacks=3, duration=3
                )
                ES.resolve(Heal(target.value, 3, self))
            case "Clarity":
                ES.resolve(GainEnergy(target.value, 4, self, allow_overflow=True))
            case "Strength":
                apply_status_to_unit(
                    target.value, "supernatural_strength", self, duration=3
                )


class InducePanic(TargetUnitActivatedAbility):
    """
    Applies <panicked> for 2 rounds.
    """

    range = 2
    cost = MovementCost(2) | EnergyCost(4)
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "panicked", self, duration=2)


class Vault(TargetUnitActivatedAbility):
    """
    Moves this unit to the other side of the target. If it did, and the target unit was
    an enemy, apply <staggered> to it.
    """

    cost = MovementCost(1)
    combinable = True
    max_activations = None
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        target_position = GS.map.position_off(target.value)
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
                and target.value.controller != self.parent.controller
            ):
                apply_status_to_unit(target.value, "staggered", self)


class PublicExecution(TargetUnitActivatedAbility):
    """
    Kills the target. Each allied unit that could see the target unit gains 2 energy.
    """

    cost = ExclusiveCost()
    can_target_self = False
    explain_qualifier_filter = "exhausted"
    explain_with_filter = "with 5 or less health"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.exhausted and unit.health <= 5

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Kill(target.value, self))
        for unit in GS.map.units:
            if unit.controller == self.parent.controller and unit.can_see(
                GS.map.hex_off(target.value)
            ):
                ES.resolve(GainEnergy(unit, 2, self))


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

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "burst_of_speed", self)


class SweatItOut(TargetUnitActivatedAbility):
    """Dispels all statuses."""

    cost = EnergyCost(3) | MovementCost(1)
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        dispel_from_unit(target.value)


class Exorcise(TargetUnitActivatedAbility):
    """
    Deals pure damage equal to the amount of dispelable statuses on the target unit
    to the target unit, then heals it equal to the amount of dispelable buffs,
    then dispels all statuses from it.
    """

    cost = EnergyCost(2) | MovementCost(1)
    range = 2
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(
            Damage(
                target.value,
                DamageSignature(
                    len(
                        [
                            status
                            for status in target.value.statuses
                            if status.intention == StatusIntention.DEBUFF
                            and status.dispellable
                        ]
                    ),
                    self,
                    DamageType.PURE,
                ),
            )
        )
        ES.resolve(
            Heal(
                target.value,
                len(
                    [
                        status
                        for status in target.value.statuses
                        if status.intention == StatusIntention.BUFF
                        and status.dispellable
                    ]
                ),
                self,
            )
        )
        dispel_all(target.value)


class WardEvil(TargetUnitActivatedAbility):
    """
    Applies <magic_ward> for 3 rounds.
    """

    cost = EnergyCost(2) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "magic_ward", self, duration=3)


class WishHarm(TargetUnitActivatedAbility):
    """
    Applies 3 stacks of <frail> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "frail", self, stacks=3, duration=2)


class GuidedTrance(TargetUnitActivatedAbility):
    """Exhausts the target and it gains full energy."""

    cost = EnergyCost(2) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    explain_qualifier_filter = "ready"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.ready

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(ExhaustUnit(target.value))
        ES.resolve(
            GainEnergy(
                target.value, target.value.max_energy.g() - target.value.energy, self
            )
        )


class SpiritProjection(TargetHexActivatedAbility):
    """
    Apply <glimpse> to the target hex. Then up to 2 times, choose another hex adjacent to the last chosen hex,
    and apply <glimpse> to that as well.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3
    requires_los = False
    requires_vision = False
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        current_hex = target.value
        apply_status_to_hex(current_hex, "glimpse", self)
        for _ in range(2):
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
                current_hex = decision.target.value
                apply_status_to_hex(current_hex, "glimpse", self)
            else:
                break


class SummonScarab(TargetHexActivatedAbility):
    """
    Summons an exhausted [scarab] with <ephemeral> for 3 rounds.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 3
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["scarab"],
                controller=self.parent.controller,
                space=target.value,
                exhausted=True,
                with_statuses=[
                    UnitStatusSignature(UnitStatus.get("ephemeral"), self, duration=3)
                ],
            )
        )


class Sweep(TargetHexArcActivatedAbility):
    """
    Deals 4 damage to units on hexes.
    """

    cost = MovementCost(1)

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(4, self, DamageType.PHYSICAL)))


class Stare(TargetRadiatingLineActivatedAbility):
    """
    Applies <glimpse> to hexes sequentially, starting from the hex closest to this unit, until a hex blocks vision.
    """

    length = 4
    combinable = True
    hidden_target = True

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "glimpse", self)
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

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(MoveUnit(self.parent, target.value))


class Jump(TargetHexActivatedAbility):
    """Moves to the target hex."""

    cost = EnergyCost(3) | ExclusiveCost()
    range = 3
    requires_los = False
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(MoveUnit(self.parent, target.value))


class Compel(TargetUnitActivatedAbility):
    """
    Applies <compulsion> for 1 round.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    requires_los = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "compulsion", self, duration=1)


class PsychicCommand(TargetUnitActivatedAbility):
    """Activates it."""

    cost = EnergyCost(2)
    range = 2
    combinable = True
    can_target_self = False
    requires_los = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(QueueUnitForActivation(target.value))


class Baffle(TargetUnitActivatedAbility):
    """Applies <baffled>."""

    cost = EnergyCost(3) | MovementCost(2)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    requires_los = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "baffled", self)


class KarmicJustice(TargetUnitActivatedAbility):
    """
    Applies <karmic_shield> for 1 round.
    """

    cost = EnergyCost(4) | MovementCost(1)
    range = 3
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "karmic_shield", self, duration=1)


class BurnBright(TargetUnitActivatedAbility):
    """
    Sets the target units health to 1, dispel all debuffs and applies <burning_bright>
    for 1 round.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        target.value.damage = target.value.max_health.g() - 1
        dispel_from_unit(target.value, StatusIntention.DEBUFF)
        apply_status_to_unit(target.value, "burning_bright", self, duration=1)


class InstilFocus(TargetUnitActivatedAbility):
    """Applies <focused> for 3 rounds."""

    cost = EnergyCost(2) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "focused", self, duration=3)


class RoyalJelly(TargetUnitActivatedAbility):
    """
    The target unit is healed 1 and gains 1 energy.
    """

    cost = MovementCost(1) | EnergyCost(2)
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 1, self))
        ES.resolve(GainEnergy(target.value, 1, self))


class SummonBees(TargetHexActivatedAbility):
    """
    Spawns a [bee_swarm] with <ephemeral> for 1 round on the target hex.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 2
    requires_los = False
    requires_vision = False
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=UnitBlueprint.registry["bee_swarm"],
                controller=self.parent.controller,
                space=target.value,
                with_statuses=[
                    UnitStatusSignature(UnitStatus.get("ephemeral"), self, duration=1)
                ],
            )
        )


class StimulatingInjection(TargetUnitActivatedAbility):
    """
    Deals 1 pure damage and readies the target.
    This unit dies.
    """

    cost = EnergyCost(3)
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Damage(target.value, DamageSignature(1, self, DamageType.PURE)))
        ES.resolve(ReadyUnit(target.value))
        # TODO sacrifice as a cost?
        ES.resolve(Kill(self.parent, self))


class EnfeeblingHex(TargetUnitActivatedAbility):
    """
    Applies <enfeebled> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "enfeebled", self, duration=2)


class Suplex(TargetUnitActivatedAbility):
    """
    Deals 3 damage, and moves the target to the other side of this unit.
    """

    cost = MovementCost(2) | EnergyCost(3)
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Damage(target.value, DamageSignature(3, self, DamageType.PHYSICAL)))
        own_position = GS.map.position_off(self.parent)
        if target_hex := GS.map.hexes.get(
            own_position + (own_position - GS.map.position_off(target.value))
        ):
            ES.resolve(MoveUnit(target.value, target_hex, external=True))


class Lasso(TargetUnitActivatedAbility):
    """
    Applies <rooted> for 1 round.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    combinable = True

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "rooted", self, duration=1)


class Showdown(TargetUnitActivatedAbility):
    """
    This unit hits the target with its primary ranged attack twice.
    Then, if the target unit is alive and can hit this unit with its primary attack,
    it does so. If it does, and both units are still alive, repeat this process, up to
    5 times total.
    """

    cost = ExclusiveCost() | EnergyCost(3)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        if not (attack := self.parent.get_primary_attack(RangedAttackFacet)):
            return

        for _ in range(5):
            for _ in range(2):
                ES.resolve(
                    Hit(attacker=self.parent, defender=target.value, attack=attack)
                )

            ES.resolve(CheckAlive(target.value))
            if not target.value.on_map():
                break

            if not (
                (defender_attack := target.value.get_primary_attack())
                and self.parent
                in defender_attack.get_legal_targets(ActiveUnitContext(target.value, 1))
            ):
                break

            ES.resolve(
                Hit(
                    attacker=target.value,
                    defender=self.parent,
                    attack=defender_attack,
                )
            )

            ES.resolve(CheckAlive(self.parent))
            if not self.parent.on_map():
                break


class BallMode(NoTargetActivatedAbility):
    """
    Applies status <rolling> to this unit.
    """

    cost = ExclusiveCost()

    def perform(self, target: None) -> None:
        apply_status_to_unit(self.parent, "rolling", self)


class RaiseShrine(TargetHexActivatedAbility):
    """
    Applies status <shrine>.
    """

    cost = MovementCost(2) | EnergyCost(3)

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "shrine", self)


class GrantCharm(TargetUnitActivatedAbility):
    """
    Applies <lucky_charm> for 3 rounds.
    """

    cost = EnergyCost(2)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "lucky_charm", self, duration=3)


class ChokingSoot(TargetHexCircleActivatedAbility):
    """
    Applies <soot> to hexes for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(4)
    range = 2

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "soot", self, duration=2)


class SmokeCanister(TargetHexCircleActivatedAbility):
    """
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 3
    combinable = True

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "smoke", self, duration=2)


class Terrorize(TargetUnitActivatedAbility):
    """
    Applies <terror> for 2 rounds.
    """

    cost = MovementCost(2) | EnergyCost(5)
    range = 4
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "terror", self, duration=2)


class RollUp(NoTargetActivatedAbility):
    """Applies <rolled_up> to this unit."""

    cost = MovementCost(1)

    def perform(self, target: None) -> None:
        apply_status_to_unit(self.parent, "rolled_up", self)


class InkScreen(TargetHexArcActivatedAbility):
    """
    Applies <ink_cloud> for 2 rounds to the target hexes.
    """

    cost = EnergyCost(3) | MovementCost(1)

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "ink_cloud", self, duration=2)


class Scorch(TargetHexArcActivatedAbility):
    """
    Deals 3 damage and applies 2 stacks of <burn> to units on hexes.
    """

    cost = MovementCost(1) | EnergyCost(3)

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.PHYSICAL)))
                apply_status_to_unit(unit, "burn", self, stacks=2)


class FlameWall(TargetRadiatingLineActivatedAbility):
    """
    Applies 2 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 3 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    length = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "burning_terrain", self, stacks=1, duration=3)
            if unit := GS.map.unit_on(h):
                apply_status_to_unit(unit, "burn", self, stacks=2)


class FlameThrower(ActivatedAbilityFacet[ObjectListResult[Hex]]):
    """
    Applies 1 stacks of <burn> to each unit on hexes, and 1 stack of <burning_terrain> to the hex for 2 rounds.
    """

    cost = EnergyCost(3)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 1-1-3 arc lengths radiating cone."

    # TODO variable length cone?
    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        return Cone(
            GS.map.hex_off(self.parent),
            list(GS.map.get_neighbors_off(self.parent)),
            [0, 0, 1],
        )

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "burning_terrain", self, stacks=1, duration=2)
            if unit := GS.map.unit_on(h):
                apply_status_to_unit(unit, "burn", self, stacks=1)


class VitalityTransfusion(ActivatedAbilityFacet[ObjectListResult[Unit]]):
    """
    Transfers health from the second to the first unit.
    Amount transferred is the minimum of 2, how much the recipient is missing, and how much the donor can give without dying.
    """

    cost = MovementCost(1) | EnergyCost(2)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target two other allied units within 3 range LoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Unit]] | None:
        if (
            len(
                units := find_units_within_range(
                    self.parent,
                    3,
                    with_controller=ControllerTargetOption.ALLIED,
                    can_include_self=False,
                )
            )
            >= 2
        ):
            return NOfUnits(units, 2, ["select recipient", "select donor"])

    def perform(self, target: ObjectListResult[Unit]) -> None:
        recipient, donor = target.values
        available_health = min(donor.health - 1, recipient.damage, 2)
        if available_health:
            # TODO yikes should be an event, but unclear what it should be,
            #  since we don't want it to be damage i think.
            donor.damage += available_health
            ES.resolve(Heal(recipient, available_health, self))


class ForcedMarch(TargetUnitActivatedAbility):
    """
    You may take one move action with the targeted unit.
    """

    cost = EnergyCost(2)
    range = 3
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        if moveable_hexes := target.value.get_potential_move_destinations(None):
            decision = GS.make_decision(
                self.parent.controller,
                SelectOptionDecisionPoint(
                    [
                        MoveOption(
                            target_profile=OneOfHexes(
                                moveable_hexes + [GS.map.hex_off(target)]
                            )
                        ),
                        SkipOption(target_profile=NoTarget()),
                    ],
                    explanation="quick",
                ),
            )
            if isinstance(
                decision.option, MoveOption
            ) and decision.target.value != GS.map.hex_off(target):
                ES.resolve(MoveAction(target.value, to_=decision.target.value))


class FatalBonding(ActivatedAbilityFacet[ObjectListResult[Unit]]):
    """
    Applies linked <tainted_bond> to the target units for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 2 or 3 units within 4 range LoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Unit]] | None:
        if len(units := find_units_within_range(self.parent, 4)) >= 2:
            return NOfUnits(units, 3, ["select unit"] * 3, min_count=2)

    def perform(self, target: ObjectListResult[Unit]) -> None:
        if statuses := [
            event.result
            for event in itertools.chain(
                *(
                    apply_status_to_unit(
                        unit, "tainted_bond", self, duration=2
                    ).iter_type(ApplyStatus)
                    for unit in target
                )
            )
            if event.result
            and event.unit in target
            and isinstance(event.result, UnitStatus.get("tainted_bond"))
        ]:
            TaintedLink(statuses)


class PrepareTrap(TargetHexActivatedAbility):
    """
    Applies <bear_trap> to the target hex.
    """

    cost = MovementCost(1) | EnergyCost(3)
    combinable = True
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "bear_trap", self)


class MountCharge(TargetHexActivatedAbility):
    """
    Applies <timed_demo_charge> for 2 rounds to the target hex.
    """

    cost = MovementCost(1) | EnergyCost(2)
    combinable = True
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "timed_demo_charge", self, duration=2)


class Zap(TargetUnitActivatedAbility):
    """
    The target loses 3 energy.
    """

    cost = EnergyCost(2)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(LoseEnergy(target.value, 3, self))


class Shove(TargetUnitActivatedAbility):
    """
    Moves target one space away from this unit. If it is staggered, this unit gains 1 movement point.
    """

    cost = MovementCost(1) | EnergyCost(2)
    combinable = True
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        target_position = GS.map.position_off(target)
        ES.resolve(
            MoveUnit(
                target.value,
                GS.map.hexes.get(
                    target_position
                    + (target_position - GS.map.position_off(self.parent))
                ),
                external=True,
            )
        )
        if target.value.has_status("staggered"):
            ES.resolve(ModifyMovementPoints(self.parent, 1))


class Poof(TargetHexActivatedAbility):
    """Applies Smoke to the current position of this unit for 1 round, and moves this unit to the target hex."""

    cost = EnergyCost(2)
    combinable = True
    requires_los = False
    requires_vision = False
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(GS.map.hex_off(self.parent), "smoke", self, duration=1)
        ES.resolve(MoveUnit(self.parent, target.value))


class VenomousSpine(TargetUnitActivatedAbility):
    """
    Applies <debilitating_venom> for 2 rounds and <parasite>.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY
    combinable = True

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "parasite", self)
        apply_status_to_unit(target.value, "debilitating_venom", self, duration=2)


class HealingPotion(TargetUnitActivatedAbility):
    """
    Heals 1 and applies <regenerating> for 3 rounds.
    """

    cost = EnergyCost(2) | MovementCost(2)
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 1, self))
        apply_status_to_unit(target.value, "regenerating", self, duration=3)


class NaturalBlessing(TargetUnitActivatedAbility):
    """
    Applies <natures_grace> for 3 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "natures_grace", self, duration=3)


class VerdantFlash(TargetHexActivatedAbility):
    """
    Turns the terrain into Forest.
    """

    cost = EnergyCost(3) | MovementCost(1)

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(ChangeHexTerrain(target.value, Terrain.get_class("forest")))


class RaiseGround(TargetHexActivatedAbility):
    """
    Turns the terrain into Hills.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    explain_qualifier_filter = "non-elevated"

    def filter_hex(self, hex_: Hex) -> bool:
        return not hex_.terrain.is_high_ground

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(ChangeHexTerrain(target.value, Terrain.get_class("hills")))


class FlattenGround(TargetHexActivatedAbility):
    """Turns the terrain into Plains"""

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    explain_qualifier_filter = "elevated"

    def filter_hex(self, hex_: Hex) -> bool:
        return hex_.terrain.is_high_ground

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(ChangeHexTerrain(target.value, Terrain.get_class("plains")))


class DrawSpring(TargetHexActivatedAbility):
    """
    Applies <underground_spring> for 2 rounds.
    """

    cost = EnergyCost(2) | MovementCost(1)
    range = 3

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "underground_spring", self, duration=2)


class MagmaFissure(TargetHexActivatedAbility):
    """
    Applies 2 stacks of <burning_terrain>.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "burning_terrain", self, stacks=2)


class Scry(TargetHexActivatedAbility):
    """
    Applies <revealed> for 2 rounds.
    """

    cost = EnergyCost(2)
    range = 6
    requires_los = False
    requires_vision = False
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "revealed", self, duration=2)


class ShrinkRay(TargetUnitActivatedAbility):
    """
    Deals 1 damage and applies 1 stack of <shrunk> for 2 rounds.
    """

    cost = MovementCost(1) | EnergyCost(3)
    range = 2

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Damage(target.value, DamageSignature(1, self, DamageType.PHYSICAL)))
        apply_status_to_unit(target.value, "shrunk", self, stacks=1, duration=2)


class MagicMissile(TargetUnitActivatedAbility):
    """
    Deals 2 damage.
    """

    cost = EnergyCost(2) | MovementCost(1)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Damage(target.value, DamageSignature(2, self)))


class MagicShield(TargetUnitActivatedAbility):
    """
    Applies 2 stacks of <shield>.
    """

    cost = EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "shield", self, stacks=2)


class AssembleTheDoombot(TargetHexActivatedAbility):
    """
    Applies <doombot_scaffold> to hex.
    If it already has <doombot_scaffold>, instead dispel it, and spawn an exhausted [doombot_3000] with <ephemeral> for 4 rounds.
    """

    cost = ExclusiveCost() | EnergyCost(4)
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        if GS.map.unit_on(target.value):
            return
        if statuses := target.value.get_statuses(HexStatus.get("doombot_scaffold")):
            for status in statuses:
                ES.resolve(DispelStatus(target.value, status))
            ES.resolve(
                SpawnUnit(
                    UnitBlueprint.registry["doombot_3000"],
                    self.parent.controller,
                    target.value,
                    exhausted=True,
                    with_statuses=[
                        UnitStatusSignature(
                            UnitStatus.get("ephemeral"), self, duration=4
                        )
                    ],
                )
            )
        else:
            apply_status_to_hex(target.value, "doombot_scaffold", self)


class Translocate(ActivatedAbilityFacet[ObjectListResult[Unit | Hex]]):
    """
    Moves the unit to the hex.
    """

    cost = EnergyCost(2)
    combinable = True

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target unit within 1 range, and an empty hex adjacent to that unit."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Unit | Hex]] | None:
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

    def perform(self, target: ObjectListResult[Hex | Unit]) -> None:
        unit, to_ = target
        ES.resolve(MoveUnit(unit, to_, external=unit != self.parent))


class WringEssence(ActivatedAbilityFacet[ObjectListResult[Unit | Hex]]):
    """
    Spawns an exhausted [blood_homunculus] with 4 health on the selected hex with the same controller as the selected unit.
    If a unit is spawned this way, this ability deals 4 pure damage to the selected unit.
    """

    cost = EnergyCost(3) | MovementCost(1)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target unit within 2 range LoS, and an empty hex adjacent to that unit."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Unit | Hex]] | None:
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

    def perform(self, target: ObjectListResult[Hex | Unit]) -> None:
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


class InkRing(TargetHexRingActivatedAbility):
    """
    Applies <blinded> for 3 rounds.
    """

    cost = EnergyCost(3)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            apply_status_to_unit(unit, "blinded", self, duration=3)


class MalevolentStare(TargetUnitActivatedAbility):
    """
    Dispels all buffs and applies <silenced> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(2)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        dispel_from_unit(target.value, StatusIntention.BUFF)
        apply_status_to_unit(target.value, "silenced", self, duration=2)


class HelpfulWatchers(TargetHexActivatedAbility):
    """
    If the target is a Forest, apply <revealed> for 3 rounds.
    """

    cost = EnergyCost(1)
    range = 2
    requires_los = False
    requires_vision = False
    hidden_target = True

    def filter_hex(self, hex_: Hex) -> bool:
        return isinstance(hex_.terrain, Forest) or not hex_.is_visible_to(
            self.parent.controller
        )

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        if isinstance(target.value.terrain, Forest):
            apply_status_to_hex(target.value, "revealed", self, duration=3)


class IronBlessing(TargetUnitActivatedAbility):
    """
    Applies <armored> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    combinable = True
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "armored", self, duration=2)


class StopHittingYourself(TargetUnitActivatedAbility):
    """
    The target unit hits itself with its own primary attack.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        if attack := target.value.get_primary_attack():
            ES.resolve(Hit(target.value, target.value, attack))


class Hitch(TargetUnitActivatedAbility):
    """
    Applies <hitched>.
    """

    cost = EnergyCost(3)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False
    combinable = True

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "hitched", self)


class CoordinatedManeuver(TargetUnitActivatedAbility):
    """
    Activates it.
    """

    cost = EnergyCost(2) | MovementCost(1)
    combinable = True
    range = 3
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(QueueUnitForActivation(target.value))


class LayMine(TargetHexActivatedAbility):
    """
    Applies <mine>.
    """

    cost = EnergyCost(2) | MovementCost(1)
    combinable = True
    max_activations = 2
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "mine", self)


class TidyUp(TargetHexActivatedAbility):
    """Dispels all hex statuses."""

    cost = EnergyCost(2)

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        dispel_all(target.value)


class Vomit(TargetHexActivatedAbility):
    """
    Deals 5 damage.
    """

    cost = MovementCost(2)
    requires_vision = False
    can_target_self = False

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        if unit := GS.map.unit_on(target.value):
            ES.resolve(Damage(unit, DamageSignature(5, self, DamageType.PHYSICAL)))


class Mortar(TargetHexActivatedAbility):
    """Deals 3 damage to any unit on the target hex."""

    cost = ExclusiveCost()
    range = 3
    requires_los = False
    requires_vision = False
    explain_that_filter = "and at least 2 hexes away"

    def filter_hex(self, hex_: Hex) -> bool:
        return GS.map.distance_between(hex_, self.parent) > 1

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        if unit := GS.map.unit_on(target.value):
            ES.resolve(Damage(unit, DamageSignature(3, self, DamageType.PHYSICAL)))


class Binoculars(TargetHexActivatedAbility):
    """
    If this unit has LoS to the target hex, apply <revealed> for 2 rounds.
    """

    cost = ExclusiveCost()
    range = 4
    requires_vision = False
    requires_los = False

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        if not line_of_sight_obstructed_for_unit(
            self.parent,
            GS.map.position_off(self.parent),
            target.value.position,
        ):
            apply_status_to_hex(target.value, "revealed", self, duration=2)


class MapOut(TargetHexActivatedAbility):
    """
    Applies <mapped_out>.
    """

    cost = EnergyCost(2)
    hidden_target = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "mapped_out", self)


class ShootFlare(TargetTriHexActivatedAbility):
    """
    Applies <flare> for 1 round.
    """

    cost = EnergyCost(3)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "flare", self, duration=1)


class SludgeBelch(TargetTriHexActivatedAbility):
    """
    Applies <sludge> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "sludge", self, duration=2)


class FalseCure(TargetTriHexActivatedAbility):
    """
    Heals units 3 and applies 1 stack of <poison>.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            ES.resolve(Heal(unit, 3, self))
            apply_status_to_unit(unit, "poison", self, stacks=1)


class HandGrenade(TargetTriHexActivatedAbility):
    """
    Deals 2 damage.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                ES.resolve(Damage(unit, DamageSignature(2, self, DamageType.PHYSICAL)))


class FlashBang(TargetTriHexActivatedAbility):
    """
    Applies <blinded> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for _hex in target:
            if unit := GS.map.unit_on(_hex):
                apply_status_to_unit(unit, "blinded", self, duration=2)


class SmokeGrenade(TargetTriHexActivatedAbility):
    """
    Applies <smoke> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "smoke", self, duration=2)


class WildernessGuide(TargetUnitActivatedAbility):
    """
    Applies <pathfinding> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "pathfinding", self, duration=2)


class Camouflage(TargetUnitActivatedAbility):
    """
    Applies <camouflaged>.
    """

    cost = EnergyCost(3) | MovementCost(2)
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "camouflaged", self)


class AwarenessMentor(TargetUnitActivatedAbility):
    """
    Applies <keen_vision> for 1 round.
    """

    cost = EnergyCost(3)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "keen_vision", self, duration=1)


class IcicleSplinter(TargetUnitActivatedAbility):
    """
    Applies 3 stacks of <frail> for 2 rounds and 4 stacks of <frigid> for 2 rounds.
    """

    cost = EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "frail", self, stacks=3, duration=2)
        apply_status_to_unit(target.value, "frigid", self, stacks=4, duration=2)


class ShieldWithFrost(TargetUnitActivatedAbility):
    """
    Applies <frost_shield> for 2 rounds.
    """

    cost = EnergyCost(4) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "frost_shield", self, duration=2)


class RingOfIce(TargetHexRingActivatedAbility):
    """
    Deals 2 damage to other units on the target hexes and applies <chill> for 3 rounds.
    """

    cost = EnergyCost(4) | MovementCost(1)
    range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            if unit != self.parent:
                ES.resolve(Damage(unit, DamageSignature(2, self, DamageType.PHYSICAL)))
                apply_status_to_unit(unit, "chill", self, duration=3)


class SowDiscord(TargetTriHexActivatedAbility):
    """
    Applies <paranoia> for 3 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 4

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            apply_status_to_unit(unit, "paranoia", self, duration=3)


class Scorn(TargetUnitActivatedAbility):
    """
    Applies <dishonorable_coward> for 3 rounds.
    If the target unit stands on an objective captured by its controller, neutralize it.
    """

    cost = EnergyCost(3)
    range = 2
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "dishonorable_coward", self, duration=3)
        if (
            _hex := GS.map.hex_off(target.value)
        ).is_objective and _hex.captured_by == target.value.controller:
            ES.resolve(NeutralizeObjective(_hex, self))


class SpurIntoRage(TargetUnitActivatedAbility):
    """
    Applies <senseless_rage> for 2 rounds.
    """

    cost = EnergyCost(2) | MovementCost(1)
    range = 3
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "senseless_rage", self, duration=2)


class SquirtSoot(TargetHexActivatedAbility):
    """
    Applies <soot> for 2 rounds.
    """

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "soot", self, duration=2)


class ConstructTurret(TargetHexActivatedAbility):
    """
    Summons an exhausted [sentry_turret] with <ephemeral> for 4 rounds.
    """

    cost = MovementCost(2) | EnergyCost(4)
    requires_empty = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(
            SpawnUnit(
                UnitBlueprint.get_class("sentry_turret"),
                self.parent.controller,
                target.value,
                exhausted=True,
                with_statuses=[
                    UnitStatusSignature(UnitStatus.get("ephemeral"), self, duration=4)
                ],
            )
        )


class FixErUp(TargetUnitActivatedAbility):
    """
    Heals 2. If it's a [sentry_turret], also resets its <ephemeral> status to 4 rounds.
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

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 2, self))
        if target.value.blueprint == UnitBlueprint.get_class("sentry_turret"):
            for status in target.value.get_statuses(UnitStatus.get("ephemeral")):
                status.duration = 4


class TurboTune(TargetUnitActivatedAbility):
    """
    Applies <turbo> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "turbo", self, duration=2)


class TurnToRabbit(TargetUnitActivatedAbility):
    """
    Applies <critterized> for 1 round.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "critterized", self, duration=1)


class TugIn(TargetUnitActivatedAbility):
    """
    Applies <beauty_sleep> for 1 round.
    """

    cost = EnergyCost(4) | MovementCost(1)
    can_target_self = False
    explain_qualifier_filter = "ready"

    def filter_unit(self, unit: Unit) -> bool:
        return unit.ready

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "beauty_sleep", self, duration=1)


class FaerieDust(TargetUnitActivatedAbility):
    """
    Applies <magic_strength> for 1 round.
    """

    cost = EnergyCost(2)
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "magic_strength", self, duration=1)


class FleaSwarm(TargetUnitActivatedAbility):
    """
    Applies <flea_infested> for 3 rounds.
    """

    cost = EnergyCost(4) | MovementCost(1)
    range = 3
    controller_target_option = ControllerTargetOption.ENEMY

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "flea_infested", self, duration=3)


class SpawnBrood(TargetHexActivatedAbility):
    """
    Spawns an exhausted [horror_spawn].
    """

    cost = EnergyCost(3) | MovementCost(1)

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        ES.resolve(
            SpawnUnit(
                UnitBlueprint.get_class("horror_spawn"),
                self.parent.controller,
                target.value,
                exhausted=True,
            )
        )


class Disempower(TargetTriHexActivatedAbility):
    """
    Applies <sapped> for 1 round.
    """

    cost = EnergyCost(2)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            apply_status_to_unit(unit, "sapped", self, duration=1)


class TorporFumes(TargetTriHexActivatedAbility):
    """
    Applies 2 stacks of <tired> to units on target hexes.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for unit in GS.map.units_on(target):
            apply_status_to_unit(unit, "tired", self, stacks=2)


class Pummel(TargetHexActivatedAbility):
    """
    Applies 2 stacks of <incoming> for 1 round.
    """

    cost = ExclusiveCost() | EnergyCost(3)
    range = 6
    min_range = 2
    requires_vision = False
    requires_los = False

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "incoming", self, stacks=2, duration=1)


class Bombard(TargetTriHexActivatedAbility):
    """
    Applies 1 stacks of <incoming> for 1 round.
    """

    cost = ExclusiveCost() | EnergyCost(2)
    range = 7
    min_range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "incoming", self, stacks=1, duration=1)


class OrbitalStrike(TargetTriHexActivatedAbility):
    """
    Applies 4 stacks of <incoming> for 2 rounds.
    """

    cost = MovementCost(2) | EnergyCost(3)
    range = 5

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "incoming", self, stacks=4, duration=2)


class SpySatellite(TargetTriHexActivatedAbility):
    """
    Applies <revealed> for 1 round.
    """

    cost = MovementCost(2) | EnergyCost(2)
    range = 5

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "revealed", self, duration=1)


class FireStorm(TargetTriHexActivatedAbility):
    """
    For each target hex, if it has <burning_terrain>, apply 2 stacks of <burning_terrain> for 2 rounds, and 2 <burn> to any
    unit on it, otherwise apply 1 stack of those statuses.
    """

    cost = EnergyCost(3) | ExclusiveCost()
    range = 4
    min_range = 2

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(
                h,
                "burning_terrain",
                self,
                stacks=(
                    2
                    if (is_burning := h.has_status(HexStatus.get("burning_terrain")))
                    else 1
                ),
                duration=2,
            )
            if unit := GS.map.unit_on(h):
                apply_status_to_unit(unit, "burn", self, stacks=2 if is_burning else 1)


class GiantPincers(ActivatedAbilityFacet[ObjectListResult[Hex]]):
    """Deals 5 + attack power damage to units on the target hexes."""

    cost = MovementCost(1)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target two visible hexes adjacent to this unit, with one hex also adjacent to this unit between them."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        # TODO edge??
        if (
            len(
                hexes := [
                    h
                    for h in GS.map.get_neighbors_off(self.parent)
                    if h.is_visible_to(self.parent.controller)
                ]
            )
            >= 2
        ):
            return Tree(
                TreeNode(
                    [
                        (
                            _hex,
                            TreeNode(
                                [
                                    (hexes[(idx + offset) % len(hexes)], None)
                                    for offset in (-2, 2)
                                ],
                                "select second hex",
                            ),
                        )
                        for idx, _hex in enumerate(hexes)
                    ],
                    "select first hex",
                )
            )

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            if unit := GS.map.unit_on(h):
                ES.resolve(
                    Damage(
                        unit,
                        DamageSignature(
                            5 + self.parent.attack_power.g(), self, DamageType.PHYSICAL
                        ),
                    )
                )


class Evacuate(ActivatedAbilityFacet[ObjectListResult[Unit | Hex]]):
    """
    Teleports the target unit to the target hex, then exhausts it.
    """

    cost = EnergyCost(2) | ExclusiveCost()

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target other allied unit within 4 range NLoS, and an empty hex adjacent to this unit."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Unit | Hex]] | None:
        if (hexes := find_hexs_within_range(self.parent, 1, require_empty=True)) and (
            units := [
                (
                    unit,
                    TreeNode([(h, None) for h in hexes], "select hex"),
                )
                for unit in find_units_within_range(
                    self.parent,
                    4,
                    require_los=False,
                    with_controller=ControllerTargetOption.ALLIED,
                    can_include_self=False,
                )
            ]
        ):
            return Tree(TreeNode(units, "select unit"))

    def perform(self, target: ObjectListResult[Hex | Unit]) -> None:
        unit, to_ = target
        ES.resolve(MoveUnit(unit, to_, external=True))
        ES.resolve(ExhaustUnit(unit))


class CriticalAid(TargetUnitActivatedAbility):
    """
    Heals the target unit to 4 health.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 2
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        ES.resolve(Heal(target.value, 4 - target.value.health, self))


class GasGrenade(TargetTriHexActivatedAbility):
    """
    Applies <trench_gas> for 2 rounds.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3

    def perform(self, target: ObjectListResult[Hex]) -> None:
        for h in target:
            apply_status_to_hex(h, "trench_gas", self, duration=2)


class DeployStakes(TargetHexActivatedAbility):
    """
    Applies <stakes>.
    """

    cost = EnergyCost(1)
    combinable = True

    def perform(self, target: SingleObjectResult[Hex]) -> None:
        apply_status_to_hex(target.value, "stakes", self)


class Sandbags(TargetUnitActivatedAbility):
    """
    Applies <dug_in>.
    """

    cost = EnergyCost(3) | MovementCost(2)

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "dug_in", self)


class CuringWord(TargetUnitActivatedAbility):
    """
    Dispels one debuff.
    """

    cost = EnergyCost(3) | MovementCost(1)
    range = 3
    controller_target_option = ControllerTargetOption.ALLIED
    can_target_self = False

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        if available_options := [
            status
            for status in target.value.statuses
            if status.intention == StatusIntention.DEBUFF and status.dispellable
        ]:
            # TODO can be auto resolved choice logic
            if len(available_options) == 1:
                choice = available_options[0]
            else:
                # TODO mapping support in SelectOptionAtHexDecisionPoint
                name_map = {status.name: status for status in available_options}
                choice = name_map[
                    GS.make_decision(
                        target.value.controller,
                        SelectOptionAtHexDecisionPoint(
                            GS.map.hex_off(target),
                            list(name_map.keys()),
                            explanation="select debuff",
                        ),
                    )
                ]
            ES.resolve(DispelStatus(target.value, choice))


class OpenGate(ActivatedAbilityFacet[ObjectListResult[Hex]]):
    """
    Applies <gate> to both hexes for 3 rounds.
    """

    cost = ExclusiveCost() | EnergyCost(4)

    @classmethod
    def get_target_explanation(cls) -> str | None:
        return "Target 2 hexes within 3 range NLoS."

    def get_target_profile(self) -> TargetProfile[ObjectListResult[Hex]] | None:
        if (
            len(
                hexes := [
                    _hex for _hex in GS.map.get_hexes_within_range_off(self.parent, 3)
                ]
            )
            >= 2
        ):
            return NOfHexes(hexes, 2, ["select hex"] * 2)

    def perform(self, target: ObjectListResult[Hex]) -> None:
        if statuses := [
            result.result
            for result in itertools.chain(
                *(
                    apply_status_to_hex(hex_, "gate", self, duration=3).iter_type(
                        ApplyHexStatus
                    )
                    for hex_ in target.values
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


class ForetellDemise(TargetUnitActivatedAbility):
    """
    Applies <inevitable_death> for 2 rounds.
    """

    cost = EnergyCost(7)
    range = 1

    def perform(self, target: SingleObjectResult[Unit]) -> None:
        apply_status_to_unit(target.value, "inevitable_death", self, duration=2)


class AVisionOfDoom(TargetHexCircleActivatedAbility):
    """
    Applies <impending_doom> for 2 rounds.
    """

    cost = EnergyCost(7)
    range = 1

    def perform(self, target: list[Hex]) -> None:
        for _hex in target:
            apply_status_to_hex(_hex, "impending_doom", self, duration=2)
