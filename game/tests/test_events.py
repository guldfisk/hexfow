import dataclasses
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    ClassVar,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    TypeAlias,
    cast,
)

import pytest
from frozendict import frozendict

from debug_utils import dp
from events.eventsystem import ES, StateModifierEffect
from game.core import (
    GS,
    ActivateUnitOption,
    Connection,
    EffortOption,
    GameState,
    Hex,
    HexMap,
    HexSpec,
    Landscape,
    MeleeAttackFacet,
    MoveOption,
    Player,
    RangedAttackFacet,
    SkipOption,
    Terrain,
    Unit,
    UnitBlueprint,
)
from game.events import Hit, Round, SpawnUnit, Turn
from game.map.coordinates import CC
from game.map.geometry import hex_circle
from game.map.terrain import Plains, Water
from game.tests.conftest import TestScope
from game.tests.test_terrain import InstantDamageMagma
from game.tests.units import TEST_CHICKEN
from game.units.blueprints import (
    CACTUS,
    LIGHT_ARCHER,
    LUMBERING_PILLAR,
    MARSHMALLOW_TITAN,
)
from game.values import Size


JSON_DICT: TypeAlias = Mapping[str, Any]

Response: TypeAlias = JSON_DICT | Callable[[JSON_DICT, Player], JSON_DICT]

QueuedResponse: TypeAlias = (
    Response | tuple[Response, Callable[[JSON_DICT, Player], Any]]
)


class MockConnection(Connection):
    def __init__(self, player: Player):
        super().__init__(player)
        self.queued_responses: list[QueuedResponse] = []
        self.history: list[JSON_DICT] = []

    def queue_responses(self, *vs: QueuedResponse) -> None:
        self.queued_responses.extend(vs)

    def send(self, values: Mapping[str, Any]) -> None:
        self.history.append(values)

    def wait_for_response(self) -> Mapping[str, Any]:
        raise NotImplementedError()

    def get_response(self, values: Mapping[str, Any]) -> Mapping[str, Any]:
        self.history.append(values)
        if TestScope.log_game_states:
            dp(values, self.player)
        queues_response = self.queued_responses.pop(0)
        if isinstance(queues_response, tuple):
            response, asserter = queues_response
            asserter(values, self.player)
        else:
            response = queues_response
        return (
            response(values, self.player)
            if isinstance(response, Callable)
            else response
        )


def make_hex_terrain(_hex: Hex, terrain_type: type[Terrain]) -> None:
    _hex.terrain = terrain_type()
    _hex.terrain.create_effects(_hex)


class GSCheck(ABC):
    @abstractmethod
    def __call__(self, gs: JSON_DICT, player: Player) -> None:
        pass


@dataclasses.dataclass
class GSChecks:
    checks: list[GSCheck]

    @abstractmethod
    def __call__(self, gs: JSON_DICT, player: Player) -> None:
        for check in self.checks:
            check(gs, player)


@dataclasses.dataclass
class HasHexes(GSCheck):
    coordinates: Iterable[CC]

    def __call__(self, gs: JSON_DICT, player: Player) -> None:
        assert {frozendict(_hex["cc"]) for _hex in gs["map"]["hexes"]} == {
            frozendict(c.serialize()) for c in self.coordinates
        }


@dataclasses.dataclass
class HexesVisible(GSCheck):
    visible_coordinates: Iterable[CC]

    def __call__(self, gs: JSON_DICT, player: Player) -> None:
        visibles = {frozendict(c.serialize()) for c in self.visible_coordinates}

        target = {
            frozendict(_hex["cc"]): frozendict(_hex["cc"]) in visibles
            for _hex in gs["map"]["hexes"]
        }
        result = {
            frozendict(_hex["cc"]): _hex["visible"] for _hex in gs["map"]["hexes"]
        }

        if target != result:
            print("vision check error:")
            print("has vision but should not:")
            print(
                {c for c, v in result.items() if v}
                - {c for c, v in target.items() if v}
            )
            print("does have vision but should:")
            print(
                {c for c, v in target.items() if v}
                - {c for c, v in result.items() if v}
            )
            assert False


@dataclasses.dataclass
class HexesInvisible(GSCheck):
    invisible_coordinates: Iterable[CC]

    def __call__(self, gs: JSON_DICT, player: Player) -> None:
        # visibles = {frozendict(c.serialize()) for c in self.invisible_coordinates}

        target = {frozendict(c.serialize()): False for c in self.invisible_coordinates}
        result = {
            frozendict(_hex["cc"]): _hex["visible"]
            for _hex in gs["map"]["hexes"]
            if frozendict(_hex["cc"]) in target.keys()
        }

        if target != result:
            print("vision check error:")
            print("has vision but should not:")
            print(
                {c for c, v in result.items() if v}
                - {c for c, v in target.items() if v}
            )
            # print("does have vision but should:")
            # print(
            #     {c for c, v in target.items() if v}
            #     - {c for c, v in result.items() if v}
            # )
            assert False


class SelectionError(Exception):
    pass


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
        raise SelectionError()
        # options = {
        #     CC(**v["cc"]): idx for idx, v in enumerate(values["values"]["options"])
        # }
        # return {"index": options[self.coordinate]}


@dataclasses.dataclass
class OneOfUnitsSelector(TargetSelector):
    unit: Unit
    available_choices: Iterable[Unit] | None = None

    def select(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        # # TODO player etc
        # _id = GS2.id_maps[player].get_id_for(self.unit)
        # for idx, option in enumerate(values["values"]["units"]):
        #     if option["id"] == _id:
        #         return {"index": idx}

        options = {
            option["id"]: idx for idx, option in enumerate(values["values"]["units"])
        }

        if self.available_choices is not None:
            unit_choices = {
                player.id_map.get_id_for(unit): unit for unit in self.available_choices
            }
            try:
                assert options.keys() == unit_choices.keys()
            except AssertionError:
                print("Unexpected units available for selection:")
                print(
                    [
                        player.id_map.get_object_for(_id)
                        for _id in options.keys() - unit_choices.keys()
                    ]
                    # [unit_choices[_id] for _id in options.keys() - unit_choices.keys()]
                )
                print("Expected units not available for selection:")
                print(
                    [
                        player.id_map.get_object_for(_id)
                        for _id in unit_choices.keys() - options.keys()
                    ]
                )
                raise

        return {"index": options[player.id_map.get_id_for(self.unit)]}

        # raise ValueError("Blah")


class DecisionSelector(ABC):
    @abstractmethod
    def __call__(
        self, values: Mapping[str, Any], player: Player
    ) -> Mapping[str, Any]: ...


@dataclasses.dataclass
class OptionSelector(DecisionSelector):
    target_selector: TargetSelector | None = None

    @abstractmethod
    def should_select(self, option: Mapping[str, Any]) -> bool: ...

    def __call__(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
        for idx, option in enumerate(values["decision"]["payload"]["options"]):
            if self.should_select(option):
                return {
                    "index": idx,
                    "target": (
                        self.target_selector.select(option["target_profile"], player)
                        if self.target_selector is not None
                        else None
                    ),
                }
        raise SelectionError()


# @dataclasses.dataclass
class MoveOptionSelector(OptionSelector):
    def should_select(self, option: Mapping[str, Any]) -> bool:
        return option["type"] == MoveOption.__name__


class MeleeAttackSelector(OptionSelector):
    def should_select(self, option: Mapping[str, Any]) -> bool:
        return (
            option["type"] == EffortOption.__name__
            and option["values"]["facet"]["category"] == MeleeAttackFacet.category
        )


class RangedAttackSelector(OptionSelector):
    def should_select(self, option: Mapping[str, Any]) -> bool:
        return (
            option["type"] == EffortOption.__name__
            and option["values"]["facet"]["category"] == RangedAttackFacet.category
        )


class SkipOptionSelector(OptionSelector):
    def should_select(self, option: Mapping[str, Any]) -> bool:
        return option["type"] == SkipOption.__name__


# @dataclasses.dataclass
# class UnitSelector(DecisionSelector):
#     unit: Unit
#
#     def __call__(self, values: Mapping[str, Any], player: Player) -> Mapping[str, Any]:
#         _id = GS2.id_maps[player].get_id_for(self.unit)
#         for idx, option in enumerate(values["decision"]["payload"]["units"]):
#             if option["id"] == _id:
#                 return {"index": idx}
#         raise ValueError("blah")


@dataclasses.dataclass
class ActivateSelector(OptionSelector):
    def should_select(self, option: Mapping[str, Any]) -> bool:
        return option["type"] == ActivateUnitOption.__name__


def select_hex(coordinate: CC, values: Mapping[str, Any]) -> Mapping[str, Any]:
    options = {CC(**v["cc"]): idx for idx, v in enumerate(values["values"]["options"])}
    return {"index": options[coordinate]}


def generate_hex_landscape(
    radius: int = 2, terrain_type: type[Terrain] = Plains
) -> Landscape:
    return Landscape({cc: HexSpec(terrain_type, False) for cc in hex_circle(radius)})


@pytest.fixture
def ground_landscape() -> Landscape:
    return generate_hex_landscape()


@pytest.fixture
def game_state(ground_landscape: Landscape) -> Iterator[GameState]:
    gs = GameState(2, MockConnection, ground_landscape)
    # GameState.instance = gs
    GS.bind(gs)
    yield gs
    for interface in gs.connections.values():
        assert not cast(MockConnection, interface).queued_responses


@pytest.fixture
def player1(game_state: GameState) -> Player:
    return game_state.turn_order.original_order[0]


@pytest.fixture
def player1_connection(game_state: GameState, player1: Player) -> MockConnection:
    return game_state.connections[player1]


@pytest.fixture
def player2(game_state: GameState) -> Player:
    return game_state.turn_order.original_order[1]


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


def test_attack(unit_spawner: UnitSpawner) -> None:
    chicken = unit_spawner.spawn(TEST_CHICKEN)
    cactus = unit_spawner.spawn(CACTUS)

    ES.resolve(
        Hit(attacker=chicken, defender=cactus, attack=chicken.get_primary_attack())
    )
    ES.resolve_pending_triggers()

    assert cactus.damage == 1
    assert chicken.damage == 2


def test_move(unit_spawner: UnitSpawner, player1_connection: MockConnection) -> None:
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    player1_connection.queue_responses(
        MoveOptionSelector(OneOfHexesSelector(CC(1, -1)))
    )
    ES.resolve(Turn(chicken))
    assert GS.map.unit_positions[chicken].position == CC(1, -1)


def test_move_is_blocked(
    unit_spawner: UnitSpawner, player1_connection: MockConnection
) -> None:
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(1, -1))
    player1_connection.queue_responses(
        MoveOptionSelector(OneOfHexesSelector(CC(1, -1)))
    )
    with pytest.raises(SelectionError):
        ES.resolve(Turn(chicken))


def test_move_fails(
    unit_spawner: UnitSpawner, player2: Player, player1_connection: MockConnection
) -> None:
    pillar = unit_spawner.spawn(LUMBERING_PILLAR, coordinate=CC(0, 0))
    unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(1, -1), controller=player2)
    player1_connection.queue_responses(
        MoveOptionSelector(OneOfHexesSelector(CC(1, -1)))
    )
    # with pytest.raises(SelectionError):
    ES.resolve(Turn(pillar))
    assert GS.map.unit_positions[pillar].position == CC(0, 0)


def test_fight(
    unit_spawner: UnitSpawner,
    player2: Player,
    player1_connection: MockConnection,
    player2_connection: MockConnection,
) -> None:
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    evil_chicken = unit_spawner.spawn(
        TEST_CHICKEN, controller=player2, coordinate=CC(1, -1)
    )
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(chicken)),
        MeleeAttackSelector(OneOfUnitsSelector(evil_chicken)),
        ActivateSelector(OneOfUnitsSelector(chicken)),
        MeleeAttackSelector(OneOfUnitsSelector(evil_chicken)),
        MoveOptionSelector(OneOfHexesSelector(CC(1, -1))),
    )
    player2_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(evil_chicken)),
        MeleeAttackSelector(OneOfUnitsSelector(chicken)),
    )

    ES.resolve(Round())
    assert chicken.health == 1
    assert evil_chicken.health == 1
    assert GS.map.unit_positions[chicken].position == CC(0, 0)
    assert GS.map.unit_positions[evil_chicken].position == CC(1, -1)
    ES.resolve(Round())
    assert evil_chicken.health == 0
    assert chicken.health == 1
    assert GS.map.unit_positions[chicken].position == CC(1, -1)
    assert GS.map.unit_positions.get(evil_chicken) is None

    assert len(player1_connection.history) == 7


def test_ranged_attack(
    unit_spawner: UnitSpawner,
    player2: Player,
    player1_connection: MockConnection,
    player2_connection: MockConnection,
) -> None:
    archer = unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(0, 0))
    evil_archer = unit_spawner.spawn(
        LIGHT_ARCHER, coordinate=CC(0, 2), controller=player2
    )

    # Shoots enemy archer.
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(archer)),
        RangedAttackSelector(
            OneOfUnitsSelector(evil_archer, available_choices=[evil_archer])
        ),
    )
    player2_connection.queue_responses(SkipOptionSelector())
    ES.resolve(Round())
    assert archer.damage == 0
    assert evil_archer.damage == 1

    # A different enemy archer is spawned in between the two archers, blocking
    # vision of the original enemy archer.
    # We shoot the new one instead.
    different_evil_archer = unit_spawner.spawn(
        LIGHT_ARCHER, coordinate=CC(0, 1), controller=player2
    )
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(archer)),
        RangedAttackSelector(
            OneOfUnitsSelector(
                different_evil_archer,
                # Only new one is available to be shot.
                available_choices=[different_evil_archer],
            )
        ),
    )
    player2_connection.queue_responses(SkipOptionSelector())
    player2_connection.queue_responses(SkipOptionSelector())
    ES.resolve(Round())
    assert archer.damage == 0
    assert evil_archer.damage == 1
    assert different_evil_archer.damage == 1

    @dataclasses.dataclass(eq=False)
    class Shrink(StateModifierEffect[Unit, None, Size]):
        priority: ClassVar[int] = 1
        target: ClassVar[object] = Unit.size

        unit: Unit

        def should_modify(self, obj: Unit, request: None, value: Size) -> bool:
            return obj == self.unit

        def modify(self, obj: Unit, request: None, value: Size) -> Size:
            return Size.SMALL

    # The new archer is shrunk, causing it to no longer block vision, so we shoot
    # the original one instead.
    ES.register_effect(Shrink(different_evil_archer))
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(archer)),
        RangedAttackSelector(
            OneOfUnitsSelector(
                evil_archer,
                # Both enemy archers are available to be shot now.
                available_choices=[different_evil_archer, evil_archer],
            )
        ),
    )
    player2_connection.queue_responses(SkipOptionSelector())
    player2_connection.queue_responses(SkipOptionSelector())
    ES.resolve(Round())
    assert archer.damage == 0
    assert evil_archer.damage == 2
    assert different_evil_archer.damage == 1


def test_armor(unit_spawner: UnitSpawner, player2: Player):
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    evil_pillar = unit_spawner.spawn(
        LUMBERING_PILLAR, coordinate=CC(0, 1), controller=player2
    )
    evil_marshmallow = unit_spawner.spawn(
        MARSHMALLOW_TITAN, coordinate=CC(1, 0), controller=player2
    )
    ES.resolve(Hit(chicken, evil_pillar, chicken.attacks[0]))
    ES.resolve(Hit(chicken, evil_marshmallow, chicken.attacks[0]))

    assert evil_pillar.damage == 0
    assert evil_marshmallow.damage == 2


def test_round(unit_spawner, player1_connection: MockConnection) -> None:
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    player1_connection.queue_responses(
        (
            ActivateSelector(OneOfUnitsSelector(chicken)),
            GSChecks([HasHexes(hex_circle(2)), HexesVisible(hex_circle(1))]),
        ),
        (
            MoveOptionSelector(OneOfHexesSelector(CC(1, 0))),
            HexesVisible(hex_circle(1)),
        ),
        ActivateSelector(OneOfUnitsSelector(chicken)),
        (
            MoveOptionSelector(OneOfHexesSelector(CC(0, 0))),
            HexesVisible(hex_circle(1, center=CC(1, 0))),
        ),
    )
    ES.resolve(Round())
    assert GS.map.unit_positions[chicken].position == CC(1, 0)
    assert chicken.exhausted is True
    ES.resolve(Round())
    assert GS.map.unit_positions[chicken].position == CC(0, 0)
    assert chicken.exhausted is True


def test_vision_blocked(
    unit_spawner, player1_connection: MockConnection, player2: Player
) -> None:
    def _check(visible_hexes: Collection[CC]):
        player1_connection.queue_responses(
            (SkipOptionSelector(), HexesVisible(visible_hexes)),
        )
        ES.resolve(Turn(archer))

    # Only allied archer, which has a sight 2, and can see the whole map.
    archer = unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(0, 0))
    _check(hex_circle(2))

    # Spawn adjacent enemy archer which blocks vision of the space
    # immediately behind it.
    unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(1, 0), controller=player2)
    _check(set(hex_circle(2, center=CC(0, 0))) - {CC(2, 0)})

    # Spawning another enemy archer adjacent to both blocks vision, both behind
    # that one, and the space "in-between" behind the two archers.
    unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(1, -1), controller=player2)
    _check(set(hex_circle(2, center=CC(0, 0))) - {CC(2, 0), CC(2, -2), CC(2, -1)})

    # Spawning an enemy chicken has no effect, since small units does not block
    # vision.
    unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, -1), controller=player2)
    _check(set(hex_circle(2, center=CC(0, 0))) - {CC(2, 0), CC(2, -2), CC(2, -1)})

    # Spawn allied archer that can see behind one of the enemy ones.
    different_allied_archer = unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(0, 1))
    _check(set(hex_circle(2, center=CC(0, 0))) - {CC(2, -2), CC(2, -1)})

    # Allied large units blocks vision (pillar is itself blind).
    unit_spawner.spawn(LUMBERING_PILLAR, coordinate=CC(-1, 0))
    _check(set(hex_circle(2, center=CC(0, 0))) - {CC(2, -2), CC(2, -1), CC(-2, 0)})

    @dataclasses.dataclass(eq=False)
    class CapVision(StateModifierEffect[Unit, None, int]):
        priority: ClassVar[int] = 1
        target: ClassVar[object] = Unit.sight

        unit: Unit
        value: int

        def should_modify(self, obj: Unit, request: None, value: int) -> bool:
            return obj == self.unit

        def modify(self, obj: Unit, request: None, value: int) -> int:
            return min(value, self.value)

    # Reducing the sight of the archers affects the vision.
    ES.register_effect(CapVision(archer, 1))
    ES.register_effect(CapVision(different_allied_archer, 0))
    _check(hex_circle(1))


def test_impassable_terrain(
    unit_spawner, player1_connection: MockConnection, player2: Player
) -> None:
    make_hex_terrain(GS.map.hexes[CC(0, 1)], Water)
    chicken = unit_spawner.spawn(TEST_CHICKEN, coordinate=CC(0, 0))
    player1_connection.queue_responses(MoveOptionSelector(OneOfHexesSelector(CC(0, 1))))
    with pytest.raises(SelectionError):
        ES.resolve(Turn(chicken))
    assert GS.map.unit_positions[chicken].position == CC(0, 0)


def test_walk_onto_magma(
    unit_spawner, player1_connection: MockConnection, player2: Player
) -> None:
    make_hex_terrain(GS.map.hexes[CC(0, 1)], InstantDamageMagma)
    archer = unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(0, 0))
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(archer)),
        MoveOptionSelector(OneOfHexesSelector(CC(0, 1))),
        SkipOptionSelector(),
    )
    ES.resolve(Round())
    assert GS.map.unit_positions[archer].position == CC(0, 1)

    assert archer.damage == 2


def test_unit_dies_mid_turn(
    unit_spawner: UnitSpawner, player1_connection: MockConnection, player2: Player
) -> None:
    make_hex_terrain(GS.map.hexes[CC(0, 1)], InstantDamageMagma)
    archer = unit_spawner.spawn(LIGHT_ARCHER, coordinate=CC(0, 0))
    archer.damage = archer.max_health.g() - 1
    player1_connection.queue_responses(
        ActivateSelector(OneOfUnitsSelector(archer)),
        MoveOptionSelector(OneOfHexesSelector(CC(0, 1))),
    )
    ES.resolve(Round())
    assert not archer.on_map()
