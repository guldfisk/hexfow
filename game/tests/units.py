from game.core import MeleeAttackFacet, UnitBlueprint
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
