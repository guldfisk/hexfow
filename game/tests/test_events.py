import dataclasses
from abc import abstractmethod, ABC
from typing import TypeVar, Mapping, Any, Callable, Iterator, cast

import pytest

from debug_utils import dp
from events.eventsystem import ES
from game.game.core import (
    Terrain,
    HexMap,
    Landscape,
    GameState,
    UnitBlueprint,
    Unit,
    AttackFacet,
    MoveOption,
    GS,
    EffortOption,
    MeleeAttackFacet,
)
from game.game.decisions import DecisionPoint, O, Option
from game.game.events import SpawnUnit, MeleeAttack, Turn, Round
from game.game.interface import Connection
from game.game.map.coordinates import CC
from game.game.map.terrain import Ground
from game.game.player import Player
from game.game.units.blueprints import CHICKEN, CACTUS
from game.game.units.facets.attacks import Peck


A = TypeVar("A")


class MockConnection(Connection):

    def __init__(self, player: Player):
        super().__init__(player)
        self.queued_responses = []
        self.history: list[Mapping[str, Any]] = []

    def queue_responses(
        self, *vs: Mapping[str, Any] | Callable[[Mapping[str, Any], Player], Mapping[str, Any]]
    ) -> None:
        self.queued_responses.extend(vs)

    def send(self, values: Mapping[str, Any]) -> None:
        self.history.append(values)

    def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
        self.history.append(values)
        dp(values)
        response = self.queued_responses.pop(0)
        return (
            response(values, self.player)
            if isinstance(response, Callable)
            else response
        )


class TargetSelector:

    @abstractmethod
    def select(
        self, values: Mapping[str, Any], player: Player
    ) -> Mapping[str, Any]: ...


@dataclasses.dataclass
class OneOfHexesSelector(TargetSelector):
    coordinate: CC

    def select(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        for idx, v in enumerate(values["values"]["options"]):
            if CC(**v) == self.coordinate:
                return {"index": idx}
        raise ValueError("blah")
        # options = {
        #     CC(**v["cc"]): idx for idx, v in enumerate(values["values"]["options"])
        # }
        # return {"index": options[self.coordinate]}


@dataclasses.dataclass
class OneOfUnitsSelector(TargetSelector):
    unit: Unit

    def select(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        # TODO player etc
        _id = GS().id_maps[player].get_id_for(self.unit)
        for idx, option in enumerate(values["values"]["units"]):
            if option["id"] == _id:
                return {"index": idx}
        raise ValueError("Blah")


class DecisionSelector(ABC):

    @abstractmethod
    def __call__(
        self, values: Mapping[str, Any], player: Player
    ) -> Mapping[str, Any]: ...


@dataclasses.dataclass
class OptionSelector(DecisionSelector):
    # option_type: type[Option]
    target_selector: TargetSelector

    @abstractmethod
    def should_select(self, option: Mapping[str, Any]) -> bool: ...

    def __call__(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        for idx, option in enumerate(values["decision"]["payload"]["options"]):
            # if option["type"] == self.option_type.__name__:
            if self.should_select(option):
                return {
                    "index": idx,
                    "target": self.target_selector.select(
                        option["target_profile"], player
                    ),
                }
        raise ValueError("blah")


# @dataclasses.dataclass
class MoveOptionSelector(OptionSelector):

    def should_select(self, option: Mapping[str, Any]) -> bool:
        return option["type"] == MoveOption.__name__


class MeleeAttackSelector(OptionSelector):

    def should_select(self, option: Mapping[str, Any]) -> bool:
        return (
            option["type"] == EffortOption.__name__
            and option["values"]["facet"]["type"] == MeleeAttackFacet.display_type
        )


@dataclasses.dataclass
class UnitSelector(DecisionSelector):
    unit: Unit

    def __call__(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        _id = GS().id_maps[player].get_id_for(self.unit)
        for idx, option in enumerate(values["decision"]["payload"]["units"]):
            if option["id"] == _id:
                return {"index": idx}
        raise ValueError("blah")


def select_hex(coordinate: CC, values: Mapping[str, Any]) -> Mapping[str, Any]:
    options = {CC(**v["cc"]): idx for idx, v in enumerate(values["values"]["options"])}
    return {"index": options[coordinate]}


def generate_hex_landscape(
    radius: int = 1, terrain_type: type[Terrain] = Ground
) -> Landscape:
    return Landscape(
        {
            CC(r, h): terrain_type
            for r in range(-radius, radius + 1)
            for h in range(-radius, radius + 1)
            if -radius <= -(r + h) <= radius
        }
    )


@pytest.fixture
def ground_landscape() -> Landscape:
    return generate_hex_landscape()


@pytest.fixture
def game_state(ground_landscape: Landscape) -> Iterator[GameState]:
    gs = GameState(2, MockConnection, ground_landscape)
    GameState.instance = gs
    yield gs
    for interface in gs.connections.values():
        assert not cast(MockConnection, interface).queued_responses


@pytest.fixture
def player1(game_state: GameState) -> Player:
    return game_state.turn_order.players[0]


@pytest.fixture
def player1_connection(game_state: GameState, player1: Player) -> MockConnection:
    return game_state.connections[player1]


@pytest.fixture
def player2(game_state: GameState) -> Player:
    return game_state.turn_order.players[1]


@pytest.fixture
def player2_connection(game_state: GameState, player2: Player) -> MockConnection:
    return game_state.connections[player2]


@pytest.fixture
def ground_map(game_state: GameState) -> HexMap:
    return game_state.map


class UnitSpawner:

    def __init__(self, hex_map: HexMap, default_player: Player):
        self.hex_map = hex_map
        self.default_controller = default_player
        self.coordinates = list(hex_map.hexes.keys())
        self.cursor = 0

    def spawn(
        self,
        blueprint: UnitBlueprint,
        controller: Player | None = None,
        coordinate: CC | None = None,
    ) -> Unit:
        units = list(
            ES.resolve(
                SpawnUnit(
                    blueprint=blueprint,
                    controller=controller or self.default_controller,
                    space=self.hex_map.hexes[
                        coordinate or self.coordinates[self.cursor]
                    ],
                )
            ).iter_type(SpawnUnit)
        )
        if not len(units) == 1:
            raise RuntimeError("Did not spawn exactly one unit")
        self.cursor += 1
        return units[0].result


@pytest.fixture
def unit_spawner(ground_map: HexMap, player1: Player) -> UnitSpawner:
    return UnitSpawner(ground_map, player1)


def get_attack(unit: Unit, attack_type: type[A]) -> A:
    for attack in unit.attacks:
        if isinstance(attack, attack_type):
            return attack
    raise ValueError(f"{unit} does not have attack {attack_type}")


def test_attack(unit_spawner: UnitSpawner) -> None:
    chicken = unit_spawner.spawn(CHICKEN)
    cactus = unit_spawner.spawn(CACTUS)

    ES.resolve(
        MeleeAttack(attacker=chicken, defender=cactus, attack=get_attack(chicken, Peck))
    )
    ES.resolve_pending_triggers()

    assert cactus.damage == 1
    assert chicken.damage == 2


def test_move(unit_spawner: UnitSpawner, player1_connection: MockConnection) -> None:
    chicken = unit_spawner.spawn(CHICKEN, coordinate=CC(0, 0))
    player1_connection.queue_responses(
        MoveOptionSelector(OneOfHexesSelector(CC(1, -1)))
    )
    ES.resolve(Turn(chicken))
    assert GS().map.unit_positions[chicken].position == CC(1, -1)


def test_fight(
    unit_spawner: UnitSpawner,
    player2: Player,
    player1_connection: MockConnection,
    player2_connection: MockConnection,
) -> None:
    chicken = unit_spawner.spawn(CHICKEN, coordinate=CC(0, 0))
    evil_chicken = unit_spawner.spawn(CHICKEN, controller=player2, coordinate=CC(1, -1))
    player1_connection.queue_responses(
        UnitSelector(chicken),
        MeleeAttackSelector(OneOfUnitsSelector(evil_chicken)),
        UnitSelector(chicken),
        MeleeAttackSelector(OneOfUnitsSelector(evil_chicken)),
    )
    player2_connection.queue_responses(
        UnitSelector(evil_chicken),
        MeleeAttackSelector(OneOfUnitsSelector(chicken))
    )

    ES.resolve(Round())
    assert chicken.health == 1
    assert evil_chicken.health == 1
    assert GS().map.unit_positions[chicken].position == CC(0, 0)
    assert GS().map.unit_positions[evil_chicken].position == CC(1, -1)
    ES.resolve(Round())
    assert chicken.health == 1
    assert evil_chicken.health == 0
    assert GS().map.unit_positions[chicken].position == CC(1, -1)
    assert GS().map.unit_positions.get(evil_chicken) is None

    assert len(player2_connection.history) == 6


def test_round(unit_spawner, player1_connection: MockConnection) -> None:
    chicken = unit_spawner.spawn(CHICKEN, coordinate=CC(0, 0))
    player1_connection.queue_responses(
        UnitSelector(chicken),
        MoveOptionSelector(OneOfHexesSelector(CC(1, 0))),
        UnitSelector(chicken),
        MoveOptionSelector(OneOfHexesSelector(CC(0, 0))),
    )
    ES.resolve(Round())
    assert GS().map.unit_positions[chicken].position == CC(1, 0)
    assert chicken.exhausted is True
    ES.resolve(Round())
    assert GS().map.unit_positions[chicken].position == CC(0, 0)
    assert chicken.exhausted is True


# def test_fight()