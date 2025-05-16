from game.game.core import UnitBlueprint
from game.game.units.facets.attacks import Peck, MarshmallowFist, LightBow
from game.game.units.facets.static_abilities import Prickly, Immobile
from game.game.values import Size


CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    facets=[Prickly, Immobile],
)

CHICKEN = UnitBlueprint(
    name="Chicken", health=2, speed=1, sight=1, size=Size.SMALL, facets=[Peck]
)

LUMBERING_PILLAR = UnitBlueprint(
    name="Lumbering Pillar", health=7, speed=1, sight=0, armor=2, size=Size.LARGE
)


LIGHT_ARCHER = UnitBlueprint(
    name="Light Archer", health=4, speed=3, sight=2, facets=[LightBow]
)

MARSHMALLOW_TITAN = UnitBlueprint(
    name="Marshmallow Titan",
    health=10,
    speed=2,
    sight=1,
    armor=-1,
    size=Size.LARGE,
    facets=[MarshmallowFist],
)
