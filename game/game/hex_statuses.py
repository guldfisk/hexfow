import dataclasses
from typing import Self, ClassVar

from events.eventsystem import StateModifierEffect, TriggerEffect, ES
from events.tests.game_objects.advanced_units import Player
from game.game.core import HexStatus, Unit, Hex, GS, StatusSignature
from game.game.events import MoveUnit, ApplyStatus, SkipTurn, Heal
from game.game.statuses import Fortified


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


@dataclasses.dataclass(eq=False)
class HexIncreasesEnergyRegenModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.energy_regen

    space: Hex

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS().map.hex_off(obj) == self.space

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + 1


@dataclasses.dataclass(eq=False)
class ShrineWalkInTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    hex: Hex
    amount: int

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.hex and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=event.unit,
                by=None,
                signature=StatusSignature(Fortified, duration=4),
            )
        )


@dataclasses.dataclass(eq=False)
class ShrineSkipTrigger(TriggerEffect[SkipTurn]):
    priority: ClassVar[int] = 0

    hex: Hex

    def should_trigger(self, event: SkipTurn) -> bool:
        return GS().map.distance_between(event.unit, self.hex) <= 1

    def resolve(self, event: SkipTurn) -> None:
        ES.resolve(Heal(event.unit, 1))


class Shrine(HexStatus):

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(
            HexIncreasesEnergyRegenModifier(self.parent),
            ShrineWalkInTrigger(self.parent, 1),
            ShrineSkipTrigger(self.parent),
        )
