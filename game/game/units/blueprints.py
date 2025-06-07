from events.eventsystem import ES
from game.game.core import UnitBlueprint, ActivatedAbilityFacet, Hex, OneOfHexes, GS
from game.game.decisions import TargetProfile
from game.game.events import SpawnUnit
from game.game.map.coordinates import line_of_sight_obstructed
from game.game.units.facets.activated_abilities import (
    Bloom,
    Grow,
    HealBeam,
    Suicide,
    InducePanic,
)
from game.game.units.facets.attacks import (
    Peck,
    MarshmallowFist,
    LightBow,
    APGun,
    BuglingClaw,
    GiantClub,
    HurlBoulder,
    Gore,
    HiddenBlade,
    Bite,
    GnomeSpear,
    RazorTusk,
    Chainsaw,
    Blaster,
    Bayonet,
    Pinch,
    Strafe,
    LightBlaster,
)
from game.game.units.facets.static_abilities import (
    Prickly,
    Immobile,
    Farsighted,
    PackHunter,
    Nourishing,
    Pusher,
    TerrainSavvy,
    Furious,
    Stealth,
    FightFlightFreeze,
    Explosive,
)
from game.game.values import Size

# cactus {1} x1
# health 3, movement 0, sight 0, energy 0/2, M
# grow
#     ability 2 energy
#     heals 1
# - units melee attacking this unit suffers 2 damage
# - immobile

CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    facets=[Prickly, Immobile, Grow],
)

# lotus bud {1p} x1
# health 3, movement 0, sight 0, energy 0/2, S
# bloom
#     ability 2 energy
#     this units dies
#     heals each adjacent unit 1
#  - immobile
#  - allied units can move unto this unit. when they do, this unit dies, and the allied unit is healed 1.

LOTUS_BUD = UnitBlueprint(
    name="Lotus Bud",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    size=Size.SMALL,
    facets=[Immobile, Nourishing, Bloom],
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

RHINO_BEAST = UnitBlueprint(
    "Rhino", health=10, speed=4, sight=2, size=Size.LARGE, facets=[Gore]
)

BOULDER_HURLER_OAF = UnitBlueprint(
    "Boulder Hurler Oaf",
    health=9,
    speed=3,
    sight=2,
    size=Size.LARGE,
    facets=[
        HurlBoulder,
        Farsighted,
    ],
)

# gnome commando {3w} x2
# health 4, movement 3, sight 1, S
# spear
#     melee attack
#     2 damage
# - ignores first move penalty each turn


GNOME_COMMANDO = UnitBlueprint(
    "Gnome Commando",
    health=4,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[GnomeSpear, TerrainSavvy],
)

# zone skirmisher {5} x2
# health 6, movement 3, sight 2, M
# salvo
#     ranged attack
#     3 damage, 2 range, -1 movement
#     -1 damage against air
# engage
#     melee attack
#     3 damage

ZONE_SKIRMISHER = UnitBlueprint(
    "ZONE Skirmisher", health=6, speed=3, sight=2, facets=[Blaster, Bayonet]
)

# goblin assassin {4} x2
# health 3, movement 3, sight 2, S
# hidden blade
#     melee attack
#     1 damage
#     +1 damage against exhausted units
# - stealth


GOBLIN_ASSASSIN = UnitBlueprint(
    "Goblin Assassin",
    health=3,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[HiddenBlade, Stealth],
)


# dire wolf {9w} x2
# health 7, movement 4, sight 2, M
# bite
#     melee attack
#     3 damage
# - pack hunter
#     when adjacent enemy unit is melee attacked by different allied unit, dire wolf also hits it.

DIRE_WOLF = UnitBlueprint(
    "Dire Wolf", health=7, speed=4, sight=2, facets=[Bite, PackHunter]
)


BULLDOZER = UnitBlueprint(
    "Bulldozer", health=11, speed=2, sight=1, size=Size.LARGE, armor=1, facets=[Pusher]
)

# horror {12wp} x1
# health 7, movement 4, sight 2, energy 4, M
# inject
#     melee attack
#     4 damage, -1 movement
#     applies horror parasite to damaged target
#         unstackable
#         when this unit dies, summon exhausted horror spawn under debuff controllers control on this hex. if hex is occupied by just followed up attacker, instead spawns on hex attacker attacked from.
# venomous spine
#     ability 3 energy
#     target enemy unit 2 range LoS, -1 movement
#     applies horror parasite and (debilitating venom for 2 rounds) to target.
#         unstackable, refreshable
#         +1 move penalty
#         -1 attack power


WAR_HOG = UnitBlueprint(
    "War Hog", health=9, speed=3, sight=2, facets=[RazorTusk, Furious]
)


MEDIC = UnitBlueprint("Medic", health=5, speed=3, sight=2, energy=4, facets=[HealBeam])

# bombard canon {6rr} x2
# health 4, movement 1, sight 1, M
# solid munition
#     ranged attack
#     4 damage, 4 range, no movement
#     stun this unit


BOMB_TRUCK = UnitBlueprint(
    "Bomb Truck", health=5, speed=3, sight=1, facets=[Explosive, Suicide]
)

# chainsaw sadist {10p} x1
# health 7, movement 3, sight 2, M
# chainsaw
#     melee attack
#     3 damage, -1 movement
#     +2 damage against unarmored
# - when this unit kills a unit with an attack, each enemy unit that could see it suffers terrified for 2 rounds.
#     stackable, refreshable
#     -1 attack power
# - adjacent enemy units can't take actions that aren't skip, attack this unit, or move away from this unit

CHAINSAW_SADIST = UnitBlueprint(
    "Chainsaw Sadist", health=7, speed=3, sight=2, facets=[Chainsaw, FightFlightFreeze]
)


# pestilence priest {10pp} x1
# health 5, movement 3, sight 2, energy 6, M
# summon scarab
#     ability 3 energy
#     target unoccupied hex range 3 LoS
#     -2 movement
#     summons exhausted scarab with ephemeral 3
# induce panic
#     ability 3 energy
#     target enemy unit range 3 LoS
#     -1 movement
#     applies panicked for 3 rounds
#         unstackable, refreshable
#         at the end of each round, this unit suffers pure damage equal to the number of adjacent units.
# - whenever an adjacent unit is damaged or debuffed, this unit regens 1 energy


# TODO this should not be here, but need to figure out how to work with dependency on blueprints
class SummonScarab(ActivatedAbilityFacet[Hex]):
    movement_cost = 2
    energy_cost = 3

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        return OneOfHexes(
            [
                _hex
                for _hex in GS().map.get_hexes_within_range_off(self.owner, 3)
                if GS().vision_map[self.owner.controller][_hex.position]
                and not line_of_sight_obstructed(
                    GS().map.position_of(self.owner).position,
                    _hex.position,
                    GS().vision_obstruction_map[self.owner.controller].get,
                )
                and (
                    (unit := GS().map.unit_on(_hex)) is None
                    or unit.is_hidden_for(self.owner.controller)
                )
            ]
        )

    def perform(self, target: Hex) -> None:
        ES.resolve(
            SpawnUnit(
                blueprint=SCARAB,
                controller=self.owner.controller,
                space=target,
                exhausted=True,
            )
        )


PESTILENCE_PRIEST = UnitBlueprint(
    "Pestilence Priest",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[SummonScarab, InducePanic],
)

SCARAB = UnitBlueprint(
    "Scarab", health=2, speed=2, armor=1, sight=1, size=Size.SMALL, facets=[Pinch]
)

BLITZ_TROOPER = UnitBlueprint(
    "Blitz Trooper", health=6, speed=3, sight=2, facets=[LightBlaster, Strafe]
)
