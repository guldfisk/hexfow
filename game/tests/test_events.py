import dataclasses
from ctypes.wintypes import PCHAR
from typing import TypeVar

import pytest

from events.eventsystem import ES
from game.game.core import (
    Terrain,
    HexMap,
    Landscape,
    GameState,
    UnitBlueprint,
    Unit,
    AttackFacet,
)
from game.game.events import SpawnUnit, MeleeAttack
from game.game.map.coordinates import CubeCoordinate
from game.game.map.terrain import Ground
from game.game.player import Player
from game.game.units.blueprints import CHICKEN, CACTUS
from game.game.units.facets.attacks import Peck


A = TypeVar("A")


def generate_hex_landscape(
    radius: int = 2, terrain_type: type[Terrain] = Ground
) -> Landscape:
    return Landscape(
        {
            CubeCoordinate(r, h): terrain_type
            for r in range(-radius, radius + 1)
            for h in range(-radius, radius + 1)
            if -radius <= -(r + h) <= radius
        }
    )


@pytest.fixture
def ground_landscape() -> Landscape:
    return generate_hex_landscape()


@pytest.fixture
def ground_map(ground_landscape: Landscape) -> HexMap:
    return HexMap(ground_landscape)


@pytest.fixture
def player() -> Player:
    return Player()


# @dataclasses.dataclass
class UnitSpawner:

    def __init__(self, hex_map: HexMap, default_player: Player):
        self.hex_map = hex_map
        self.default_player = default_player
        self.coordinates = list(hex_map.hexes.keys())
        self.cursor = 0

    def spawn(self, blueprint: UnitBlueprint, player: Player | None = None) -> Unit:
        units = list(
            ES.resolve(
                SpawnUnit(
                    blueprint=blueprint,
                    controller=player or self.default_player,
                    space=self.hex_map.hexes[self.coordinates[self.cursor]],
                )
            ).iter_type(SpawnUnit)
        )
        if not len(units) == 1:
            raise RuntimeError("Did not spawn exactly one unit")
        self.cursor += 1
        return units[0].result


@pytest.fixture
def unit_spawner(ground_map: HexMap, player: Player) -> UnitSpawner:
    return UnitSpawner(ground_map, player)


# @pytest.fixture
# def game_state() -> GameState:
#     GameState.instance = GameState()

# A = TypeVar("A", bound=AttackFacet)


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
