from __future__ import annotations

import itertools
import random
from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel
from pydantic._internal._model_construction import ModelMetaclass
from sqlalchemy import select

from game.core import HexSpec, Landscape, Scenario
from game.map.coordinates import CC
from game.map.geometry import hex_circle
from game.map.terrain import Forest, Hills, Magma, Plains, Water
from game.units.blueprints import *
from model.engine import SS
from model.grouping import get_grouping_meta, get_suffix_remover
from model.models import Map
from model.schemas import ScenarioSchema


class GameType(
    BaseModel,
    ABC,
    metaclass=get_grouping_meta(
        get_suffix_remover("GameType"), base_class=ModelMetaclass
    ),
):
    name: ClassVar[str]
    registry: ClassVar[dict[str, type[GameType]]]

    @abstractmethod
    def get_scenario(self) -> Scenario: ...


class TestGameType(GameType):
    def get_scenario(self) -> Scenario:
        landscape = Landscape(
            {
                cc: HexSpec(
                    random.choice(
                        [
                            Plains,
                            # Plains,
                            # Plains,
                            # Forest,
                            # Hills,
                            # Water,
                        ]
                    ),
                    cc.distance_to(CC(0, 0)) <= 1,
                )
                for cc in hex_circle(4)
            }
        )

        player_units = (
            (
                BLOOD_FEUD_WARLOCK,
                LIGHT_ARCHER,
            ),
            (
                RIFLE_INFANTRY,
                INFERNO_TANK,
                LUMBERING_PILLAR,
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


class RandomGameType(GameType):
    def get_scenario(self) -> Scenario:
        specs = [
            (CC(0, -1), True),
            (CC(0, 0), True),
            (CC(0, 1), True),
            (CC(0, -2), False),
            (CC(0, -3), False),
            (CC(0, 2), False),
            (CC(0, 3), False),
            (CC(-1, 0), True),
            (CC(-1, 1), True),
            (CC(1, 0), True),
            (CC(1, -1), True),
            (CC(-2, 1), False),
            (CC(2, -1), False),
            (CC(0, 4), False),
            (CC(0, -4), False),
            (CC(0, 5), False),
            (CC(0, -5), False),
            (CC(-1, -4), False),
            (CC(-2, -4), False),
            (CC(1, -5), False),
            (CC(2, -5), False),
            (CC(3, -6), False),
            (CC(-1, 5), False),
            (CC(-2, 6), False),
            (CC(1, 4), False),
            (CC(3, 3), False),
            (CC(2, 3), False),
            (CC(2, -6), False),
            (CC(2, 4), False),
            (CC(-2, -3), False),
            (CC(-2, 5), False),
            (CC(4, -7), False),
            (CC(4, -6), False),
            (CC(5, -7), False),
            (CC(4, 2), False),
            (CC(4, 3), False),
            (CC(5, 2), False),
            (CC(-3, 6), False),
            (CC(-4, 6), False),
            (CC(-4, 7), False),
            (CC(-5, 7), False),
            (CC(-3, -3), False),
            (CC(-4, -3), False),
            (CC(-4, -2), False),
            (CC(-5, -2), False),
            (CC(6, 2), False),
            (CC(6, 1), False),
            (CC(6, -7), False),
            (CC(6, -8), False),
            (CC(-6, -1), False),
            (CC(-6, -2), False),
            (CC(-6, 7), False),
            (CC(-6, 8), False),
            (CC(6, -1), False),
            (CC(6, -2), False),
            (CC(6, -3), False),
            (CC(6, -4), False),
            (CC(6, -5), False),
            (CC(6, -6), False),
            (CC(5, -6), False),
            (CC(5, -5), False),
            (CC(5, -3), False),
            (CC(5, -2), False),
            (CC(5, -1), False),
            (CC(5, 0), False),
            (CC(5, 1), False),
            (CC(6, 0), False),
            (CC(5, -4), False),
            (CC(4, -5), False),
            (CC(4, -4), False),
            (CC(4, -2), False),
            (CC(4, -1), True),
            (CC(4, 0), False),
            (CC(4, 1), False),
            (CC(3, 2), False),
            (CC(3, 1), False),
            (CC(3, -2), False),
            (CC(3, -3), False),
            (CC(3, -4), False),
            (CC(3, -5), False),
            (CC(2, -4), False),
            (CC(2, -3), False),
            (CC(2, -2), False),
            (CC(2, 0), False),
            (CC(2, 1), False),
            (CC(2, 2), False),
            (CC(1, 3), False),
            (CC(1, 2), False),
            (CC(1, 1), False),
            (CC(1, -2), False),
            (CC(1, -3), False),
            (CC(1, -4), False),
            (CC(-1, -3), False),
            (CC(-1, -1), False),
            (CC(-1, 2), False),
            (CC(-1, 3), False),
            (CC(-2, 4), False),
            (CC(-2, 3), False),
            (CC(-2, 0), False),
            (CC(-2, -1), False),
            (CC(-3, -1), False),
            (CC(-2, -2), False),
            (CC(-3, -2), False),
            (CC(-3, 1), False),
            (CC(-4, 3), True),
            (CC(-3, 3), False),
            (CC(-4, 4), False),
            (CC(-3, 2), False),
            (CC(-3, 5), False),
            (CC(-4, 5), False),
            (CC(-4, 2), False),
            (CC(-4, 1), True),
            (CC(-5, 4), False),
            (CC(-5, 2), False),
            (CC(-5, 1), False),
            (CC(-5, 3), False),
            (CC(-5, 0), False),
            (CC(-5, 5), False),
            (CC(-5, 6), False),
            (CC(-6, 6), False),
            (CC(-6, 5), False),
            (CC(-6, 3), False),
            (CC(-6, 2), False),
            (CC(-6, 4), False),
            (CC(-6, 1), False),
            (CC(-6, 0), False),
            (CC(-5, -1), False),
            (CC(-4, -1), False),
            (CC(-4, 0), False),
            (CC(-3, 0), False),
            (CC(-2, 2), False),
            (CC(-3, 4), False),
            (CC(-1, 4), False),
            (CC(3, 0), False),
            (CC(3, -1), False),
            (CC(4, -3), True),
            (CC(-1, -2), False),
        ]

        pairs: dict[frozenset[CC] : bool] = {
            frozenset((cc, CC(*(-v for v in cc)))): is_objective
            for cc, is_objective in specs
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

        spawn_area = [
            cc
            for cc in [
                CC(-6, 7),
                # CC(-6, 8),
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
                # CC(6, 2),
                CC(-6, 6),
                CC(-5, 6),
                CC(-4, 5),
                CC(-3, 4),
                CC(-2, 4),
                CC(-1, 3),
                CC(0, 3),
                CC(2, 2),
                CC(4, 1),
                CC(5, 0),
                CC(6, 0),
            ]
            if landscape.terrain_map[cc].terrain_type != Water
        ]

        min_random_unit_quantity = 9
        random_unt_quantity_threshold = 12
        point_threshold = random_unt_quantity_threshold * 7
        banned_units = {LOTUS_BUD, CACTUS, DIAMOND_GOLEM}

        unit_pool = [
            blueprint
            for blueprint in UnitBlueprint.registry.values()
            for _ in range(blueprint.max_count)
            if blueprint.price is not None and blueprint not in banned_units
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


class MapGameType(GameType):
    map_name: str

    def get_scenario(self) -> Scenario:
        return ScenarioSchema.model_validate(
            SS.scalar(select(Map.scenario).where(Map.name == self.map_name))
        ).get_scenario()
