from game.game.core import UnitBlueprint
from game.game.units.facets.attacks import Peck
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

CHICKEN = UnitBlueprint(name="Chicken", health=2, speed=1, sight=1, size=Size.SMALL, facets=[Peck])
