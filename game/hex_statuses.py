import dataclasses
from typing import Self, ClassVar

from events.eventsystem import StateModifierEffect, TriggerEffect, ES
from events.tests.game_objects.advanced_units import Player
from game.core import (
    HexStatus,
    Unit,
    Hex,
    GS,
    StatusSignature,
    DurationStatusMixin,
    DamageSignature,
    Source,
)
from game.events import MoveUnit, ApplyStatus, SkipTurn, Heal, Damage, RoundCleanup
from game.statuses import Fortified, Burn
from game.values import DamageType, VisionObstruction


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


# witch engine {13pp} x1
# health 7, movement 2, sight 2, energy, M
# choking soot
#     aoe ability 4 energy
#     aoe type hex size 1 range 3 NLoS
#     -1 movement
#     applies status soot to terrain for 2 rounds
#         unstackable, refreshable
#         blocks LoS
#         units on this space has -1 sight, to a minimum of 1
#         when a unit moves in, and at the end of each round, units on this hex receives 1 true damage
# terrify
#     ability 5 energy
#     4 range LoS
#     no movement
#     applies terrified for 2 rounds
#         unstackable, refreshable
#         if this unit is adjacent to an enemy unit, it's owner cannot round skip, and the only legal actions
#         of this units are to move away from any adjacent enemy units
# into the gears
#     ability
#     target adjacent allied unit
#     this unit heals equal to the the units heals and gains energy equal to its energy
#     kill the unit
# - withering presence
#     at the end of this units turn, it applies 1 poison to each adjacent unit
# - auro of paranoia
#     whenever an enemy unit within 4 range becomes the target of an allied ability, it suffers 1 true damage


@dataclasses.dataclass(eq=False)
class SootWalkInTrigger(TriggerEffect[MoveUnit]):
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
                DamageSignature(self.amount, self.source, type=DamageType.TRUE),
            )
        )


@dataclasses.dataclass(eq=False)
class SootRoundTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    hex: Hex
    source: Source
    amount: int

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS().map.unit_on(self.hex) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS().map.unit_on(self.hex):
            ES.resolve(
                Damage(
                    unit,
                    DamageSignature(self.amount, self.source, type=DamageType.TRUE),
                )
            )


@dataclasses.dataclass(eq=False)
class SootSightModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.sight

    space: Hex

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS().map.hex_off(obj) == self.space

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return min(max(value - 1, 1), value)


@dataclasses.dataclass(eq=False)
class SootVisionBlockingModifier(StateModifierEffect[Hex, None, VisionObstruction]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.blocks_vision_for

    space: Hex

    def should_modify(self, obj: Hex, request: None, value: VisionObstruction) -> bool:
        return obj == self.space

    def modify(
        self, obj: Hex, request: None, value: VisionObstruction
    ) -> VisionObstruction:
        return VisionObstruction.FULL


class Soot(DurationStatusMixin, HexStatus):

    def create_effects(self, by: Player) -> None:
        self.register_effects(
            SootWalkInTrigger(self.parent, self, 1),
            SootRoundTrigger(self.parent, self, 1),
            SootSightModifier(self.parent),
            SootVisionBlockingModifier(self.parent),
        )


class Smoke(DurationStatusMixin, HexStatus):

    def create_effects(self, by: Player) -> None:
        self.register_effects(
            SootSightModifier(self.parent), SootVisionBlockingModifier(self.parent)
        )


@dataclasses.dataclass(eq=False)
class BurningTerrainWalkInTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: HexStatus

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.status.parent and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=event.unit,
                by=None,
                signature=StatusSignature(Burn, stacks=self.status.stacks),
            )
        )


@dataclasses.dataclass(eq=False)
class BurningTerrainRoundTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    status: HexStatus

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS().map.unit_on(self.status.parent) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS().map.unit_on(self.status.parent):
            ES.resolve(
                ApplyStatus(
                    unit=unit,
                    by=None,
                    signature=StatusSignature(Burn, stacks=self.status.stacks),
                )
            )


class BurningTerrain(HexStatus):

    def merge(self, incoming: Self) -> bool:
        # TODO common logic?
        if (
            incoming.duration is None
            or self.duration is None
            or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        if incoming.stacks > self.stacks:
            self.stacks = incoming.stacks
        return True

    def create_effects(self, by: Player) -> None:
        self.register_effects(
            BurningTerrainWalkInTrigger(self), BurningTerrainRoundTrigger(self)
        )
