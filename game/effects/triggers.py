import dataclasses
from enum import IntEnum, auto
from typing import Callable, ClassVar

from events.eventsystem import ES, TriggerEffect, hook_on
from game.core import (
    GS,
    ActiveUnitContext,
    DamageSignature,
    EnergyCost,
    Hex,
    HexStatus,
    HexStatusSignature,
    MeleeAttackFacet,
    MoveOption,
    NoTarget,
    OneOfHexes,
    Player,
    SelectOptionDecisionPoint,
    SkipOption,
    Source,
    Status,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusLink,
    UnitStatusSignature,
    get_source_unit,
)
from game.events import (
    ActionCleanup,
    ActionUpkeep,
    ActivateAbilityAction,
    ApplyHexStatus,
    ApplyStatus,
    Damage,
    ExhaustUnit,
    GainEnergy,
    Heal,
    Hit,
    Kill,
    KillUpkeep,
    MeleeAttackAction,
    ModifyMovementPoints,
    MoveAction,
    MoveUnit,
    ReadyUnit,
    ReceiveDamage,
    Rest,
    RoundCleanup,
    RoundUpkeep,
    SpawnUnit,
    SufferDamage,
    Turn,
    TurnCleanup,
    TurnUpkeep,
)
from game.statuses.shortcuts import apply_status_to_hex, apply_status_to_unit
from game.values import DamageType, StatusIntention


class TriggerLayers(IntEnum):
    ROUND_STATUSES_TICK = auto()
    ROUND_HEAL_TICK = auto()
    PANIC = auto()
    ROUND_APPLY_DEBUFFS = auto()
    FLEETING = auto()

    TIRED = auto()
    OLD_BONES = auto()

    READY = auto()
    EXHAUST = auto()


@dataclasses.dataclass(eq=False)
class PricklyTrigger(TriggerEffect[Hit]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    amount: int

    def should_trigger(self, event: Hit) -> bool:
        return event.defender == self.unit and isinstance(
            event.attack, MeleeAttackFacet
        )

    def resolve(self, event: Hit) -> None:
        ES.resolve(Damage(event.attacker, DamageSignature(self.amount, self.source)))


@dataclasses.dataclass(eq=False)
class DebuffOnMeleeAttackTrigger(TriggerEffect[Hit]):
    priority: ClassVar[int] = 0

    unit: Unit
    signature: UnitStatusSignature

    def should_trigger(self, event: Hit) -> bool:
        return event.defender == self.unit and isinstance(
            event.attack, MeleeAttackFacet
        )

    def resolve(self, event: Hit) -> None:
        ES.resolve(ApplyStatus(event.attacker, self.signature))


@dataclasses.dataclass(eq=False)
class PackHunterTrigger(TriggerEffect[MeleeAttackAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MeleeAttackAction) -> bool:
        return (
            event.defender.controller != self.unit.controller
            and event.attacker != self.unit
            # TODO really awkward having to be defensive about this here, maybe
            #  good argument for triggers being queued before event execution?
            and event.defender.on_map()
            and GS.map.distance_between(self.unit, event.defender) <= 1
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        if attack := self.unit.get_primary_attack(MeleeAttackFacet):
            ES.resolve(Hit(attacker=self.unit, defender=event.defender, attack=attack))


@dataclasses.dataclass(eq=False)
class FuriousTrigger(TriggerEffect[Hit]):
    priority: ClassVar[int] = TriggerLayers.READY

    unit: Unit

    def should_trigger(self, event: Hit) -> bool:
        return event.defender == self.unit

    def resolve(self, event: Hit) -> None:
        ES.resolve(ReadyUnit(self.unit))


@dataclasses.dataclass(eq=False)
class ExplosiveTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    damage: int

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.unit

    def resolve(self, event: KillUpkeep) -> None:
        for unit in GS.map.get_units_within_range_off(self.unit, 1):
            ES.resolve(
                Damage(
                    unit, DamageSignature(self.damage, self.source, type=DamageType.AOE)
                )
            )


@dataclasses.dataclass(eq=False)
class SchadenfreudeDamageTrigger(TriggerEffect[Damage]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: Damage) -> bool:
        return (
            event.unit != self.unit
            and GS.map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: Damage) -> None:
        ES.resolve(GainEnergy(self.unit, 1, source=self.source))


@dataclasses.dataclass(eq=False)
class SchadenfreudeDebuffTrigger(TriggerEffect[ApplyStatus]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: ApplyStatus) -> bool:
        return (
            event.unit != self.unit
            and event.result
            and event.result.intention == StatusIntention.DEBUFF
            and GS.map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: ApplyStatus) -> None:
        ES.resolve(GainEnergy(self.unit, 1, source=self.source))


@dataclasses.dataclass(eq=False)
class OrneryTrigger(TriggerEffect[ApplyStatus]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: ApplyStatus) -> bool:
        return event.unit == self.unit and event.result

    def resolve(self, event: ApplyStatus) -> None:
        ES.resolve(Heal(self.unit, 1, self.source))


# TODO the vision based trigger is cool, but it has some pretty unintuitive interactions,
#  since the attacking unit with this ability will still block vision from where it
#  attacked, not the space it follows up into. This is kinda intentional, but weird,
#  so yeah.
@dataclasses.dataclass(eq=False)
class GrizzlyMurdererTrigger(TriggerEffect[Kill]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: Kill) -> bool:
        return (
            isinstance(event.source, MeleeAttackFacet)
            and event.source.parent == self.unit
        )

    def resolve(self, event: Kill) -> None:
        for unit in GS.map.units:
            if unit.controller != self.unit.controller and unit.can_see(
                GS.map.hex_off(event.unit)
            ):
                apply_status_to_unit(unit, "shocked", self.source, duration=2)


@dataclasses.dataclass(eq=False)
class PuffAwayTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: MoveUnit) -> bool:
        return (
            event.unit.controller != self.unit.controller
            and self.unit.ready
            and event.result
            and GS.map.distance_between(self.unit, event.to_) <= 1
            and GS.map.distance_between(self.unit, event.result) > 1
            and event.unit.is_visible_to(self.unit.controller)
        )

    def resolve(self, event: MoveUnit) -> None:
        if moveable_hexes := [
            h
            for h in self.unit.get_potential_move_destinations(None)
            if GS.map.distance_between(h, event.unit) > 1
        ]:
            decision = GS.make_decision(
                self.unit.controller,
                SelectOptionDecisionPoint(
                    [
                        MoveOption(
                            target_profile=OneOfHexes(
                                moveable_hexes + [GS.map.hex_off(self.unit)]
                            )
                        ),
                        SkipOption(target_profile=NoTarget()),
                    ],
                    explanation="puff away",
                ),
            )
            if isinstance(
                decision.option, MoveOption
            ) and decision.target != GS.map.hex_off(self.unit):
                previous_hex = GS.map.hex_off(self.unit)
                ES.resolve(MoveUnit(self.unit, to_=decision.target))
                apply_status_to_hex(previous_hex, "soot", self.source, duration=2)
                ES.resolve(ExhaustUnit(self.unit))


@dataclasses.dataclass(eq=False)
class CaughtInTheMatchTrigger(TriggerEffect[MoveAction]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MoveAction) -> bool:
        return (
            event.unit.controller != self.unit.controller
            and GS.active_unit_context
            and GS.active_unit_context.unit == event.unit
            and any(
                move_event.unit == event.unit
                and move_event.result
                and GS.map.distance_between(self.unit, move_event.result) <= 1
                and GS.map.distance_between(self.unit, move_event.to_) > 1
                for move_event in event.iter_type(MoveUnit)
            )
        )

    def resolve(self, event: MoveAction) -> None:
        # TODO should be a replacement on move penalty instead?
        ES.resolve(ModifyMovementPoints(event.unit, -1))


@dataclasses.dataclass(eq=False)
class HeelTurnTrigger(TriggerEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: SufferDamage) -> bool:
        return event.unit == self.unit and self.unit.health == 1

    def resolve(self, event: SufferDamage) -> None:
        apply_status_to_unit(self.unit, "they_ve_got_a_steel_chair", self.source)


@dataclasses.dataclass(eq=False)
class TaintedBondTrigger(TriggerEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    link: UnitStatusLink

    def should_trigger(self, event: SufferDamage) -> bool:
        return any(
            event.unit == status.parent for status in self.link.statuses
        ) and not isinstance(event.signature.source, UnitStatus.get("tainted_bond"))

    def resolve(self, event: SufferDamage) -> None:
        for status in self.link.statuses:
            if status.parent != event.unit:
                ES.resolve(
                    Damage(
                        status.parent,
                        DamageSignature(event.result, status, DamageType.PURE),
                    )
                )


@dataclasses.dataclass(eq=False)
class ParchedTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: TurnCleanup) -> bool:
        return (
            self.unit == event.unit
            and GS.active_unit_context
            and GS.active_unit_context.has_acted
            and GS.active_unit_context.movement_points <= 0
        )

    def resolve(self, event: TurnCleanup) -> None:
        ES.resolve(Damage(event.unit, DamageSignature(1, self.source, DamageType.PURE)))


@dataclasses.dataclass(eq=False)
class OldBonesTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = TriggerLayers.OLD_BONES

    unit: Unit
    source: Source

    def should_trigger(self, event: TurnCleanup) -> bool:
        return (
            self.unit == event.unit
            and GS.active_unit_context
            and GS.active_unit_context.has_acted
        )

    def resolve(self, event: TurnCleanup) -> None:
        apply_status_to_unit(self.unit, "tired", self.source, stacks=1)


@dataclasses.dataclass(eq=False)
class TiredDamageTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = TriggerLayers.TIRED

    status: UnitStatus

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: TurnCleanup) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(self.status.stacks, self.status, DamageType.PURE),
            )
        )


@dataclasses.dataclass(eq=False)
class QuickTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.unit

    def resolve(self, event: TurnCleanup) -> None:
        if moveable_hexes := self.unit.get_potential_move_destinations(None):
            decision = GS.make_decision(
                self.unit.controller,
                SelectOptionDecisionPoint(
                    [
                        MoveOption(
                            target_profile=OneOfHexes(
                                moveable_hexes + [GS.map.hex_off(self.unit)]
                            )
                        ),
                        SkipOption(target_profile=NoTarget()),
                    ],
                    explanation="quick",
                ),
            )
            if isinstance(
                decision.option, MoveOption
            ) and decision.target != GS.map.hex_off(self.unit):
                ES.resolve(MoveAction(self.unit, to_=decision.target))


@dataclasses.dataclass(eq=False)
class ToxicPresenceTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    amount: int

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.unit

    def resolve(self, event: TurnCleanup) -> None:
        for unit in GS.map.get_neighboring_units_off(self.unit):
            apply_status_to_unit(unit, "poison", self.source, stacks=self.amount)


@dataclasses.dataclass(eq=False)
class JukeAndJiveTrigger(TriggerEffect[ActionCleanup]):
    priority: ClassVar[int] = 0
    _visible: bool | None = dataclasses.field(init=False, default=None)

    unit: Unit
    source: Source

    @hook_on(ActionUpkeep)
    def on_turn_upkeep(self, event: ActionUpkeep) -> None:
        if event.unit == self.unit:
            self._visible = any(
                player != self.unit.controller and self.unit.is_visible_to(player)
                for player in GS.turn_order
            )

    def should_trigger(self, event: ActionCleanup) -> bool:
        return (
            event.unit == self.unit
            and any(
                player != self.unit.controller and self.unit.is_visible_to(player)
                for player in GS.turn_order
            )
            != self._visible
        )

    def resolve(self, event: ActionCleanup) -> None:
        apply_status_to_unit(self.unit, "all_in_jest", self.source, stacks=1)


@dataclasses.dataclass(eq=False)
class MineTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: HexStatus

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.status.parent and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Damage(event.unit, DamageSignature(2, self.status)))
        self.status.remove()


@dataclasses.dataclass(eq=False)
class BurnOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int | Callable[..., int]

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        apply_status_to_unit(
            event.unit,
            "burn",
            None,
            stacks=self.amount if isinstance(self.amount, int) else self.amount(),
        )


@dataclasses.dataclass(eq=False)
class UnitAppliesStatusOnMoveTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit
    signature: HexStatusSignature

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.unit == self.unit and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(ApplyHexStatus(event.to_, self.signature))


@dataclasses.dataclass(eq=False)
class ChillTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    unit: Unit
    source: Source

    def should_trigger(self, event: RoundCleanup) -> bool:
        return not any(
            GS.map.get_neighboring_units_off(
                self.unit, controlled_by=self.unit.controller
            )
        )

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(Damage(self.unit, DamageSignature(1, self.source, DamageType.PURE)))


@dataclasses.dataclass(eq=False)
class BurnOnCleanup(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_APPLY_DEBUFFS

    hex: Hex
    amount: int | Callable[..., int]

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            apply_status_to_unit(
                unit,
                "burn",
                None,
                stacks=self.amount if isinstance(self.amount, int) else self.amount(),
            )


@dataclasses.dataclass(eq=False)
class FleetingTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.FLEETING

    unit: Unit
    round: int
    source: Source

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.round_counter >= self.round

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(Kill(self.unit, self.source))


@dataclasses.dataclass(eq=False)
class BurnTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    status: UnitStatus

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(self.status.parent, DamageSignature(self.status.stacks, self.status))
        )
        self.status.decrement_stacks()


@dataclasses.dataclass(eq=False)
class SludgeTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    status: HexStatus

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.status.parent) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.status.parent):
            apply_status_to_unit(unit, "slimed", self.status, duration=2)


@dataclasses.dataclass(eq=False)
class RoundHealTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_HEAL_TICK

    unit: Unit
    amount: int
    source: Source

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(Heal(self.unit, self.amount, self.source))


@dataclasses.dataclass(eq=False)
class HexRoundHealTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_HEAL_TICK

    hex: Hex
    amount: int
    source: Source

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            ES.resolve(Heal(unit, self.amount, self.source))


@dataclasses.dataclass(eq=False)
class ShrineWalkInTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    source: Source

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        apply_status_to_unit(event.unit, "fortified", self.source, stacks=1, duration=4)


@dataclasses.dataclass(eq=False)
class TiredRestTrigger(TriggerEffect[Rest]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: Rest) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: Rest) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class ShrineSkipTrigger(TriggerEffect[Rest]):
    priority: ClassVar[int] = 0

    hex: Hex
    source: Source

    def should_trigger(self, event: Rest) -> bool:
        return GS.map.distance_between(event.unit, self.hex) <= 1

    def resolve(self, event: Rest) -> None:
        ES.resolve(Heal(event.unit, 1, self.source))


@dataclasses.dataclass(eq=False)
class HexWalkInDamageTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    source: Source
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            Damage(
                event.unit,
                DamageSignature(self.amount, self.source, type=DamageType.PURE),
            )
        )


@dataclasses.dataclass(eq=False)
class HitchedTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    puller: Unit
    pulled: Unit

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.unit == self.puller

    def resolve(self, event: MoveUnit) -> None:
        if event.result:
            ES.resolve(MoveUnit(self.pulled, event.result, external=True))


@dataclasses.dataclass(eq=False)
class RecurringUnitBuffTrigger(TriggerEffect[RoundUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source
    status_type: type[UnitStatus]

    def should_trigger(self, event: RoundUpkeep) -> bool:
        return not self.unit.has_status(self.status_type)

    def resolve(self, event: RoundUpkeep) -> None:
        apply_status_to_unit(self.unit, self.status_type, self.source, stacks=1)


@dataclasses.dataclass(eq=False)
class FleaInfestedTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    unit: Unit
    controller: Player

    def resolve(self, event: RoundCleanup) -> None:
        if hexes := [
            h for h in GS.map.get_neighbors_off(self.unit) if not GS.map.unit_on(h)
        ]:
            ES.resolve(
                SpawnUnit(
                    UnitBlueprint.get_class("annoying_flea"),
                    self.controller,
                    GS.make_decision(
                        self.controller,
                        SelectOptionDecisionPoint(
                            [
                                MoveOption(target_profile=OneOfHexes(hexes)),
                            ],
                            explanation="Flea Infested",
                        ),
                    ).target,
                )
            )


@dataclasses.dataclass(eq=False)
class HexRoundDamageTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    hex: Hex
    source: Source
    amount: int

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            ES.resolve(
                Damage(
                    unit,
                    DamageSignature(self.amount, self.source, type=DamageType.PURE),
                )
            )


@dataclasses.dataclass(eq=False)
class ExpireOnActivatedTrigger(TriggerEffect[TurnUpkeep]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: TurnUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: TurnUpkeep) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class ExpiresOnMovesTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.result and event.unit == self.status.parent

    def resolve(self, event: MoveUnit) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class TurnExpiringStatusTrigger(TriggerEffect[Turn]):
    priority: ClassVar[int] = 0

    status: Status

    def resolve(self, event: Turn) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class ExpireOnDealDamageStatusTrigger(TriggerEffect[Damage]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: Damage) -> bool:
        return (
            event.signature.get_unit_source() == self.status.parent
            and event.unit.controller != self.status.parent.controller
        )

    def resolve(self, event: Damage) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class ApplyStatusOnHitTrigger(TriggerEffect[Hit]):
    priority: ClassVar[int] = 0

    unit: Unit
    signature: UnitStatusSignature

    def should_trigger(self, event: Hit) -> bool:
        return event.defender == self.unit

    def resolve(self, event: Hit) -> None:
        ES.resolve(ApplyStatus(event.attacker, self.signature))


@dataclasses.dataclass(eq=False)
class ExpireOnHitTrigger(TriggerEffect[Hit]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: Hit) -> bool:
        return event.attacker == self.status.parent

    def resolve(self, event: Damage) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class DecrementPerDamageTrigger(TriggerEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: SufferDamage) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: SufferDamage) -> None:
        self.status.decrement_stacks(event.result)


@dataclasses.dataclass(eq=False)
class ExpireOnSufferDamageStatusTrigger(TriggerEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    status: Status

    def should_trigger(self, event: SufferDamage) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: SufferDamage) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class RoundDamageTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    unit: Unit
    source: Source
    amount: int | Callable[..., int]

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(
                self.unit,
                DamageSignature(
                    self.amount if isinstance(self.amount, int) else self.amount(),
                    self.source,
                    type=DamageType.PURE,
                ),
            )
        )


@dataclasses.dataclass(eq=False)
class PanickedTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.PANIC

    status: UnitStatus

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(
                    len(list(GS.map.get_neighboring_units_off(self.status.parent))),
                    self.status,
                    type=DamageType.PURE,
                ),
            )
        )


@dataclasses.dataclass(eq=False)
class PureInnocenceTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.unit and get_source_unit(event.source)

    def resolve(self, event: KillUpkeep) -> None:
        apply_status_to_unit(get_source_unit(event.source), "shame", self.source)


@dataclasses.dataclass(eq=False)
class FoulBurstTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.unit

    def resolve(self, event: KillUpkeep) -> None:
        apply_status_to_hex(GS.map.hex_off(event.unit), "soot", self.source, duration=2)


@dataclasses.dataclass(eq=False)
class ParasiteTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: KillUpkeep) -> None:
        target_hex = GS.map.hex_off(event.unit)
        if GS.map.unit_on(target_hex):
            target_hex = None

            for historic_event in reversed(ES.history):
                if isinstance(historic_event, TurnUpkeep):
                    break
                if (
                    isinstance(historic_event, MeleeAttackAction)
                    and historic_event.defender == event.unit
                ):
                    for move in historic_event.iter_type(MoveUnit):
                        if (
                            move.unit == historic_event.attacker
                            and move.result
                            and not GS.map.unit_on(move.result)
                        ):
                            target_hex = move.result
                            break
                if target_hex:
                    break

        if target_hex:
            ES.resolve(
                SpawnUnit(
                    blueprint=UnitBlueprint.registry["horror_spawn"],
                    controller=self.status.controller,
                    space=target_hex,
                    exhausted=True,
                )
            )


@dataclasses.dataclass(eq=False)
class OneTimeModifyMovementPointsStatusTrigger(TriggerEffect[TurnUpkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus
    amount: int

    def should_trigger(self, event: TurnUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: TurnUpkeep) -> None:
        ES.resolve(ModifyMovementPoints(self.status.parent, self.amount))
        self.status.remove()


@dataclasses.dataclass(eq=False)
class ScurryInTheShadowsTrigger(TriggerEffect[TurnUpkeep]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: TurnUpkeep) -> bool:
        return event.unit == self.unit and not any(
            player != self.unit.controller and self.unit.is_visible_to(player)
            for player in GS.turn_order
        )

    def resolve(self, event: TurnUpkeep) -> None:
        ES.resolve(ModifyMovementPoints(self.unit, 2))


@dataclasses.dataclass(eq=False)
class BellStruckTrigger(TriggerEffect[ReceiveDamage]):
    priority: ClassVar[int] = TriggerLayers.EXHAUST

    unit: Unit
    source: Source

    def should_trigger(self, event: ReceiveDamage) -> bool:
        return event.unit == self.unit and event.signature.amount >= 3

    def resolve(self, event: ReceiveDamage) -> None:
        apply_status_to_unit(event.unit, "stunned", self.source, stacks=1)


@dataclasses.dataclass(eq=False)
class InspirationTrigger(TriggerEffect[ActivateAbilityAction]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: ActivateAbilityAction) -> bool:
        return (
            event.unit != self.unit
            and (energy_cost := event.ability.get_cost().get(EnergyCost))
            and energy_cost.amount >= 3
            # TODO should be able to see unit, not hex
            and self.unit.can_see(GS.map.hex_off(event.unit))
        )

    def resolve(self, event: ActivateAbilityAction) -> None:
        ES.resolve(
            GainEnergy(
                self.unit,
                (
                    2
                    if (energy_cost := event.ability.get_cost().get(EnergyCost))
                    and energy_cost.amount >= 4
                    else 1
                ),
                source=self.source,
            )
        )


@dataclasses.dataclass(eq=False)
class AutomatedTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: MoveUnit) -> bool:
        return (
            self.unit.ready
            and event.unit.controller != self.unit.controller
            and event.result
            and (attack := self.unit.get_primary_attack())
            and event.unit in attack.get_legal_targets(ActiveUnitContext(self.unit, 1))
        )

    def resolve(self, event: MoveUnit) -> None:
        if attack := self.unit.get_primary_attack():
            ES.resolve(Hit(self.unit, event.unit, attack))
            ES.resolve(ExhaustUnit(self.unit))


@dataclasses.dataclass(eq=False)
class WalkInDestroyStatusTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: HexStatus

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.result and event.to_ == self.status.parent

    def resolve(self, event: MoveUnit) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class BaffledTrigger(TriggerEffect[Turn]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def should_trigger(self, event: Turn) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: Turn) -> None:
        if event.result:
            apply_status_to_unit(self.status.parent, "stunned", self.status, stacks=1)
        self.status.remove()
