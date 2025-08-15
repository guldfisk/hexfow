import dataclasses
from typing import ClassVar

from events.eventsystem import ES, ReplacementEffect, hook_on
from game.core import (
    GS,
    DamageSignature,
    Hex,
    Source,
    StatusSignature,
    Unit,
    UnitStatus,
)
from game.events import (
    ApplyStatus,
    CheckAlive,
    Damage,
    Heal,
    Kill,
    MovePenalty,
    MoveUnit,
    ReadyUnit,
    SufferDamage,
    Turn,
)
from game.statuses.dispel import dispel_from_unit
from game.values import StatusIntention


@dataclasses.dataclass(eq=False)
class CrushableReplacement(ReplacementEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: MoveUnit) -> bool:
        return (
            self.unit.controller == event.unit.controller
            and event.to_ == GS.map.hex_off(self.unit)
        )

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(Kill(self.unit))
        ES.resolve(Heal(event.unit, 1))
        ES.resolve(event)


@dataclasses.dataclass(eq=False)
class PusherReplacement(ReplacementEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def can_replace(self, event: MoveUnit) -> bool:
        return event.unit == self.unit and GS.map.unit_on(event.to_)

    def resolve(self, event: MoveUnit) -> None:
        _map = GS.map
        direction = event.to_.position - _map.position_off(event.unit)

        unit_positions: list[tuple[Unit, Hex | None]] = []
        current_position = _map.position_off(event.unit)
        while True:
            current_position += direction
            current_unit = _map.unit_on(_map.hexes[current_position])
            if not current_unit:
                break
            next_position = current_position + direction
            if next_position not in _map.hexes:
                unit_positions.append((current_unit, None))
                break
            if _map.hexes[next_position].is_passable_to(current_unit):
                unit_positions.append((current_unit, _map.hexes[next_position]))
            else:
                unit_positions.append((current_unit, None))
                break

        for unit, target in reversed(unit_positions):
            moved = False
            if target:
                moved = any(
                    e.unit == unit
                    for e in ES.resolve(MoveUnit(unit, target)).iter_type(MoveUnit)
                )
            if not moved:
                # TODO should damage when move fails, even if the target wasn't non to begin with
                ES.resolve(Damage(unit, DamageSignature(2, self.source)))
                ES.resolve(CheckAlive(unit))

        if not _map.unit_on(event.to_):
            ES.resolve(event)


@dataclasses.dataclass(eq=False)
class PerTurnMovePenaltyIgnoreReplacement(ReplacementEffect[MovePenalty]):
    priority: ClassVar[int] = 0

    unit: Unit
    limit: int
    ignored_this_turn: int = dataclasses.field(init=False, default=0)

    @hook_on(Turn)
    def on_move_hook(self, event: Turn) -> None:
        self.ignored_this_turn = 0

    def can_replace(self, event: MovePenalty) -> bool:
        return event.unit == self.unit and self.ignored_this_turn < self.limit

    def resolve(self, event: MovePenalty) -> None:
        ignore_quantity = min(self.limit - self.ignored_this_turn, event.amount)
        self.ignored_this_turn += ignore_quantity
        event.branch(amount=event.amount - ignore_quantity)


@dataclasses.dataclass(eq=False)
class IgnoresMoveOutPenaltyReplacement(ReplacementEffect[MovePenalty]):
    priority: ClassVar[int] = 0

    unit: Unit

    def can_replace(self, event: MovePenalty) -> bool:
        return event.unit == self.unit and not event.in_

    def resolve(self, event: MovePenalty) -> None:
        pass


@dataclasses.dataclass(eq=False)
class UnitImmuneToStatusReplacement(ReplacementEffect[ApplyStatus]):
    priority: ClassVar[int] = 0

    unit: Unit
    status_type: type[UnitStatus]

    def can_replace(self, event: ApplyStatus) -> bool:
        return (
            event.unit == self.unit and event.signature.status_type == self.status_type
        )

    def resolve(self, event: ApplyStatus) -> None:
        pass


@dataclasses.dataclass(eq=False)
class LastStandReplacement(ReplacementEffect[Kill]):
    priority: ClassVar[int] = 0

    unit: Unit
    source: Source

    def can_replace(self, event: Kill) -> bool:
        return event.unit == self.unit and not any(
            isinstance(status, UnitStatus.get("mortally_wounded"))
            for status in event.unit.statuses
        )

    def resolve(self, event: Kill) -> None:
        event.unit.damage = event.unit.max_health.g() - 1
        dispel_from_unit(event.unit, StatusIntention.DEBUFF)
        ES.resolve(
            ApplyStatus(
                event.unit,
                StatusSignature(
                    UnitStatus.get("mortally_wounded"), self.source, duration=1
                ),
            )
        )


@dataclasses.dataclass(eq=False)
class LuckyCharmReplacement(ReplacementEffect[SufferDamage]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def can_replace(self, event: SufferDamage) -> bool:
        return event.unit == self.status.parent and event.signature.amount == 1

    def resolve(self, event: SufferDamage) -> None:
        self.status.remove()


@dataclasses.dataclass(eq=False)
class StunnedReplacement(ReplacementEffect[ReadyUnit]):
    priority: ClassVar[int] = 0

    status: UnitStatus

    def can_replace(self, event: ReadyUnit) -> bool:
        return event.unit == self.status.parent

    def resolve(self, event: ReadyUnit) -> None:
        self.status.decrement_stacks()
