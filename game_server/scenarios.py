import itertools
import json
import random
from pathlib import Path

from game.core import (
    Landscape,
    HexSpec,
    Scenario,
    Terrain,
    HexStatusSignature,
    HexStatus,
)
from game.map.coordinates import CC
from game.map.geometry import hex_circle
from game.map.terrain import Plains, Forest, Hills, Water, Magma
from game.units.blueprints import *


def get_test_scenario() -> Scenario:
    landscape = Landscape(
        {
            cc: HexSpec(
                random.choice([Plains, Forest, Hills]),
                cc.distance_to(CC(0, 0)) <= 1,
            )
            for cc in hex_circle(4)
        }
    )

    player_units = (
        (
            TRACTOR,
            GIANT_TOAD,
            RIFLE_INFANTRY,
        ),
        (
            LEGENDARY_WRESTLER,
            LIGHT_ARCHER,
            RHINO_BEAST,
            RIFLE_INFANTRY,
        ),
    )

    ccs = sorted(
        landscape.terrain_map.keys(),
        key=lambda cc: (cc.distance_to(CC(0, 0)), cc.r, CC.h),
    )

    return Scenario(
        landscape=landscape,
        units=[{ccs.pop(0): v for v in values} for values in player_units],
    )


def get_simple_scenario() -> Scenario:
    landscape = Landscape(
        {
            cc: HexSpec(
                random.choice([Plains, Forest]),
                cc.distance_to(CC(0, 0)) <= 1,
            )
            for cc in hex_circle(3)
        }
    )

    player_units = (
        (LIGHT_ARCHER, LIGHT_ARCHER),
        (
            ZONE_SKIRMISHER,
            GNOME_COMMANDO,
        ),
    )

    ccs = sorted(
        landscape.terrain_map.keys(),
        key=lambda cc: (cc.distance_to(CC(0, 0)), cc.r, CC.h),
    )

    return Scenario(
        landscape=landscape,
        units=[{ccs.pop(0): v for v in values} for values in player_units],
    )


def get_playtest_scenario() -> Scenario:
    with open(Path(__file__).parent.resolve() / "scenario_spec.json", "r") as f:
        spec = json.load(f)

    landscape = Landscape(
        {
            CC(**hex_spec["cc"]): HexSpec(
                Terrain.registry[hex_spec["terrainType"]],
                hex_spec["isObjective"],
                statuses=[
                    HexStatusSignature(HexStatus.get(identifier), source=None)
                    for identifier in hex_spec["statuses"]
                ],
            )
            for hex_spec in spec.values()
        }
    )

    units = [
        {
            CC(**hex_spec["cc"]): UnitBlueprint.registry[hex_spec["unit"]["identifier"]]
            for hex_spec in spec.values()
            if hex_spec.get("unit") and hex_spec["unit"]["allied"] is allied
        }
        for allied in (False, True)
    ]

    return Scenario(
        landscape=landscape,
        units=units,
    )


def get_random_scenario() -> Scenario:
    # with open("/home/phdk/PycharmProjects/hexfow/game_server/scenario_spec.json", "r") as f:
    with open(Path(__file__).parent.resolve() / "scenario_spec.json", "r") as f:
        spec = json.load(f)

    pairs: dict[frozenset[CC] : bool] = {
        frozenset(
            (CC(**hex_spec["cc"]), CC(**{k: -v for k, v in hex_spec["cc"].items()}))
        ): hex_spec["isObjective"]
        for hex_spec in spec.values()
    }

    terrain_pool = (
        [Water] * 2 + [Magma] * 3 + [Plains] * 40 + [Forest] * 16 + [Hills] * 18
    )

    landscape = Landscape(
        dict(
            itertools.chain(
                *(
                    [(cc, HexSpec(terrain_type, is_objective)) for cc in pair]
                    for (pair, is_objective), terrain_type in zip(
                        pairs.items(), random.sample(terrain_pool, len(pairs))
                    )
                )
            )
        )
    )

    print(len(pairs))

    spawn_area = [
        cc
        for cc in [
            CC(-6, 7),
            CC(-6, 8),
            CC(-5, 6),
            CC(-5, 7),
            CC(-4, 6),
            CC(-4, 7),
            CC(-3, 5),
            CC(-3, 6),
            CC(-2, 5),
            CC(-2, 6),
            CC(-1, 4),
            CC(-1, 5),
            CC(0, 4),
            CC(0, 5),
            CC(1, 3),
            CC(1, 4),
            CC(2, 3),
            CC(2, 4),
            CC(3, 2),
            CC(3, 3),
            CC(4, 2),
            CC(4, 3),
            CC(5, 1),
            CC(5, 2),
            CC(6, 1),
            CC(6, 2),
        ]
        if landscape.terrain_map[cc].terrain_type != Water
    ]

    min_random_unit_quantity = 7
    random_unt_quantity_threshold = 12
    point_threshold = random_unt_quantity_threshold * 5
    banned_units = {LOTUS_BUD, CACTUS, DIAMOND_GOLEM}

    unit_pool = [
        blueprint
        for blueprint in UnitBlueprint.registry.values()
        for _ in range(blueprint.max_count)
        if blueprint.price is not None and not blueprint in banned_units
    ]
    random.shuffle(unit_pool)

    units = []

    # player_units = [[], []]

    while (
        len(units) < min_random_unit_quantity
        or sum(u.price for u in units) < point_threshold
    ) and not len(units) > random_unt_quantity_threshold:
        units.append(unit_pool.pop())

    print("points", sum(u.price for u in units))
    print("units", len(units))

    player_1_units = {}
    player_2_units = {}

    random.shuffle(spawn_area)

    for unit, position in zip(units, spawn_area):
        player_1_units[CC(-position.r, -position.h)] = unit
        player_2_units[position] = unit

    return Scenario(landscape, [player_1_units, player_2_units])
