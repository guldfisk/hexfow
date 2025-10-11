import dataclasses
import math
from enum import IntEnum, auto
from typing import Callable, ClassVar

from events.eventsystem import StateModifierEffect, hook_on
from events.tests.game_objects.advanced_units import Player
from game.core import (
    GS,
    ActivatedAbilityFacet,
    ActiveUnitContext,
    AttackFacet,
    DamageSignature,
    EffortOption,
    Hex,
    MoveOption,
    OneOfHexes,
    OneOfUnits,
    Option,
    SingleTargetAttackFacet,
    SkipOption,
    Source,
    Terrain,
    TerrainProtectionRequest,
    Unit,
)
from game.events import MoveUnit, TurnUpkeep
from game.map.coordinates import CC
from game.values import Resistance, Size, VisionObstruction


class SpeedLayer(IntEnum):
    FLAT = auto()
    PROPORTIONAL = auto()
    CAP = auto()
    SET = auto()


class SightLayer(IntEnum):
    FLAT = auto()
    CAPPED_FLAT = auto()
    MIN = auto()
    CAP = auto()


class LegalOptions(IntEnum):
    RESTRICTIVE = auto()
    MUST_ATTACK = auto()


class IsHiddenLayer(IntEnum):
    STEALTH = auto()
    DETECTION = auto()


@dataclasses.dataclass(eq=False)
class AquaticModifier(StateModifierEffect[Unit, None, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.is_aquatic

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: bool) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class RootedModifier(StateModifierEffect[Unit, None, list[Hex]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_potential_move_destinations

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: list[Hex]) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: list[Hex]) -> list[Hex]:
        return []


class CrabShuffleModifier(StateModifierEffect[Unit, None, list[Hex]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_potential_move_destinations

    def __init__(self, unit: Unit):
        self.unit = unit
        self._last_direction: CC | None = None

    @hook_on(TurnUpkeep)
    def on_turn_upkeep(self, event: TurnUpkeep) -> None:
        self._last_direction = None

    @hook_on(MoveUnit)
    def on_move(self, event: MoveUnit) -> None:
        if (
            event.unit == self.unit
            and event.result
            and (vector := event.to_.position - event.result.position).length == 1
        ):
            self._last_direction = vector

    def should_modify(self, obj: Unit, request: None, value: list[Hex]) -> bool:
        return obj == self.unit and self._last_direction

    def modify(self, obj: Unit, request: None, value: list[Hex]) -> list[Hex]:
        return [
            h
            for h in value
            if not h.position == GS.map.position_off(self.unit) + self._last_direction
        ]


@dataclasses.dataclass(eq=False)
class FarsightedModifier(StateModifierEffect[Unit, Hex, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.can_see

    unit: Unit

    def should_modify(self, obj: Unit, request: Hex, value: int) -> bool:
        return (
            obj == self.unit
            and request.map.distance_between(self.unit, request.position) == 1
        )

    def modify(self, obj: Unit, request: Hex, value: bool) -> bool:
        return False


@dataclasses.dataclass(eq=False)
class CrushableModifier(StateModifierEffect[Hex, Unit, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_occupied_for

    unit: Unit

    def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return request.controller == self.unit.controller and obj == GS.map.hex_off(
            self.unit
        )

    def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class PusherModifier(StateModifierEffect[Hex, Unit, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_occupied_for

    unit: Unit

    def should_modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return request == self.unit and obj != GS.map.hex_off(self.unit)

    def modify(self, obj: Hex, request: Unit, value: bool) -> bool:
        return True


def stealth_hidden_for(unit: Unit, player: Player) -> bool:
    return unit.controller != player and not any(
        player in seeing_unit.provides_vision_for(None)
        and seeing_unit.can_see(GS.map.hex_off(unit))
        for seeing_unit in GS.map.get_neighboring_units_off(unit)
    )


@dataclasses.dataclass(eq=False)
class InvisibleWhenActiveModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.STEALTH
    target: ClassVar[object] = Unit.is_hidden_for

    unit: Unit

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return (
            obj == self.unit
            and GS.active_unit_context
            and GS.active_unit_context.unit == self.unit
            and request != self.unit.controller
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class StealthModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.STEALTH
    # TODO is_hidden_for should prob be is_hidden_for(unit) instead of for (player)
    target: ClassVar[object] = Unit.is_hidden_for

    unit: Unit

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return obj == self.unit and stealth_hidden_for(obj, request)

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


class NotMovedStealthModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.STEALTH
    target: ClassVar[object] = Unit.is_hidden_for

    def __init__(self, unit: Unit):
        self.unit = unit
        self._has_moved = False

    @hook_on(TurnUpkeep)
    def on_turn_upkeep(self, event: TurnUpkeep):
        self._has_moved = False

    @hook_on(MoveUnit)
    def on_move(self, event: MoveUnit):
        if event.unit == self.unit and event.result:
            self._has_moved = True

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return (
            obj == self.unit
            and not self._has_moved
            and stealth_hidden_for(obj, request)
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class ForestStealthModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.STEALTH
    target: ClassVar[object] = Unit.is_hidden_for

    hex: Hex

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return (
            GS.map.hex_off(obj) == self.hex
            and obj.size.g() == Size.SMALL
            and stealth_hidden_for(obj, request)
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class StealthOnTerrainModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.STEALTH
    target: ClassVar[object] = Unit.is_hidden_for

    unit: Unit
    terrain_type: type[Terrain]

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return (
            obj == self.unit
            and isinstance(GS.map.hex_off(obj).terrain, self.terrain_type)
            and stealth_hidden_for(obj, request)
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class FightFlightFreezeModifier(
    StateModifierEffect[Unit, ActiveUnitContext, list[Option]]
):
    priority: ClassVar[int] = LegalOptions.RESTRICTIVE
    target: ClassVar[object] = Unit.get_legal_options

    unit: Unit

    def should_modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> bool:
        return (
            obj.controller != self.unit.controller
            and GS.map.distance_between(self.unit, obj) <= 1
        )

    def modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> list[Option]:
        options = []
        for option in value:
            if (
                isinstance(option, EffortOption)
                and isinstance(option.facet, SingleTargetAttackFacet)
                and isinstance(option.target_profile, OneOfUnits)
                and self.unit in option.target_profile.units
            ):
                options.append(
                    EffortOption(option.facet, target_profile=OneOfUnits([self.unit]))
                )
            elif (
                isinstance(option, MoveOption)
                and isinstance(option.target_profile, OneOfHexes)
                and (
                    valid_hexes := [
                        _hex
                        for _hex in option.target_profile.hexes
                        if GS.map.distance_between(self.unit, _hex) > 1
                    ]
                )
            ):
                options.append(MoveOption(target_profile=OneOfHexes(valid_hexes)))
            elif isinstance(option, SkipOption):
                options.append(option)
        return options


@dataclasses.dataclass(eq=False)
class MustAttackModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
    priority: ClassVar[int] = LegalOptions.MUST_ATTACK
    target: ClassVar[object] = Unit.get_legal_options

    unit: Unit

    def should_modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> bool:
        return obj == self.unit

    def modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> list[Option]:
        if attack_options := [
            option
            for option in value
            if isinstance(option, EffortOption)
            and isinstance(option.facet, AttackFacet)
        ]:
            return attack_options
        return value


@dataclasses.dataclass(eq=False)
class TelepathicSpyModifier(StateModifierEffect[Unit, None, set[Player]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.provides_vision_for

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: set[Player]) -> bool:
        return (
            obj.controller != self.unit.controller
            and GS.map.distance_between(self.unit, obj) <= 1
        )

    def modify(self, obj: Unit, request: None, value: set[Player]) -> set[Player]:
        return value | {self.unit.controller}


@dataclasses.dataclass(eq=False)
class ParanoiaModifier(StateModifierEffect[Unit, None, set[Player]]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.provides_vision_for

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: set[Player]) -> bool:
        if GS.active_unit_context and GS.active_unit_context.unit == self.unit:
            return obj != self.unit
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: set[Player]) -> set[Player]:
        return value - {self.unit.controller}


@dataclasses.dataclass(eq=False)
class UnitNoCaptureModifier(StateModifierEffect[Unit, Hex, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.can_capture_objectives_on

    unit: Unit

    def should_modify(self, obj: Unit, request: Hex, value: bool) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: Hex, value: bool) -> bool:
        return False


@dataclasses.dataclass(eq=False)
class ResistanceModifier(StateModifierEffect[Unit, DamageSignature, Resistance]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_resistance_against

    unit: Unit
    resistance: Resistance

    def should_modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> bool:
        return obj == self.unit

    def modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> Resistance:
        return max(value, self.resistance)


@dataclasses.dataclass(eq=False)
class SourceTypeResistanceModifier(
    StateModifierEffect[Unit, DamageSignature, Resistance]
):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_resistance_against

    unit: Unit
    source_type: type[Source] | list[type[Source]]
    resistance: Resistance

    def should_modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> bool:
        return (
            obj == self.unit
            and request.source
            and isinstance(request.source, self.source_type)
        )

    def modify(
        self, obj: Unit, request: DamageSignature, value: Resistance
    ) -> Resistance:
        return max(value, self.resistance)


@dataclasses.dataclass(eq=False)
class TerrainProtectionModifier(
    StateModifierEffect[Unit, TerrainProtectionRequest, int]
):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.get_terrain_protection_for

    unit: Unit
    terrain_type: type[Terrain]
    amount: int

    def should_modify(
        self, obj: Unit, request: TerrainProtectionRequest, value: int
    ) -> bool:
        return obj == self.unit and isinstance(
            GS.map.hex_off(self.unit).terrain, self.terrain_type
        )

    def modify(self, obj: Unit, request: TerrainProtectionRequest, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class IncreaseSpeedAuraModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.FLAT
    target: ClassVar[object] = Unit.speed

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return (
            obj.controller == self.unit.controller
            and GS.map.distance_between(obj, self.unit) == 1
        )

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class UnitSpeedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.FLAT
    target: ClassVar[object] = Unit.speed

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class GambitSpeedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.FLAT
    target: ClassVar[object] = Unit.speed

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit and GS.round_counter == 1

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class UnitProportionalSpeedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.PROPORTIONAL
    target: ClassVar[object] = Unit.speed

    unit: Unit
    multiplier: float
    round_up: bool = True

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return (math.ceil if self.round_up else math.floor)(value * self.multiplier)


@dataclasses.dataclass(eq=False)
class UnitCapSpeedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.CAP
    target: ClassVar[object] = Unit.speed

    unit: Unit
    value: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return min(value, self.value)


@dataclasses.dataclass(eq=False)
class UnitSetSpeedModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SpeedLayer.SET
    target: ClassVar[object] = Unit.speed

    unit: Unit
    value: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return self.value


@dataclasses.dataclass(eq=False)
class HexFlatEnergyRegenModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.energy_regen

    space: Hex
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS.map.hex_off(obj) == self.space

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class HexCappedFlatSightModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SightLayer.CAPPED_FLAT
    target: ClassVar[object] = Unit.sight

    space: Hex

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS.map.hex_off(obj) == self.space

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return min(max(value - 1, 1), value)


@dataclasses.dataclass(eq=False)
class HexFlatSightModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SightLayer.FLAT
    target: ClassVar[object] = Unit.sight

    space: Hex
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS.map.hex_off(obj) == self.space

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + self.amount


@dataclasses.dataclass(eq=False)
class HexBlocksVisionModifier(StateModifierEffect[Hex, None, VisionObstruction]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.blocks_vision_for

    space: Hex

    def should_modify(self, obj: Hex, request: None, value: VisionObstruction) -> bool:
        return obj == self.space

    def modify(
        self, obj: Hex, request: None, value: VisionObstruction
    ) -> VisionObstruction:
        return VisionObstruction.FULL


@dataclasses.dataclass(eq=False)
class HexStealthRevealedModifier(StateModifierEffect[Unit, Player, bool]):
    priority: ClassVar[int] = IsHiddenLayer.DETECTION
    target: ClassVar[object] = Unit.is_hidden_for

    space: Hex
    controller: Player | None

    def should_modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return obj == GS.map.unit_on(self.space) and (
            request == self.controller or self.controller is None
        )

    def modify(self, obj: Unit, request: Player, value: bool) -> bool:
        return False


@dataclasses.dataclass(eq=False)
class HexRevealedModifier(StateModifierEffect[Hex, Player, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.is_visible_to

    space: Hex
    controller: Player | None

    def should_modify(self, obj: Hex, request: Player, value: bool) -> bool:
        return obj == self.space and (
            request == self.controller or self.controller is None
        )

    def modify(self, obj: Hex, request: Player, value: bool) -> bool:
        return True


@dataclasses.dataclass(eq=False)
class IgnoreMoveInOnTerrainModifier(StateModifierEffect[Hex, Unit, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.get_move_in_penalty_for

    unit: Unit
    terrain_type: type[Terrain]

    def should_modify(self, obj: Hex, request: Unit, value: int) -> bool:
        return request == self.unit and isinstance(obj.terrain, self.terrain_type)

    def modify(self, obj: Hex, request: Unit, value: int) -> int:
        return 0


@dataclasses.dataclass(eq=False)
class MappedOutModifier(StateModifierEffect[Hex, Unit, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Hex.get_move_in_penalty_for

    space: Hex
    controller: Player

    def should_modify(self, obj: Hex, request: Unit, value: int) -> bool:
        return obj == self.space and request.controller == self.controller

    def modify(self, obj: Hex, request: Unit, value: int) -> int:
        return 0


@dataclasses.dataclass(eq=False)
class UnitAttackPowerFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.attack_power

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class HexAttackPowerFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.attack_power

    hex_: Hex
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return GS.map.hex_off(obj) == self.hex_

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class NegativeAttackPowerAuraModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.attack_power

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return (
            obj.controller != self.unit.controller
            and GS.map.distance_between(obj, self.unit) == 1
        )

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value - self.amount


@dataclasses.dataclass(eq=False)
class UnactivateableModifier(StateModifierEffect[Unit, None, bool]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.can_be_activated

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: bool) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: bool) -> bool:
        return False


@dataclasses.dataclass(eq=False)
class HaughtyModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.energy_regen

    unit: Unit

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit and not self.unit.damage

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + 1


@dataclasses.dataclass(eq=False)
class UnitEnergyRegenFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.energy_regen

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class UnitArmorFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.armor

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class UnitSightFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SightLayer.FLAT
    target: ClassVar[object] = Unit.sight

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class UnitSightMinModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = SightLayer.MIN
    target: ClassVar[object] = Unit.sight

    unit: Unit
    amount: int

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return max(value, self.amount)


@dataclasses.dataclass(eq=False)
class UnitMaxHealthFlatModifier(StateModifierEffect[Unit, None, int]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.max_health

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: int) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: int) -> int:
        return value + (self.amount if isinstance(self.amount, int) else self.amount())


@dataclasses.dataclass(eq=False)
class UnitSizeFlatModifier(StateModifierEffect[Unit, None, Size]):
    priority: ClassVar[int] = 1
    target: ClassVar[object] = Unit.size

    unit: Unit
    amount: int | Callable[..., int]

    def should_modify(self, obj: Unit, request: None, value: Size) -> bool:
        return obj == self.unit

    def modify(self, obj: Unit, request: None, value: Size) -> Size:
        return Size(
            min(
                max(
                    value
                    + (self.amount if isinstance(self.amount, int) else self.amount()),
                    0,
                ),
                2,
            )
        )


@dataclasses.dataclass(eq=False)
class TerrorModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
    priority: ClassVar[int] = LegalOptions.RESTRICTIVE
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
            for unit in GS.map.get_neighboring_units_off(obj)
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
                            for unit in GS.map.get_neighboring_units_off(_hex)
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


@dataclasses.dataclass(eq=False)
class SilencedModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
    priority: ClassVar[int] = LegalOptions.RESTRICTIVE
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
                isinstance(option, EffortOption)
                and isinstance(option.facet, ActivatedAbilityFacet)
            )
        ]


@dataclasses.dataclass(eq=False)
class DisarmedModifier(StateModifierEffect[Unit, ActiveUnitContext, list[Option]]):
    priority: ClassVar[int] = LegalOptions.RESTRICTIVE
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
                isinstance(option, EffortOption)
                and isinstance(option.facet, AttackFacet)
            )
        ]


@dataclasses.dataclass(eq=False)
class UnwieldySwimmerModifier(
    StateModifierEffect[Unit, ActiveUnitContext, list[Option]]
):
    priority: ClassVar[int] = LegalOptions.RESTRICTIVE
    target: ClassVar[object] = Unit.get_legal_options

    unit: Unit

    def should_modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> bool:
        return obj == self.unit and isinstance(
            GS.map.hex_off(self.unit).terrain, Terrain.registry["water"]
        )

    def modify(
        self, obj: Unit, request: ActiveUnitContext, value: list[Option]
    ) -> list[Option]:
        return [
            option
            for option in value
            if not (
                isinstance(option, EffortOption)
                and isinstance(option.facet, (ActivatedAbilityFacet, AttackFacet))
            )
        ]


@dataclasses.dataclass(eq=False)
class HexMoveOutPenaltyModifier(StateModifierEffect[Hex, Unit, int]):
    priority: ClassVar[int] = 0
    target: ClassVar[object] = Hex.get_move_out_penalty_for

    hex: Hex
    amount: int

    def should_modify(self, obj: Hex, request: Unit, value: int) -> bool:
        return obj == self.hex

    def modify(self, obj: Hex, request: Unit, value: int) -> int:
        return value + self.amount
