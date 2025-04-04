from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from typing import ClassVar, Literal, Any, TypeVar, Iterator
from typing import Mapping

from bidict import bidict

from events.eventsystem import Modifiable, ModifiableAttribute, modifiable
from game.game.decisions import DecisionPoint, Option, TargetProfile, O, JSON
from game.game.has_effects import HasEffects
from game.game.map.coordinates import CubeCoordinate
from game.game.player import Player
from game.game.statuses import HasStatuses
from game.game.turn_order import TurnOrder
from game.game.values import Size


A = TypeVar("A", bound=DecisionPoint)
T = TypeVar("T")


class SerializationContext: ...


class Serializable(ABC):

    @abstractmethod
    def serialize(self, context: SerializationContext) -> JSON: ...


class MoveOption(Option[O]):

    def serialize_values(self) -> JSON:
        return {}


@dataclasses.dataclass
class EffortOption(Option[O]):
    facet: EffortFacet

    def serialize_values(self) -> JSON:
        return {"facet": self.facet.serialize(None)}


class Facet(HasStatuses, Serializable):
    name: ClassVar[str]
    description: ClassVar[str | None] = None
    flavor: ClassVar[str | None] = None

    def __init__(self, owner: Unit):
        super().__init__()

        self.owner = owner

    def create_effects(self) -> None: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"name": self.name}


class EffortFacet(Facet, Modifiable):
    movement_cost: ClassVar[int | None]

    @modifiable
    def has_sufficient_movement_points(self, context: ActiveUnitContext) -> bool:
        return (
            self.movement_cost is None or self.movement_cost <= context.movement_points
        )

    @abstractmethod
    def can_be_activated(self, context: ActiveUnitContext) -> bool: ...


class AttackFacet(EffortFacet): ...


class MeleeAttackFacet(AttackFacet):
    damage: ClassVar[int]

    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]:
        return [
            unit
            for unit in GS().map.get_neighboring_units_off(self.owner)
            if unit.controller != self.owner.controller
            and unit.can_be_attacked_by(self)
        ]

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return self.has_sufficient_movement_points() and self.get_legal_targets()


class ActivatedAbilityFacet(EffortFacet): ...


class StatickAbilityFacet(Facet): ...


FULL_ENERGY: Literal["FULL_ENERGY"] = "FULL_ENERGY"


@dataclasses.dataclass
class UnitBlueprint:
    name: str
    health: int
    speed: int
    sight: int
    energy: int = 0
    starting_energy: int | FULL_ENERGY = FULL_ENERGY
    size: Size = Size.MEDIUM
    aquatic: bool = False
    facets: list[type[Facet]] = dataclasses.field(default_factory=list)


class Unit(HasStatuses, Modifiable, Serializable):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    max_energy: ModifiableAttribute[None, int]
    size: ModifiableAttribute[None, Size]
    attack_power: ModifiableAttribute[None, int]
    aquatic: ModifiableAttribute[None, bool]
    is_broken: ModifiableAttribute[None, bool]

    def __init__(
        self, controller: Player, blueprint: UnitBlueprint, exhausted: bool = False
    ):
        super().__init__()

        self.controller = controller
        self.blueprint = blueprint

        self.damage: int = 0
        self.max_health.set(blueprint.health)
        self.sight.set(blueprint.sight)
        self.max_energy.set(blueprint.energy)
        self.energy: int = (
            blueprint.starting_energy
            if isinstance(blueprint.starting_energy, int)
            else blueprint.energy
        )
        self.size.set(blueprint.size)
        self.attack_power.set(0)
        self.aquatic.set(blueprint.aquatic)
        self.is_broken.set(False)
        self.exhausted = exhausted

        self.attacks: list[AttackFacet] = []
        self.activated_abilities: list[ActivatedAbilityFacet] = []
        self.static_abilities: list[StatickAbilityFacet] = []

        for facet in blueprint.facets:
            if issubclass(facet, AttackFacet):
                self.attacks.append(facet(self))
            elif issubclass(facet, ActivatedAbilityFacet):
                self.activated_abilities.append(facet(self))
            elif issubclass(facet, StatickAbilityFacet):
                self.static_abilities.append(facet(self))

        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.create_effects()

    @modifiable
    def can_be_activated(self, _: None = None) -> bool:
        return not self.exhausted

    @modifiable
    def can_be_attacked_by(self, attack: AttackFacet) -> bool:
        # if isinstance(attack, MeleeAttack):
        return True

    @modifiable
    def get_legal_options(self, _: None = None) -> list[Option]:
        options = []
        if moveable_hexes := [
            _hex
            for _hex in GS().map.get_neighbors_off(self)
            if _hex.can_move_into(self)
        ]:
            options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))
        for facet in self.attacks:
            if isinstance(facet, MeleeAttackFacet) and facet.can_be_activated(
                GS().active_unit_context
            ):
                options.append(
                    EffortOption(
                        facet, target_profile=OneOfUnits(facet.get_legal_targets())
                    )
                )
        return options

    @property
    def health(self) -> int:
        return self.max_health.g() - self.damage

    def serialize(self, context: SerializationContext) -> JSON:
        return {"name": self.blueprint.name}

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))


@dataclasses.dataclass
class OneOfUnits(TargetProfile[Unit]):
    units: list[Unit]

    def serialize_values(self) -> JSON:
        return {"units": [unit.serialize(None) for unit in self.units]}

    def parse_response(self, v: Any) -> Unit:
        return self.units[v["index"]]


@dataclasses.dataclass
class Landscape:
    terrain_map: Mapping[CubeCoordinate, type[Terrain]]
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]


class Terrain(HasEffects, ABC):

    def is_water(self) -> bool:
        return False


@dataclasses.dataclass
class Hex(Modifiable, HasStatuses, Serializable):
    position: CubeCoordinate
    terrain: Terrain
    map: HexMap

    @modifiable
    def is_passable_to(self, unit: Unit) -> bool:
        if self.terrain.is_water():
            return unit.aquatic.g()
        return True

    @modifiable
    def is_occupied_for(self, unit: Unit) -> bool:
        return not self.map.unit_on(self)

    @modifiable
    def can_move_into(self, unit: Unit) -> bool:
        return self.is_occupied_for(unit) and self.is_passable_to(unit)

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "cc": {
                "r": self.position.r,
                "h": self.position.h,
            },
            "terrain": self.terrain.__class__.__name__,
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))


@dataclasses.dataclass
class OneOfHexes(TargetProfile[Hex]):
    hexes: list[Hex]

    def serialize_values(self) -> JSON:
        return {"units": [_hex.serialize(None) for _hex in self.hexes]}

    def parse_response(self, v: Any) -> Hex:
        return self.hexes[v["index"]]


class MovementException(Exception): ...


class HexMap:
    def __init__(self, landscape: Landscape):
        # TODO register terrain effects
        self.hexes = {
            position: Hex(position=position, terrain=terrain_type(), map=self)
            for position, terrain_type in landscape.terrain_map.items()
        }
        self.unit_positions: bidict[Unit, Hex] = bidict()

    def units_controlled_by(self, player: Player) -> Iterator[Unit]:
        for unit in self.unit_positions.keys():
            if unit.controller == player:
                yield unit

    def move_unit_to(self, unit: Unit, space: Hex) -> None:
        if self.unit_positions.inverse.get(space) is not None:
            raise MovementException()
        self.unit_positions[unit] = space

    def unit_on(self, space: Hex) -> Unit | None:
        return self.unit_positions.inverse.get(space)

    def position_of(self, unit: Unit) -> Hex:
        return self.unit_positions[unit]

    def get_neighbors_off(self, off: CubeCoordinate | Unit) -> Iterator[Hex]:
        for neighbor_coordinate in (
            self.unit_positions[off] if isinstance(off, Unit) else off
        ).neighbors():
            if _hex := self.hexes.get(neighbor_coordinate):
                yield _hex

    def get_neighboring_units_off(
        self, off: CubeCoordinate | Unit, controlled_by: Player | None = None
    ) -> Iterator[Unit]:
        for _hex in self.get_neighbors_off(off):
            if unit := self.unit_positions.inverse.get(_hex):
                if controlled_by is None or controlled_by == unit.controller:
                    yield unit


@dataclasses.dataclass
class ActiveUnitContext:
    unit: Unit
    movement_points: int
    should_stop: bool = False


class GameState:
    instance: GameState | None = None

    def __init__(self, player_count: int):
        self.turn_order = TurnOrder([Player() for _ in range(player_count)])
        # self.map = HexMap(settings.map_spec.generate_landscape())
        self.map = HexMap()
        self.active_unit_context: ActiveUnitContext | None = None
        # self.points: dict[Player]
        self.target_points = 10
        self.round_counter = 0

    def take_action(self, player: Player, action: DecisionPoint[T]) -> T: ...


# TODO
def GS() -> GameState:
    return GameState.instance
