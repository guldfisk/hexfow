from game.core import UnitBlueprint
from game.units.facets.activated_abilities import (
    Bloom,
    Grow,
    HealBeam,
    NothingStopsTheMail,
    InducePanic,
    Vault,
    BatonPass,
    SummonScarab,
    Sweep,
    Stare,
    Jaunt,
    Rouse,
    SummonBees,
    StimulatingInjection,
    Suplex,
    Lasso,
    RaiseShrine,
    GrantCharm,
    ChokingSoot,
    Terrorize,
    Scorch,
    FlameWall,
    Showdown,
    SmokeCanister,
    GreaseTheGears,
    VitalityTransfer,
    Shove,
    Poof,
    VenomousSpine,
    Scry,
)
from game.units.facets.attacks import (
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
    RoundhouseKick,
    EtherealSting,
    Stinger,
    GlassFist,
    DiamondFist,
    Slay,
    Tackle,
    FromTheTopRope,
    TwinRevolvers,
    BellHammer,
    SnappingBeak,
    OtterBite,
    HammerCannon,
    ScratchAndBite,
    Shiv,
    SerratedClaws,
)
from game.units.facets.static_abilities import (
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
    TelepathicSpy,
    CaughtInTheMatch,
    HeelTurn,
    Quick,
    GlassSkin,
    DiamondSkin,
    LastStand,
    ToxicPresence,
    FlameResistant,
    Diver,
    ScurryInTheShadows,
    JukeAndJive,
)
from game.values import Size


CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    facets=[Prickly, Immobile, Grow],
    price=1,
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
    price=1,
)

CHICKEN = UnitBlueprint(
    name="Chicken", health=2, speed=1, sight=1, size=Size.SMALL, facets=[Peck], price=1
)

LUMBERING_PILLAR = UnitBlueprint(
    name="Lumbering Pillar",
    health=7,
    speed=1,
    sight=0,
    armor=2,
    size=Size.LARGE,
    price=2,
)


LIGHT_ARCHER = UnitBlueprint(
    name="Light Archer",
    health=4,
    speed=3,
    sight=2,
    facets=[LightBow],
    price=3,
    max_count=3,
)

MARSHMALLOW_TITAN = UnitBlueprint(
    name="Marshmallow Titan",
    health=10,
    speed=2,
    sight=1,
    armor=-1,
    size=Size.LARGE,
    facets=[MarshmallowFist],
    price=3,
    max_count=2,
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

AP_GUNNER = UnitBlueprint(
    "AP Gunner", health=5, speed=2, sight=2, facets=[APGun], price=6, max_count=2
)


BUGLING = UnitBlueprint(
    "Bugling",
    health=4,
    speed=4,
    sight=2,
    size=Size.SMALL,
    facets=[BuglingClaw],
    price=5,
    max_count=3,
)


CYCLOPS = UnitBlueprint(
    "Cyclops",
    health=11,
    speed=3,
    size=Size.LARGE,
    sight=1,
    facets=[GiantClub, Sweep, Stare],
    price=15,
)


RHINO_BEAST = UnitBlueprint(
    "Rhino", health=10, speed=4, sight=2, size=Size.LARGE, facets=[Gore], price=15
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
    price=8,
)


GNOME_COMMANDO = UnitBlueprint(
    "Gnome Commando",
    health=4,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[GnomeSpear, TerrainSavvy],
    price=3,
    max_count=2,
)

ZONE_SKIRMISHER = UnitBlueprint(
    "ZONE Skirmisher",
    health=6,
    speed=3,
    sight=2,
    facets=[Blaster, Bayonet],
    price=2,
    max_count=2,
)


GOBLIN_ASSASSIN = UnitBlueprint(
    "Goblin Assassin",
    health=3,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[HiddenBlade, Stealth],
    price=4,
    max_count=2,
)


DIRE_WOLF = UnitBlueprint(
    "Dire Wolf", health=7, speed=4, sight=2, facets=[Bite, PackHunter], price=9
)


BULLDOZER = UnitBlueprint(
    "Bulldozer",
    health=11,
    speed=2,
    sight=1,
    size=Size.LARGE,
    armor=1,
    facets=[Pusher],
    price=9,
)


HORROR_SPAWN = UnitBlueprint(
    "Horror Spawn",
    health=3,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[SerratedBeak],
    price=None,
)

HORROR = UnitBlueprint(
    "Horror",
    health=7,
    speed=4,
    sight=2,
    energy=4,
    facets=[SerratedClaws, VenomousSpine],
    price=12,
)

WAR_HOG = UnitBlueprint(
    "War Hog", health=8, speed=3, sight=2, facets=[RazorTusk, Furious], price=11
)


MEDIC = UnitBlueprint(
    "Medic", health=4, speed=3, sight=2, energy=5, facets=[HealBeam], price=6
)

# bombard canon {6rr} x2
# health 4, movement 1, sight 1, M
# solid munition
#     ranged attack
#     4 damage, 4 range, no movement
#     stun this unit


BOMB_TRUCK = UnitBlueprint(
    "Bomb Truck",
    health=5,
    speed=3,
    sight=1,
    facets=[NothingStopsTheMail, Explosive],
    price=6,
)


CHAINSAW_SADIST = UnitBlueprint(
    "Chainsaw Sadist",
    health=7,
    speed=3,
    sight=2,
    facets=[Chainsaw, FightFlightFreeze, GrizzlyMurderer],
    price=13,
)


PESTILENCE_PRIEST = UnitBlueprint(
    "Pestilence Priest",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[SummonScarab, InducePanic, Schadenfreude],
    price=10,
)

SCARAB = UnitBlueprint(
    "Scarab",
    health=2,
    speed=2,
    armor=1,
    sight=1,
    size=Size.SMALL,
    facets=[Pinch],
    price=None,
)

SNAPPING_TURTLE = UnitBlueprint(
    "Snapping Turtle",
    health=2,
    speed=2,
    armor=1,
    sight=1,
    size=Size.SMALL,
    aquatic=True,
    facets=[SnappingBeak],
    price=2,
)


# TODO # - ignores move penalties on wet terrain
OTTER_SCOUT = UnitBlueprint(
    "Otter Scout",
    health=5,
    speed=3,
    sight=2,
    size=Size.SMALL,
    aquatic=True,
    facets=[OtterBite, Diver],
    price=4,
)


BLITZ_TROOPER = UnitBlueprint(
    "Blitz Trooper", health=6, speed=3, sight=2, facets=[LightBlaster, Strafe], price=10
)


EFFORTLESS_ATHLETE = UnitBlueprint(
    "Effortless Athlete",
    health=6,
    speed=3,
    sight=2,
    energy=4,
    facets=[RoundhouseKick, Vault, BatonPass, TerrainSavvy],
    price=8,
)


CAPRICIOUS_TRICKSTER = UnitBlueprint(
    "Capricious Trickster",
    health=6,
    speed=3,
    sight=2,
    energy=5,
    facets=[Shiv, Vault, Shove, Poof, JukeAndJive],
    price=11,
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

BLIND_ORACLE = UnitBlueprint(
    "Blind Oracle", health=2, speed=2, sight=0, energy=2, facets=[Scry], price=2
)

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


STIM_DRONE = UnitBlueprint(
    "Stim Drone",
    health=3,
    speed=2,
    sight=1,
    energy=3,
    size=Size.SMALL,
    facets=[StimulatingInjection],
    price=4,
)


# TODO how do resistance with current damage thingy, split into 2 events?
# glass golem {5} x2
# health 1, movement 3, armor 2, sight 2, M
# punch
#     melee attack
#     3 damage
# - greater resistance to damage from statuses

GLASS_GOLEM = UnitBlueprint(
    "Glass Golem",
    health=1,
    speed=3,
    armor=2,
    sight=2,
    facets=[GlassFist, GlassSkin],
    price=5,
)

# diamond golem {7} x2
# health 1, movement 3, armor 3, sight 2, M
# diamond fist
#     melee attack
#     4 damage
# - immune to damage from statuses

DIAMOND_GOLEM = UnitBlueprint(
    "Diamond Golem",
    health=1,
    speed=3,
    armor=3,
    sight=2,
    facets=[DiamondFist, DiamondSkin],
    price=9,
)

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

GIANT_SLAYER_MOUSE = UnitBlueprint(
    "Giant Slayer Mouse",
    health=5,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[Slay, LastStand],
    price=7,
)

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
    health=3,
    speed=1,
    sight=2,
    energy=6,
    size=Size.SMALL,
    facets=[EtherealSting, Jaunt],
    price=7,
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

BEE_SWARM = UnitBlueprint(
    "Bee Swarm",
    health=2,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[Stinger],
    price=None,
)

BEE_SHAMAN = UnitBlueprint(
    "Bee Shaman", health=4, speed=3, sight=2, energy=3, facets=[SummonBees], price=None
)

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
    "Telepath",
    health=5,
    speed=3,
    sight=0,
    energy=5,
    facets=[TelepathicSpy, Rouse],
    price=None,
)

# legendary wrestler {11pg} x1
# health 7, movement 3, sight 2, energy 4, M
# tackle
#     melee attack
#     2 damage
#     applies stumble
#         -1 movement point next activation
# from the top rope
#     melee attack
#     4 damage, -1 movement
#     +1 damage against units with stumble debuff
#     deals 2 non-lethal physical damage to this unit
# supplex
#     ability 3 energy, -2 movement
#     target M- adjacent unit
#     deals 3 melee damage and moves the target to the other side of this unit, if able.
# - caught in the match
#     enemies disengageging this units suffers -1 movement point
# - heel turn
#     when this unit receives 4 or more damage in a single instance, it gets, "they've got a still chari"
#         unstackable
#         +1 attack power


LEGENDARY_WRESTLER = UnitBlueprint(
    "Legendary Wrestler",
    health=7,
    speed=3,
    sight=2,
    energy=4,
    facets=[
        Tackle,
        FromTheTopRope,
        Suplex,
        CaughtInTheMatch,
        HeelTurn,
    ],
    price=11,
)

# notorious outlaw
# health 5, movement 3, sight 2, energy 3, M
# twin revolvers
#     2x repeatable ranged attack
#     2 damage, 3 range, -1 movement
# lasso
#     combineable ability 3 energy
#     target enemy unit 2 range LoS
#     -2 movement
#     applies rooted for 1 round
# showdown
#     ability 3 energy
#     target enemy unit 3 range LoS
#     no movement
#     hits the targeted unit with primary ranged attack twice
#     if it is still alive, it will first try to hit with it's primary ranged attack if it has one, if it doesn't or can't,
#     it will try to hit with it's primary melee attack.
#     if it hits this way, exhaust it
# - dash
#     when this unit ends it's turn, it may move one space (irregardless of movement points)

NOTORIOUS_OUTLAW = UnitBlueprint(
    "Notorious Outlaw",
    health=5,
    speed=3,
    sight=2,
    energy=3,
    facets=[
        TwinRevolvers,
        Lasso,
        Showdown,
        Quick,
    ],
    price=12,
)

# shrine keeper {5pp} x1
# health 4, movement 3, sight 2, 4 energy, S
# raise shrine
#     ability 3 energy, -2 movement
#     target hex 1 range
#     applies status shrine to terrain
#         units on this hex has +1 mana regen
#         whenever a unit within 1 range skips, heal it 1
#         whenever a unit enters this hex, apply buff fortified for 4 rounds
#             unstackable, refreshable
#             +1 max health
# lucky charm
#     ability 1 energy
#     target different allied unit 1 range
#     applies buff lucky charm for 3 rounds
#         unstackable, refreshable
#         if this unit would suffer exactly one damage, instead remove this buff
# clean up
#     combinable ability 2 energy, -2 movement
#     target hex 1 range
#     removes all statuses from hex

SHRINE_KEEPER = UnitBlueprint(
    "Shrine Keeper",
    health=4,
    speed=3,
    sight=2,
    energy=4,
    size=Size.SMALL,
    facets=[RaiseShrine, GrantCharm],
    price=5,
)


BELL_STRIKER_BRUTE = UnitBlueprint(
    "Bell-Striker Brute", health=8, speed=3, sight=2, facets=[BellHammer], price=10
)

# witch engine {13pp} x1
# health 7, movement 2, sight 2, energy, M
# choking soot
#     aoe ability 4 energy
#     aoe type hex size 1 range 3 NLoS
#     -1 movement
#     applies status soot to terrain for 2 rounds
#         unstackable, refreshable
#         blocks LoS
#         units on this space has -1 sight, to a minimum of 1
#         when a unit moves in, and at the end of each round, units on this hex receives 1 true damage
# terrify
#     ability 5 energy
#     4 range LoS
#     no movement
#     applies terrified for 2 rounds
#         unstackable, refreshable
#         if this unit is adjacent to an enemy unit, it's owner cannot round skip, and the only legal actions
#         of this units are to move away from any adjacent enemy units
# into the gears
#     ability
#     target adjacent allied unit
#     this unit heals equal to the the units heals and gains energy equal to its energy
#     kill the unit
# - withering presence
#     at the end of this units turn, it applies 1 poison to each adjacent unit
# - auro of paranoia
#     whenever an enemy unit within 4 range becomes the target of an allied ability, it suffers 1 true damage

WITCH_ENGINE = UnitBlueprint(
    "Witch Engine",
    health=7,
    speed=2,
    sight=2,
    energy=8,
    facets=[ChokingSoot, Terrorize, GreaseTheGears, ToxicPresence],
    price=13,
)


INFERNO_TANK = UnitBlueprint(
    "Inferno Tank",
    health=7,
    speed=2,
    sight=1,
    armor=1,
    energy=5,
    size=Size.LARGE,
    facets=[
        Scorch,
        FlameWall,
        FlameResistant,
    ],
    price=12,
)


ZONE_MECH = UnitBlueprint(
    "Zone Mech",
    health=8,
    speed=2,
    armor=1,
    sight=2,
    energy=4,
    size=Size.LARGE,
    facets=[HammerCannon, SmokeCanister],
    price=15,
)

# gate fiend {15wwwgpp} x1
# health 8, movement 2, sight 2, energy 4, M
# infernal blade
#     melee attack
#     4 damage
#     applies 2 burning
# open gate
#     ability 4 energy
#     two target hexes 4 range NLoS
#     no movement
#     applies linked status gate to both hexes for 3 rounds
#         units on this hex can move to linked hex as normal move action


BLOOD_CONDUIT = UnitBlueprint(
    "Blood Conduit",
    health=3,
    speed=3,
    sight=2,
    energy=3,
    facets=[VitalityTransfer],
    price=4,
)


RAT_SCOUT = UnitBlueprint(
    "Rat Scout",
    health=4,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[ScratchAndBite, ScurryInTheShadows],
    price=4,
    max_count=2,
)
