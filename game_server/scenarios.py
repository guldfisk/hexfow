import random

from game.core import Landscape, HexSpec, Scenario
from game.map.coordinates import CC
from game.map.geometry import hex_circle
from game.map.terrain import Plains, Forest
from game.units.blueprints import *


def get_test_scenario() -> Scenario:
    landscape = Landscape(
        {
            cc: HexSpec(
                random.choice([Plains, Forest]),
                cc.distance_to(CC(0, 0)) <= 1,
            )
            for cc in hex_circle(4)
        }
    )

    player_units = (
        (
            STAUNCH_IRON_HEART,
            MAD_SCIENTIST,
            INFERNO_TANK,
        ),
        (
            BLOOD_CONDUIT,
            CYCLOPS,
            WITCH_ENGINE,
            LIGHT_ARCHER,
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
