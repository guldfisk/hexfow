import dataclasses
from typing import Self, ClassVar

from events.eventsystem import TriggerEffect, ES, StateModifierEffect
from events.tests.game_objects.advanced_units import Player
from game.game.core import (
    UnitStatus,
    GS,
    RefreshableDurationUnitStatus,
    Unit,
    UnitBlueprint,
    ActiveUnitContext,
    MoveOption,
)
from game.game.damage import DamageSignature
from game.game.decisions import Option
from game.game.events import (
    Damage,
    Upkeep,
    Kill,
    TurnUpkeep,
    MeleeAttackAction,
    MoveUnit,
    SpawnUnit,
    Turn,
    KillUpkeep,
)
from game.game.values import DamageType


@dataclasses.dataclass(eq=False)
class BurnTrigger(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: Upkeep) -> None:
        ES.resolve(Damage(self.status.parent, DamageSignature(self.status.stacks)))
        self.status.decrement_stacks()


# TODO what should the order off trigger be for burn vs decrement and such?
class Burn(UnitStatus):
    identifier = "burn"

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(BurnTrigger(self))


# TODO timings (right now only get to trigger duration -1 times)
@dataclasses.dataclass(eq=False)
class PanickedTrigger(TriggerEffect[Upkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: Upkeep) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(
                    len(list(GS().map.get_neighboring_units_off(self.status.parent))),
                    type=DamageType.TRUE,
                ),
            )
        )


class Panicked(RefreshableDurationUnitStatus):
    identifier = "panicked"

    def create_effects(self, by: Player) -> None:
        self.register_effects(PanickedTrigger(self))


class Ephemeral(UnitStatus):
    identifier = "ephemeral"

    def merge(self, incoming: Self) -> bool:
        if incoming.duration < self.duration:
            self.duration = incoming.duration
            self.original_duration = incoming.original_duration
            return True
        return False

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


@dataclasses.dataclass(eq=False)
class TerrifiedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.attack_power

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value - 1


class Terrified(RefreshableDurationUnitStatus):
    identifier = "terrified"

    def create_effects(self, by: Player) -> None:
        self.register_effects(TerrifiedModifier(self.parent))


@dataclasses.dataclass(eq=False)
class ParasiteTrigger(TriggerEffect[KillUpkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus
    created_by: Player

    def should_trigger(self, event: KillUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: KillUpkeep) -> None:
        target_position = GS().map.position_of(event.unit)
        if GS().map.unit_on(target_position):
            target_position = None

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
                            and not GS().map.unit_on(move.result)
                        ):
                            target_position = move.result
                            break
                if target_position:
                    break

        if target_position:
            ES.resolve(
                SpawnUnit(
                    blueprint=UnitBlueprint.registry["horror_spawn"],
                    controller=self.created_by,
                    space=target_position,
                    exhausted=True,
                )
            )


class Parasite(UnitStatus):
    identifier = "parasite"

    # TODO ABC for this
    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(ParasiteTrigger(self, by))


@dataclasses.dataclass(eq=False)
class BurstOfSpeedTrigger(TriggerEffect[TurnUpkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def should_trigger(self, event: TurnUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: TurnUpkeep) -> None:
        # TODO should be an event
        GS().active_unit_context.movement_points += 1
        self.status.remove()


class BurstOfSpeed(UnitStatus):
    identifier = "burst_of_speed"

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(BurstOfSpeedTrigger(self))


# TODO separate from burst of speed trigger since it should prob
#  have different priority
@dataclasses.dataclass(eq=False)
class StumblingTrigger(TriggerEffect[TurnUpkeep]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def should_trigger(self, event: TurnUpkeep) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: TurnUpkeep) -> None:
        # TODO should be an event
        GS().active_unit_context.movement_points -= 1
        self.status.remove()


class Stumbling(UnitStatus):
    identifier = "stumbling"

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(StumblingTrigger(self))


# TODO maybe this can be merged with the terrified modifier?
@dataclasses.dataclass(eq=False)
class TheyVeGotASteelChairModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.attack_power

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + 2


class TheyVeGotASteelChair(UnitStatus):
    identifier = "they_ve_got_a_steel_chair"

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(TheyVeGotASteelChairModifier(self.parent))


@dataclasses.dataclass(eq=False)
class StaggeredTrigger(TriggerEffect[Turn]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: Turn) -> None:
        self.status.remove()


class Staggered(UnitStatus):
    identifier = "staggered"

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(StaggeredTrigger(self))


@dataclasses.dataclass(eq=False)
class RootedModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_legal_options

    unit: Unit

    def should_modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> bool:
        return obj == self.unit

    def modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> list[Option]:
        return [option for option in value if not isinstance(option, MoveOption)]


class Rooted(RefreshableDurationUnitStatus):
    identifier = "rooted"

    def create_effects(self, by: Player) -> None:
        self.register_effects(RootedModifier(self.parent))
