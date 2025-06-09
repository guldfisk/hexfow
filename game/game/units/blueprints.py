from game.game.core import UnitBlueprint
from game.game.units.facets.activated_abilities import (
    Bloom,
    Grow,
    HealBeam,
    Suicide,
    InducePanic,
    LeapFrog,
    BatonPass,
    SummonScarab,
    Sweep,
    Stare,
    Jaunt,
    Rouse,
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
    SerratedBeak,
    Inject,
    RoundhouseKick,
    Sting,
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
    Schadenfreude,
    GrizzlyMurderer,
    EggBearer,
    TelepathicSpy,
)
from game.game.values import Size


CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    facets=[Prickly, Immobile, Grow],
)


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


CYCLOPS = UnitBlueprint(
    "Cyclops",
    health=11,
    speed=3,
    size=Size.LARGE,
    sight=1,
    facets=[GiantClub, Sweep, Stare],
)


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


GNOME_COMMANDO = UnitBlueprint(
    "Gnome Commando",
    health=4,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[GnomeSpear, TerrainSavvy],
)

ZONE_SKIRMISHER = UnitBlueprint(
    "ZONE Skirmisher", health=6, speed=3, sight=2, facets=[Blaster, Bayonet]
)


GOBLIN_ASSASSIN = UnitBlueprint(
    "Goblin Assassin",
    health=3,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[HiddenBlade, Stealth],
)


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


HORROR_SPAWN = UnitBlueprint(
    "Horror Spawn",
    health=3,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[SerratedBeak, EggBearer],
)

HORROR = UnitBlueprint(
    "Horror", health=7, speed=4, sight=2, energy=4, facets=[Inject, EggBearer]
)

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


CHAINSAW_SADIST = UnitBlueprint(
    "Chainsaw Sadist",
    health=7,
    speed=3,
    sight=2,
    facets=[Chainsaw, FightFlightFreeze, GrizzlyMurderer],
)


PESTILENCE_PRIEST = UnitBlueprint(
    "Pestilence Priest",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[SummonScarab, InducePanic, Schadenfreude],
)

SCARAB = UnitBlueprint(
    "Scarab", health=2, speed=2, armor=1, sight=1, size=Size.SMALL, facets=[Pinch]
)

BLITZ_TROOPER = UnitBlueprint(
    "Blitz Trooper", health=6, speed=3, sight=2, facets=[LightBlaster, Strafe]
)


EFFORTLESS_ATHLETE = UnitBlueprint(
    "Effortless Athlete",
    health=6,
    speed=3,
    sight=2,
    energy=4,
    facets=[RoundhouseKick, LeapFrog, BatonPass, TerrainSavvy],
)

# anti-tank mine {1p} x2
# health 1, movement 1, sight 0, S
# deploy
#     ability
#     this unit dies leaving no corpse. apply status anti-tank mined to terrain
#         hidden
#         when L ground unit moves in, it suffers 3 damage with 2 ap, and remove this status.

# blind oracle {2p} x1
# health 2, movement 2, sight 0, energy 2/3, M
# vision
#     aoe ability 2 energy
#     aot type hex, 6 range, NLoS, no movement
#     applies revealed to hex for 1 round

# psy-synced null {4p} x2
# health 4, movement 3, sight 2, energy 3, M
# psionic synchronization
#     ability 2 energy
#     target allied unit 2 range NLoS
#     activates target

# blood conduit {4pp} x1
# health 3, movement 3, sight 2, energy 3, M
# vitality transfer
#     ability 2 energy
#     target two allied units 3 range LoS, -1 movement
#     transfers up to 3 health from one to the other

# stim drone {4pp} x1
# health 3, movement 2, sight 1, energy 3, S
# inject
#     ability 3 energy
#     target unit 1 range
#     ready target, it suffers 1 pure damage
#     this unit dies

# TODO how do resistance with current damage thingy, split into 2 events?
# glass golem {5} x2
# health 1, movement 3, armor 2, sight 2, M
# punch
#     melee attack
#     3 damage
# - greater resistance to damage from statuses

# diamond golem {7} x2
# health 1, movement 3, armor 3, sight 2, M
# diamond fist
#     melee attack
#     4 damage
# - immune to damage from statuses

# TODO look at this as well for damage changes
# inferno trooper {5} x2
# health 6, movement 3, sight 2, M
# flamethrower
#     ranged attack
#     3 damage, 1 range, -1 movement
#     armor piercing
#     ground only
#     deals damage in the form of burning

# TODO terrain statuses
# desolation trooper {6} x2
# health 6, movement 3, sight 2, energy 4, M
# beam
#     ranged attack
#     3 damage, 2 range, -1 movement
#     armor piercing
#     deals damage in the form of radiated
# desecrate ground
#     aoe ability 3 energy, -2 movement
#     aoe type hex size 1 centered on this unit
#     applies 2 radiated and radiation 1 to terrain
# - greater resistance to damage from radiated

# TODO dispells
# witch doctor {6pp} x1
# health 3, movement 3, sight 2, energy 5, M
# restore
#      ability 3 energy
#      target allied unit 3 range LoS
#      -1 movement
#      heals 3 health and dispel latest debuff
# evil eye
#     ability 2 energy
#     target enemy unit 3 range LoS
#     -2 movement
#     apply 1 poison

# giant slayer mouse {7} x1
# health 5, movement 3, sight 2, S
# slay
#     melee attack
#     3 damage
#     +2 damage against L
# - if health would be reduced below 1, instead reduce it to 1, dispel all debuffs and apply mortally wounded for 1 round
#     unstackable, unrefreshable
#     undispellable
#     dies when expires

# TODO how works in multiples/different controllers?
# cult brute {7wp} x1
# health 7, movement 3, sight 2, M
# ritual dagger
#     melee attack
#     3 damage
#     before damage, apply entangled doom to target
#         whenever this unit suffers damage not from entangled doom, each other allied unit with the entangled doom debuff suffers 1 pure damage
# - whenever an enemy unit with entangled doom dies, heals this unit 1 health


VOID_SPRITE = UnitBlueprint(
    "Void Sprite",
    health=5,
    speed=1,
    sight=2,
    energy=7,
    size=Size.SMALL,
    facets=[Sting, Jaunt],
)

# bee swarm {-}
# health 2, movement 3, sight 1, S
# sting
#     melee attack
#     2 damage
#     ignores terrain protection
# - flying
# - greater melee/ranged resistant

# bee shaman {7wrp} x2
# health 4, movement 3, sight 2, energy 3, S
# summon bees
#     ability 2 energy
#     target hex 2 range LoS, -2 movement
#     summons bee swarm with ephemeral duration 1 round
# royal jelly
#     ability 2 energy
#     target different allied unit 2 range LoS, -1 movement
#     heals 2 and restores 1 energy

# telepath {7pp} x1
# health 5, movement 3, sight 0, energy 5, M
# rouse
#     ability 3 energy
#     target other unit 3 range NLoS
#     -1 movement
#     activates target
# pacify
#     ability 3 energy
#     target other unit 3 range NLoS
#     -2 movement
#     applies pacified for 1 round
#         disarmed
#         +1 energy regen
# turn outwards
#     ability 3 energy
#     target other unit 2 range NLoS
#     -1 movement
#     applies far gazing for 2 rounds
#         +1 sight
#         cannot see adjacent hexes
# - adjacent enemy units also provide vision for this units controller

TELEPATH = UnitBlueprint(
    "Telepath", health=5, speed=3, sight=0, energy=5, facets=[TelepathicSpy, Rouse]
)
