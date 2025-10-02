from game.core import MeleeAttackFacet, UnitBlueprint
from game.units.facets.attacks import LightBow
from game.units.facets.static_abilities import Immobile, Prickly
from game.values import Size


class Peck(MeleeAttackFacet):
    damage = 1


TEST_CHICKEN = UnitBlueprint(
    name="Test Chicken",
    health=2,
    speed=1,
    sight=1,
    size=Size.SMALL,
    facets=[Peck],
    price=1,
)

TEST_LIGHT_ARCHER = UnitBlueprint(
    name="Light Archer",
    health=4,
    speed=3,
    sight=2,
    facets=[LightBow],
    price=3,
)

TEST_CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    facets=[Prickly, Immobile],
    price=None,
)
