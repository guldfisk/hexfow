from game.game.core import UnitBlueprint
from game.game.units.facets.attacks import (
    Peck,
    MarshmallowFist,
    LightBow,
    APGun,
    BuglingClaw,
    GiantClub,
    HurlBoulder,
)
from game.game.units.facets.static_abilities import Prickly, Immobile, Farsighted
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

# ap rifle squad {6r} x2
# health 5, movement 2, sight 2, M
# ap rifle
#     ranged attack
#     3 damage, 3 range
#     1 ap
#     +1 damage against large
#     -1 damage against air
#     no movement

AP_GUNNER = UnitBlueprint("AP Gunner", health=5, speed=2, sight=2, facets=[APGun])


BUGLING = UnitBlueprint(
    "Bugling", health=4, speed=4, sight=2, size=Size.SMALL, facets=[BuglingClaw]
)

# cyclops {15gg} x1
# health 11, movement 3, sight 1, L
# club
#     melee attack
#     5 damage
# sweep
#     aoe attack
#     aoe type 3 consecutive adjacent hexes
#     4 melee damage, -1 movement
# stare
#     combinable aoe ability
#         aoe type radiating line length 4 FoV propagation
#         reveals hexes this action

CYCLOPS = UnitBlueprint(
    "Cyclops", health=11, speed=3, size=Size.LARGE, sight=1, facets=[GiantClub]
)

# rhino beast {15wwg} x1
# health 10, movement 4, sight 2, L
# gore
#     melee attack
#     4 damage
#     +2 damage if this unit was not adjacent to target at the beginning of turn


BOULDER_HURLER_OAF = UnitBlueprint(
    "Boulder Hurler Oaf",
    health=9,
    speed=3,
    sight=2,
    size=Size.LARGE,
    facets=[HurlBoulder, Farsighted],
)
