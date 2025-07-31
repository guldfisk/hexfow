import dataclasses
from enum import IntEnum, auto
from typing import ClassVar, Callable

from events.eventsystem import TriggerEffect, ES, hook_on, E
from game.core import (
    Unit,
    Hex,
    MeleeAttackFacet,
    MoveOption,
    OneOfHexes,
    SkipOption,
    StatusSignature,
    DamageSignature,
    Source,
    UnitStatus,
    Status,
    UnitBlueprint,
    EnergyCost,
    HexStatus,
    GS,
)
from game.decisions import NoTarget, SelectOptionDecisionPoint
from game.events import (
    Hit,
    Damage,
    MoveAction,
    MeleeAttackAction,
    MoveUnit,
    Kill,
    KillUpkeep,
    GainEnergy,
    ApplyStatus,
    TurnCleanup,
    SufferDamage,
    ActionUpkeep,
    ActionCleanup,
    RoundCleanup,
    Rest,
    Heal,
    Turn,
    TurnUpkeep,
    SpawnUnit,
    ReceiveDamage,
    ModifyMovementPoints,
    ExhaustUnit,
    ActivateAbilityAction,
    ReadyUnit,
)
from game.values import DamageType, StatusIntention


class TriggerLayers(IntEnum):
    ROUND_STATUSES_TICK = auto()
    ROUND_APPLY_DEBUFFS = auto()

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
    signature: StatusSignature

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


# TODO same trigger etc
@dataclasses.dataclass(eq=False)
class SchadenfreudeDamageTrigger(TriggerEffect[Damage]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: Damage) -> bool:
        return (
            event.unit != self.unit
            and GS.map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: Damage) -> None:
        ES.resolve(GainEnergy(self.unit, 1))


@dataclasses.dataclass(eq=False)
class SchadenfreudeDebuffTrigger(TriggerEffect[ApplyStatus]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: ApplyStatus) -> bool:
        return (
            event.unit != self.unit
            and event.result.intention == StatusIntention.DEBUFF
            and GS.map.distance_between(self.unit, event.unit) <= 1
        )

    def resolve(self, event: ApplyStatus) -> None:
        ES.resolve(GainEnergy(self.unit, 1))


# TODO originally this was for all simple attacks, but then the kill event isn't
#  a child. could of course hack it in some way, or just have multiple triggers,
#  but it only has a melee attack, and maybe it is more evocative anyways...
# TODO the vision based trigger is cool, but it has some pretty unintuitive interactions,
#  since the attacking unit with this ability will still block vision from where it
#  attacked, not the space it follows up into. This is kinda intentional, but weird,
#  so yeah.
@dataclasses.dataclass(eq=False)
class GrizzlyMurdererTrigger(TriggerEffect[MeleeAttackAction]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def should_trigger(self, event: MeleeAttackAction) -> bool:
        return event.attacker == self.unit and any(
            kill.unit == event.defender for kill in event.iter_type(Kill)
        )

    def resolve(self, event: MeleeAttackAction) -> None:
        for unit in GS.map.units:
            if unit.controller != self.unit.controller and unit.can_see(
                GS.map.hex_off(event.defender)
            ):
                ES.resolve(
                    ApplyStatus(
                        unit,
                        StatusSignature(
                            UnitStatus.get("terrified"), self.source, duration=2
                        ),
                    )
                )


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
        return event.unit == self.unit and event.result >= 4

    def resolve(self, event: SufferDamage) -> None:
        ES.resolve(
            ApplyStatus(
                self.unit,
                StatusSignature(
                    UnitStatus.get("they_ve_got_a_steel_chair"), self.source
                ),
            )
        )


@dataclasses.dataclass(eq=False)
class QuickTrigger(TriggerEffect[TurnCleanup]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: TurnCleanup) -> bool:
        return event.unit == self.unit

    def resolve(self, event: TurnCleanup) -> None:
        options = [SkipOption(target_profile=NoTarget())]
        if moveable_hexes := self.unit.get_potential_move_destinations(None):
            options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))

        decision = GS.make_decision(
            self.unit.controller,
            SelectOptionDecisionPoint(options, explanation="quick"),
        )
        if isinstance(decision.option, MoveOption):
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
            ES.resolve(
                ApplyStatus(
                    unit,
                    StatusSignature(
                        UnitStatus.get("poison"), self.source, stacks=self.amount
                    ),
                )
            )


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
                for player in GS.turn_order.players
            )

    def should_trigger(self, event: ActionCleanup) -> bool:
        return (
            event.unit == self.unit
            and any(
                player != self.unit.controller and self.unit.is_visible_to(player)
                for player in GS.turn_order.players
            )
            != self._visible
        )

    def resolve(self, event: ActionCleanup) -> None:
        ES.resolve(
            ApplyStatus(
                self.unit,
                StatusSignature(UnitStatus.get("all_in_jest"), self.source, stacks=1),
            )
        )


@dataclasses.dataclass(eq=False)
class BurnOnWalkIn(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int | Callable[..., int]

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=event.unit,
                signature=StatusSignature(
                    UnitStatus.get("burn"),
                    None,
                    stacks=(
                        self.amount if isinstance(self.amount, int) else self.amount()
                    ),
                ),
            )
        )


@dataclasses.dataclass(eq=False)
class BurnOnCleanup(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_APPLY_DEBUFFS

    hex: Hex
    amount: int | Callable[..., int]

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            ES.resolve(
                ApplyStatus(
                    unit=unit,
                    signature=StatusSignature(
                        UnitStatus.get("burn"),
                        None,
                        stacks=(
                            self.amount
                            if isinstance(self.amount, int)
                            else self.amount()
                        ),
                    ),
                )
            )


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
class HexRoundHealTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

    hex: Hex
    amount: int

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS.map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS.map.unit_on(self.hex):
            ES.resolve(Heal(unit, self.amount))


@dataclasses.dataclass(eq=False)
class ShrineWalkInTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    source: Source

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            ApplyStatus(
                event.unit,
                StatusSignature(UnitStatus.get("fortified"), self.source, duration=4),
            )
        )


@dataclasses.dataclass(eq=False)
class ShrineSkipTrigger(TriggerEffect[Rest]):
    priority: ClassVar[int] = 0

    hex: Hex

    def should_trigger(self, event: Rest) -> bool:
        return GS.map.distance_between(event.unit, self.hex) <= 1

    def resolve(self, event: Rest) -> None:
        ES.resolve(Heal(event.unit, 1))


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
        print("HALO", event.unit, self.puller)
        return event.unit == self.puller

    def resolve(self, event: MoveUnit) -> None:
        if event.result:
            ES.resolve(MoveUnit(self.pulled, event.result))


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
class TurnExpiringStatusTrigger(TriggerEffect[Turn]):
    priority: ClassVar[int] = 0

    status: Status

    def resolve(self, event: Turn) -> None:
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
    priority: ClassVar[int] = TriggerLayers.ROUND_STATUSES_TICK

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
class BellStruckTrigger(TriggerEffect[ReceiveDamage]):
    priority: ClassVar[int] = TriggerLayers.EXHAUST

    unit: Unit

    def should_trigger(self, event: ReceiveDamage) -> bool:
        return event.unit == self.unit and event.signature.amount >= 3

    def resolve(self, event: ReceiveDamage) -> None:
        ES.resolve(ExhaustUnit(event.unit))


@dataclasses.dataclass(eq=False)
class InspirationTrigger(TriggerEffect[ActivateAbilityAction]):
    priority: ClassVar[int] = 0

    unit: Unit

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
            )
        )


@dataclasses.dataclass(eq=False)
class WalkInDestroyStatusTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: HexStatus

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.result and event.to_ == self.status.parent

    def resolve(self, event: MoveUnit) -> None:
        self.status.remove()
