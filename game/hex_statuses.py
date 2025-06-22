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
    Status,
)
from game.events import MoveUnit, ApplyStatus, Rest, Heal, Damage, RoundCleanup, Turn
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
            ApplyStatus(event.unit, StatusSignature(Fortified, self, duration=4))
        )


@dataclasses.dataclass(eq=False)
class ShrineSkipTrigger(TriggerEffect[Rest]):
    priority: ClassVar[int] = 0

    hex: Hex

    def should_trigger(self, event: Rest) -> bool:
        return GS().map.distance_between(event.unit, self.hex) <= 1

    def resolve(self, event: Rest) -> None:
        ES.resolve(Heal(event.unit, 1))


class Shrine(HexStatus):

    def merge(self, incoming: Self) -> bool:
        return True

    def create_effects(self) -> None:
        self.register_effects(
            HexIncreasesEnergyRegenModifier(self.parent),
            ShrineWalkInTrigger(self.parent, 1),
            ShrineSkipTrigger(self.parent),
        )


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
                DamageSignature(self.amount, self.source, type=DamageType.PURE),
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
                    DamageSignature(self.amount, self.source, type=DamageType.PURE),
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

    def create_effects(self) -> None:
        self.register_effects(
            SootWalkInTrigger(self.parent, self, 1),
            SootRoundTrigger(self.parent, self, 1),
            SootSightModifier(self.parent),
            SootVisionBlockingModifier(self.parent),
        )


class Smoke(DurationStatusMixin, HexStatus):

    def create_effects(self) -> None:
        self.register_effects(
            SootSightModifier(self.parent), SootVisionBlockingModifier(self.parent)
        )


@dataclasses.dataclass(eq=False)
class BurningTerrainWalkInTrigger(TriggerEffect[MoveUnit]):
    priority: ClassVar[int] = 0

    status: HexStatus
    source: Source

    def should_trigger(self, event: MoveUnit) -> bool:
        return event.to_ == self.status.parent and event.result

    def resolve(self, event: MoveUnit) -> None:
        ES.resolve(
            ApplyStatus(
                unit=event.unit,
                signature=StatusSignature(Burn, self.source, stacks=self.status.stacks),
            )
        )


@dataclasses.dataclass(eq=False)
class BurningTerrainRoundTrigger(TriggerEffect[RoundCleanup]):
    priority: ClassVar[int] = 0

    status: HexStatus
    source: Source

    def should_trigger(self, event: RoundCleanup) -> bool:
        return GS().map.unit_on(self.status.parent) is not None

    def resolve(self, event: RoundCleanup) -> None:
        if unit := GS().map.unit_on(self.status.parent):
            ES.resolve(
                ApplyStatus(
                    unit=unit,
                    signature=StatusSignature(
                        Burn, self.source, stacks=self.status.stacks
                    ),
                )
            )


class BurningTerrain(HexStatus):

    def merge(self, incoming: Self) -> bool:
        # TODO common logic?
        if not self.duration is None and (
            incoming.duration is None or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        if incoming.stacks > self.stacks:
            self.stacks = incoming.stacks
        return True

    def create_effects(self) -> None:
        self.register_effects(
            BurningTerrainWalkInTrigger(self, self),
            BurningTerrainRoundTrigger(self, self),
        )


@dataclasses.dataclass(eq=False)
class RevealedModifier(StateModifierEffect[Hex, Player, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_visible_to

    space: Hex
    controller: Player

    def should_modify(self, obj: Hex, request: Player, value: bool) -> bool:
        return obj == self.space and request == self.controller

    def modify(self, obj: Hex, request: Player, value: bool) -> bool:
        return True


class Revealed(HexStatus):
    def merge(self, incoming: Self) -> bool:
        # TODO common logic?
        if incoming.controller == self.controller:
            if not self.duration is None and (
                incoming.duration is None or (incoming.duration > self.duration)
            ):
                self.duration = incoming.duration
            return True
        return False

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(RevealedModifier(self.parent, self.controller))


# TODO common
@dataclasses.dataclass(eq=False)
class TurnExpiringStatusTrigger(TriggerEffect[Turn]):
    priority: ClassVar[int] = 0

    status: Status

    def resolve(self, event: Turn) -> None:
        self.status.remove()


class Glimpse(HexStatus):
    def merge(self, incoming: Self) -> bool:
        return incoming.controller == self.controller

    def is_hidden_for(self, player: Player) -> bool:
        return player != self.controller

    def create_effects(self) -> None:
        self.register_effects(
            RevealedModifier(self.parent, self.controller),
            TurnExpiringStatusTrigger(self),
        )
