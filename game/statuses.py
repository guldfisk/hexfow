import dataclasses
from typing import Self, ClassVar

from events.eventsystem import TriggerEffect, ES, StateModifierEffect, ReplacementEffect
from events.tests.game_objects.advanced_units import Player
from game.core import (
    UnitStatus,
    GS,
    RefreshableDurationUnitStatus,
    Unit,
    UnitBlueprint,
    ActiveUnitContext,
    MoveOption,
    DamageSignature,
    OneOfHexes,
    SkipOption,
    EffortOption,
    MeleeAttackFacet,
)
from game.decisions import Option
from game.events import (
    Damage,
    Kill,
    TurnUpkeep,
    MeleeAttackAction,
    MoveUnit,
    SpawnUnit,
    Turn,
    KillUpkeep,
    ReceiveDamage,
    SufferDamage,
    RoundCleanup,
)
from game.values import DamageType, StatusIntention


@dataclasses.dataclass(eq=False)
class BurnTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(self.status.parent, DamageSignature(self.status.stacks, self.status))
        )
        self.status.decrement_stacks()


# TODO what should the order off trigger be for burn vs decrement and such?
class Burn(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(BurnTrigger(self))


@dataclasses.dataclass(eq=False)
class PoisonTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(self.status.stacks, self.status, type=DamageType.PURE),
            )
        )


class Poison(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        self.stacks += incoming.stacks
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(PoisonTrigger(self))


# TODO timings (right now only get to trigger duration -1 times)
@dataclasses.dataclass(eq=False)
class PanickedTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def resolve(self, event: RoundCleanup) -> None:
        ES.resolve(
            Damage(
                self.status.parent,
                DamageSignature(
                    len(list(GS().map.get_neighboring_units_off(self.status.parent))),
                    self.status,
                    type=DamageType.PURE,
                ),
            )
        )


class Panicked(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(PanickedTrigger(self))


class Ephemeral(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        if incoming.duration < self.duration:
            self.duration = incoming.duration
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
    default_intention = StatusIntention.DEBUFF

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
        target_hex = GS().map.hex_off(event.unit)
        if GS().map.unit_on(target_hex):
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
                            and not GS().map.unit_on(move.result)
                        ):
                            target_hex = move.result
                            break
                if target_hex:
                    break

        if target_hex:
            ES.resolve(
                SpawnUnit(
                    blueprint=UnitBlueprint.registry["horror_spawn"],
                    controller=self.created_by,
                    space=target_hex,
                    exhausted=True,
                )
            )


class Parasite(UnitStatus):
    default_intention = StatusIntention.DEBUFF

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
    default_intention = StatusIntention.BUFF

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
    default_intention = StatusIntention.DEBUFF

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
    default_intention = StatusIntention.BUFF

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
    default_intention = StatusIntention.DEBUFF

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
        return [
            option
            for option in value
            if not (
                isinstance(option, MoveOption)
                or (
                    isinstance(option, EffortOption)
                    and isinstance(option.facet, MeleeAttackFacet)
                )
            )
        ]


class Rooted(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(RootedModifier(self.parent))


@dataclasses.dataclass(eq=False)
class IncreaseUnitMaxHealthModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.max_health

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


class Fortified(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.BUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(IncreaseUnitMaxHealthModifier(self.parent, 1))


@dataclasses.dataclass(eq=False)
class LuckyCharmReplacement(ReplacementEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def can_replace(self, event: SufferDamage) -> bool:
        return event.unit == self.status.parent and event.signature.amount == 1

    def resolve(self, event: SufferDamage) -> None:
        self.status.remove()


class LuckyCharm(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.BUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(LuckyCharmReplacement(self))


@dataclasses.dataclass(eq=False)
class BellStruckTrigger(TriggerEffect[ReceiveDamage]):
    priority: ClassVar[int] = 0

    unit: Unit

    def should_trigger(self, event: ReceiveDamage) -> bool:
        return event.unit == self.unit and event.signature.amount >= 3

    def resolve(self, event: ReceiveDamage) -> None:
        self.unit.exhausted = True


class BellStruck(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(BellStruckTrigger(self.parent))


class MortallyWounded(UnitStatus):
    default_intention = StatusIntention.DEBUFF

    def merge(self, incoming: Self) -> bool:
        return True

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


@dataclasses.dataclass(eq=False)
class TerrorModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
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
        has_adjacent_enemies = any(
            unit
            for unit in GS().map.get_neighboring_units_off(obj)
            if unit.controller != obj.controller and unit.is_visible_to(obj.controller)
        )
        options = []
        for option in value:
            if (
                isinstance(option, MoveOption)
                and isinstance(option.target_profile, OneOfHexes)
                and (
                    valid_hexes := [
                        _hex
                        for _hex in option.target_profile.hexes
                        if not any(
                            unit
                            for unit in GS().map.get_neighboring_units_off(_hex)
                            if unit.controller != obj.controller
                            and unit.is_visible_to(obj.controller)
                        )
                    ]
                )
            ):
                options.append(MoveOption(target_profile=OneOfHexes(valid_hexes)))
            else:
                if not has_adjacent_enemies:
                    options.append(option)
        return options


class Terror(RefreshableDurationUnitStatus):
    default_intention = StatusIntention.DEBUFF

    def create_effects(self, by: Player) -> None:
        self.register_effects(TerrorModifier(self.parent))
