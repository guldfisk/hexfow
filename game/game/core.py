from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import ClassVar, Literal, Any, TypeVar, Iterator
from typing import Mapping

from bidict import bidict

from events.eventsystem import Modifiable, ModifiableAttribute, modifiable, ES
from game.game.damage import DamageSignature
from game.game.decisions import (
    DecisionPoint,
    Option,
    TargetProfile,
    O,
    JSON,
    NoTarget,
    Serializable,
    SerializationContext,
    IDMap,
)
from game.game.has_effects import HasEffects
from game.game.interface import Connection
from game.game.map.coordinates import CC, line_of_sight_obstructed
from game.game.map.geometry import hex_circle
from game.game.player import Player
from game.game.statuses import HasStatuses
from game.game.turn_order import TurnOrder
from game.game.values import Size, DamageType
from game.tests.conftest import EventLogger


A = TypeVar("A", bound=DecisionPoint)
T = TypeVar("T")


class VisionBound(Serializable):

    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"id": context.id_map.get_id_for(self), **self.serialize_values(context)}


class MoveOption(Option[O]):

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class EffortOption(Option[O]):
    facet: EffortFacet

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"facet": self.facet.serialize(context)}


@dataclasses.dataclass
class ActivateUnitOption(Option[O]):

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


class SkipOption(Option[None]):

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


class Facet(HasStatuses, Serializable):
    # TODO hmm
    # name: ClassVar[str]
    # TODO hm
    display_type: ClassVar[str]
    description: ClassVar[str | None] = None
    flavor: ClassVar[str | None] = None

    def __init__(self, owner: Unit):
        super().__init__()

        self.owner = owner

    # TODO common interface?
    def create_effects(self) -> None: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"name": self.__class__.__name__, "type": self.display_type}


class EffortFacet(Facet, Modifiable):
    movement_cost: ClassVar[int | None]
    combineable: ClassVar[bool] = False

    @modifiable
    def has_sufficient_movement_points(self, context: ActiveUnitContext) -> bool:
        return (
            self.movement_cost is None or self.movement_cost <= context.movement_points
        )

    @abstractmethod
    def can_be_activated(self, context: ActiveUnitContext) -> bool: ...


class AttackFacet(EffortFacet): ...


class SingleTargetAttackFacet(AttackFacet):
    damage_type: ClassVar[DamageType]
    damage: ClassVar[int]
    ap: ClassVar[int] = 0

    @modifiable
    def get_damage_against(self, unit: Unit) -> int:
        return self.damage

    @modifiable
    def get_damage_signature_against(self, unit: Unit) -> DamageSignature:
        return DamageSignature(
            self.get_damage_against(unit), type=self.damage_type, ap=self.ap
        )


class MeleeAttackFacet(SingleTargetAttackFacet):
    display_type = "MeleeAttack"
    damage_type = DamageType.MELEE

    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]:
        # TODO handle vision
        return [
            unit
            for unit in GS().map.get_neighboring_units_off(self.owner)
            if unit.controller != self.owner.controller
            and unit.can_be_attacked_by(self)
            # TODO test
            and GS().map.position_of(unit).is_passable_to(self.owner)
        ]

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            not context.activated_facets[self.__class__.__name__]
            and self.has_sufficient_movement_points(context)
            and self.get_legal_targets(None)
        )


class RangedAttackFacet(SingleTargetAttackFacet):
    display_type = "RangedAttack"
    damage_type = DamageType.RANGED
    range: ClassVar[int]

    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]:
        print("legal targets for", self)
        for unit in GS().map.get_units_within_range_off(self.owner, self.range):
            print("against", unit)
            print(
                GS().vision_map[self.owner.controller][
                    GS().map.position_of(unit).position
                ]
            )
            print(
                not line_of_sight_obstructed(
                    GS().map.position_of(self.owner).position,
                    GS().map.position_of(unit).position,
                    GS().vision_obstruction_map[self.owner.controller].get,
                )
            )
            print(unit.can_be_attacked_by(self))
        return [
            unit
            for unit in GS().map.get_units_within_range_off(self.owner, self.range)
            if unit.controller != self.owner.controller
            # TODO test on this
            and GS().vision_map[self.owner.controller][
                GS().map.position_of(unit).position
            ]
            and not line_of_sight_obstructed(
                GS().map.position_of(self.owner).position,
                GS().map.position_of(unit).position,
                GS().vision_obstruction_map[self.owner.controller].get,
            )
            and unit.can_be_attacked_by(self)
        ]

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            not context.activated_facets[self.__class__.__name__]
            and self.has_sufficient_movement_points(context)
            and self.get_legal_targets(None)
        )


class ActivatedAbilityFacet(EffortFacet):
    display_type = "ActivatedAbility"


class StatickAbilityFacet(Facet): ...


FULL_ENERGY: Literal["FULL_ENERGY"] = "FULL_ENERGY"


@dataclasses.dataclass
class UnitBlueprint:
    name: str
    health: int
    speed: int
    sight: int
    armor: int = 0
    energy: int = 0
    starting_energy: int | FULL_ENERGY = FULL_ENERGY
    size: Size = Size.MEDIUM
    aquatic: bool = False
    facets: list[type[Facet]] = dataclasses.field(default_factory=list)

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"


class Unit(HasStatuses, Modifiable, VisionBound):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    armor: ModifiableAttribute[None, int]
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
        self.speed.set(blueprint.speed)
        self.sight.set(blueprint.sight)
        self.armor.set(blueprint.armor)
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
    def blocks_vision_for(self, player: Player) -> bool:
        size = self.size.g()
        if size == Size.LARGE:
            return True
        if size == Size.SMALL:
            return False
        return player != self.controller

    @modifiable
    def can_see(self, space: Hex) -> bool:
        if (
            space.map.position_of(self).position.distance_to(space.position)
            > self.sight.g()
        ):
            return False
        return not line_of_sight_obstructed(
            space.map.position_of(self).position,
            space.position,
            GS().vision_obstruction_map[self.controller].get,
        )
        # obstruction_map = GS().vision_obstruction_map[self.controller]
        #
        # collided_sides = [False, False]
        #
        # for coordinates in find_collisions(
        #     space.map.position_of(self).position, space.position
        # ):
        #     if len(coordinates) == 1:
        #         if obstruction_map[coordinates[0]]:
        #             return False
        #     else:
        #         for idx, c in enumerate(coordinates):
        #             if obstruction_map[c]:
        #                 collided_sides[idx] = True
        #         if all(collided_sides):
        #             return False
        #
        # return True

    @modifiable
    def get_legal_options(self, context: ActiveUnitContext) -> list[Option]:
        options = []
        if context.movement_points > 0:
            if moveable_hexes := [
                _hex
                for _hex in GS().map.get_neighbors_off(self)
                if not GS().vision_map[self.controller][_hex.position]
                or _hex.can_move_into(self)
            ]:
                options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))
            for facet in self.attacks:
                if isinstance(
                    facet, (MeleeAttackFacet, RangedAttackFacet)
                ) and facet.can_be_activated(GS().active_unit_context):
                    options.append(
                        EffortOption(
                            facet,
                            target_profile=OneOfUnits(facet.get_legal_targets(None)),
                        )
                    )
                # if isinstance(facet, RangedAttackFacet) and facet.can_be_activated(GS().active_unit_context):
                #     options.append()
        if not context.has_acted or options:
            options.append(SkipOption(target_profile=NoTarget()))
        return options

    def on_map(self) -> bool:
        return self in GS().map.unit_positions

    @property
    def health(self) -> int:
        return self.max_health.g() - self.damage

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "blueprint": self.blueprint.name,
            "controller": self.controller.name,
            "max_health": self.max_health.g(),
            "damage": self.damage,
            "speed": self.speed.g(),
            "sight": self.sight.g(),
            "max_energy": self.max_energy.g(),
            "energy": self.energy,
            # TODO
            "size": self.size.g().name[0],
            # "attack_power"
            "exhausted": self.exhausted,
        }

    # def serialize(self, context: SerializationContext) -> JSON:
    #     return {"name": self.blueprint.name}

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.blueprint.name}, {self.controller.name}, {id(self)})"


@dataclasses.dataclass
class OneOfUnits(TargetProfile[Unit]):
    units: list[Unit]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.units]
        }

    def parse_response(self, v: Any) -> Unit:
        return self.units[v["index"]]


@dataclasses.dataclass
class Landscape:
    terrain_map: Mapping[CC, type[Terrain]]
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]


@dataclasses.dataclass
class TerrainProtectionRequest:
    unit: Unit
    damage_type: DamageType


class Terrain(HasEffects, ABC):

    def create_effects(self, space: Hex) -> None: ...

    def is_water(self) -> bool:
        return False

    def blocks_vision(self) -> bool:
        return False

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return 0

    def is_highground(self) -> bool:
        return False


@dataclasses.dataclass
class Hex(Modifiable, HasStatuses, Serializable):
    position: CC
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

    @modifiable
    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_in_penalty_for(unit)

    @modifiable
    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_out_penalty_for(unit)

    @modifiable
    def blocks_vision_for(self, player: Player) -> bool:
        if self.terrain.blocks_vision():
            return True
        if unit := self.map.unit_on(self):
            return unit.blocks_vision_for(player)
        return False

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return self.terrain.get_terrain_protection_for(request)

    # TODO
    # def serialize_values(self, context: SerializationContext) -> JSON:
    #     pass

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "cc": {
                "r": self.position.r,
                "h": self.position.h,
            },
            "terrain": self.terrain.__class__.__name__,
            "visible": (visible := GS().vision_map[context.player][self.position]),
            "unit": (
                (unit.serialize(context) if (unit := self.map.unit_on(self)) else None)
                if visible
                else None
            ),
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self):
        return f"{type(self).__name__}({self.position.r}, {self.position.h})"


@dataclasses.dataclass
class OneOfHexes(TargetProfile[Hex]):
    hexes: list[Hex]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"options": [_hex.position.serialize() for _hex in self.hexes]}

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
        for _hex in self.hexes.values():
            _hex.terrain.create_effects(_hex)
        self.unit_positions: bidict[Unit, Hex] = bidict()

    def units_controlled_by(self, player: Player) -> Iterator[Unit]:
        for unit in self.unit_positions.keys():
            if unit.controller == player:
                yield unit

    def move_unit_to(self, unit: Unit, space: Hex) -> None:
        if self.unit_positions.inverse.get(space) is not None:
            raise MovementException()
        self.unit_positions[unit] = space

    def remove_unit(self, unit: Unit) -> None:
        del self.unit_positions[unit]

    def unit_on(self, space: Hex) -> Unit | None:
        return self.unit_positions.inverse.get(space)

    # TODO maybe called hex off?
    def position_of(self, unit: Unit) -> Hex:
        return self.unit_positions[unit]

    def get_neighbors_off(self, off: CC | Unit) -> Iterator[Hex]:
        for neighbor_coordinate in (
            self.unit_positions[off].position if isinstance(off, Unit) else off
        ).neighbors():
            if _hex := self.hexes.get(neighbor_coordinate):
                yield _hex

    def get_neighboring_units_off(
        self, off: CC | Unit, controlled_by: Player | None = None
    ) -> Iterator[Unit]:
        for _hex in self.get_neighbors_off(off):
            if unit := self.unit_positions.inverse.get(_hex):
                if controlled_by is None or controlled_by == unit.controller:
                    yield unit

    def get_units_within_range_off(
        self, off: CC | Unit, distance: int
    ) -> Iterator[Unit]:
        for _hex in hex_circle(
            distance,
            center=self.unit_positions[off].position if isinstance(off, Unit) else off,
        ):
            if _hex in self.hexes and (
                unit := self.unit_positions.inverse.get(self.hexes[_hex])
            ):
                yield unit

    def serialize(self, context: SerializationContext) -> JSON:
        return {"hexes": [_hex.serialize(context) for _hex in self.hexes.values()]}


@dataclasses.dataclass
class ActiveUnitContext(Serializable):
    unit: Unit
    movement_points: int
    has_acted: bool = False
    should_stop: bool = False
    activated_facets: defaultdict[str, int] = dataclasses.field(
        default_factory=lambda: defaultdict(int)
    )

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "unit": self.unit.serialize(context),
            "movement_points": self.movement_points,
            # 'has_acted': self.has_acted,
        }


class GameState:
    instance: GameState | None = None

    def __init__(
        self,
        player_count: int,
        # interface_class: type[Interface],
        connection_class: type[Connection],
        landscape: Landscape,
    ):
        self.turn_order = TurnOrder(
            [Player(f"player {i+1}") for i in range(player_count)]
        )
        # TODO this is really dumb, do this in a better way (want p1 to start).
        # self.turn_order.advance()
        # self.interfaces = {
        #     player: interface_class() for player in self.turn_order.players
        # }
        self.connections = {
            player: connection_class(player) for player in self.turn_order.players
        }
        # self.map = HexMap(settings.map_spec.generate_landscape())
        self.map = HexMap(landscape)
        self.active_unit_context: ActiveUnitContext | None = None
        # self.points: dict[Player]
        self.target_points = 10
        self.round_counter = 0

        # TODO move to player
        # self._id_map = IDMap()
        self.id_maps: dict[Player, IDMap] = {
            player: IDMap() for player in self.turn_order.players
        }

        self.vision_obstruction_map: dict[Player, dict[CC, bool]] = {}
        self.vision_map: dict[Player, dict[CC, bool]] = {}

        # TODO for debugging
        self._event_log: list[str] = []
        ES.register_event_callback(EventLogger(self._event_log.append))

    def update_vision(self) -> None:
        for player in self.turn_order.players:
            self.vision_obstruction_map[player] = {
                position: _hex.blocks_vision_for(player)
                for position, _hex in self.map.hexes.items()
            }

            self.vision_map[player] = {
                position: any(
                    unit.can_see(_hex) for unit in self.map.units_controlled_by(player)
                )
                for position, _hex in self.map.hexes.items()
            }

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        v = {
            # "game_state": {
            #     "players": {},
            #     "round": self.round_counter,
            #     "map": self.map.serialize(context),
            # },
            "player": context.player.name,
            "players": {},
            "round": self.round_counter,
            "map": self.map.serialize(context),
            "decision": decision_point.serialize(context) if decision_point else None,
            "active_unit_context": (
                self.active_unit_context.serialize(context)
                if self.active_unit_context
                else None
            ),
            # TODO for debugging
            "event_log": self._event_log,
        }
        # TODO lmao
        context.id_map.prune()
        return v

    def make_decision(self, player: Player, decision_point: DecisionPoint[O]) -> O:
        # self.update_vision()
        for _player in self.turn_order.players:
            if _player != player:
                self.connections[_player].send(
                    self.serialize_for(
                        SerializationContext(_player, self.id_maps[_player]), None
                    )
                )
        response = self.connections[player].get_response(
            self.serialize_for(
                SerializationContext(player, self.id_maps[player]), decision_point
            )
        )
        # TODO
        print("response in game state", response)
        return decision_point.parse_response(response)


# TODO
def GS() -> GameState:
    return GameState.instance
