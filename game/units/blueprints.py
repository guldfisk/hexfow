from game.core import UnitBlueprint
from game.units.facets.activated_abilities import (
    AssembleTheDoombot,
    BatonPass,
    Binoculars,
    Bloom,
    ChokingSoot,
    ConstructTurret,
    CoordinatedManeuver,
    CriticalAid,
    CuringWord,
    EnfeeblingHex,
    Evacuate,
    FalseCure,
    FatalBonding,
    FixErUp,
    FlameThrower,
    FlameWall,
    FlashBang,
    GiantPincers,
    GrantCharm,
    GrantWish,
    GreaseTheGears,
    Grow,
    GuidedTrance,
    HandGrenade,
    HealBeam,
    Hitch,
    InducePanic,
    InkRing,
    InstilFocus,
    InternalStruggle,
    IronBlessing,
    Jaunt,
    Jump,
    Lasso,
    LayMine,
    MalevolentStare,
    MapOut,
    Mortar,
    OpenGate,
    Poof,
    PsychicCommand,
    PublicExecution,
    RaiseShrine,
    Riddle,
    Scorch,
    Scorn,
    Scry,
    SelfDestruct,
    ShootFlare,
    Shove,
    Showdown,
    ShrinkRay,
    SludgeBelch,
    SmokeCanister,
    SmokeGrenade,
    SowDiscord,
    SpiritProjection,
    SpurIntoRage,
    SquirtSoot,
    Stare,
    StimulatingInjection,
    SummonBees,
    SummonScarab,
    Suplex,
    SweatItOut,
    Sweep,
    Terrorize,
    TidyUp,
    Translocate,
    TurboTune,
    Vault,
    VenomousSpine,
    VitalityTransfusion,
    Vomit,
    WringEssence,
)
from game.units.facets.attacks import (
    AnkleBite,
    APGun,
    Bayonet,
    BellHammer,
    Bite,
    Blaster,
    BloodExpunge,
    BurningSting,
    Chainsaw,
    Chomp,
    CommandersPistol,
    CrushingMandibles,
    CrypticClaws,
    CurvedHorns,
    DancingSaber,
    DeathLaser,
    DiamondFist,
    DrainingGrasp,
    EtherealSting,
    FinalSting,
    FromTheTopRope,
    Frostbite,
    GiantClub,
    GlassFist,
    Gnaw,
    GnomeSpear,
    Gore,
    GranGransOlClub,
    Grapple,
    GuillotineAxe,
    HammerBlow,
    HammerCannon,
    HiddenBlade,
    HurlBoulder,
    InfernalBlade,
    LightBlaster,
    LightBow,
    MarshmallowFist,
    MightyBlow,
    MiniGun,
    OtterBite,
    Peck,
    Pinch,
    RazorTusk,
    Rifle,
    RifleSalvo,
    RoundhouseKick,
    Scratch,
    ScratchAndBite,
    SerratedBeak,
    SerratedClaws,
    ServicePistol,
    Shiv,
    Slay,
    Slice,
    SlingShot,
    SnappingBeak,
    SniperRifle,
    SolidMunition,
    Spew,
    Stinger,
    Strafe,
    StubbyClaws,
    SturdyClaws,
    Swelter,
    Tackle,
    TongueLash,
    TwinRevolvers,
    ViciousBite,
    Wrench,
)
from game.units.facets.static_abilities import (
    AntiMagicHide,
    Aquatic,
    Automated,
    CaughtInTheMatch,
    CrabShuffle,
    DiamondSkin,
    Diver,
    DreadfulVisage,
    Explosive,
    Farsighted,
    FightFlightFreeze,
    FlameResistant,
    Fleeting,
    FoulBurst,
    Furious,
    GlassSkin,
    GrizzlyMurderer,
    HeelTurn,
    Immobile,
    Inspiration,
    InspiringPresence,
    JukeAndJive,
    LastStand,
    MagicForm,
    Nourishing,
    OldBones,
    Ornery,
    PackHunter,
    Prickly,
    PuffAway,
    Pusher,
    Quick,
    Schadenfreude,
    ScurryInTheShadows,
    SlimyLocomotion,
    SlimySkin,
    SludgeTrail,
    SootDweller,
    Stakeout,
    Stealth,
    StrainedPusher,
    Swimmer,
    TelepathicSpy,
    TerrainSavvy,
    ToughSkin,
    ToxicPresence,
    ToxicSkin,
)
from game.values import Size


BLIND_GRUB = UnitBlueprint(
    name="Blind Grub",
    health=3,
    speed=3,
    sight=0,
    size=Size.SMALL,
    price=1,
)

BLIND_ORACLE = UnitBlueprint(
    "Blind Oracle",
    health=2,
    speed=2,
    sight=0,
    energy=2,
    facets=[Scry],
    price=1,
)

CHICKEN = UnitBlueprint(
    name="Chicken",
    health=2,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[Peck],
    price=1,
)

FIREFLY = UnitBlueprint(
    "Firefly",
    health=2,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[BurningSting, Fleeting],
    price=1,
)

HIVE_GUARD_GNAT = UnitBlueprint(
    "Hive-Guard Gnat",
    health=1,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[FinalSting],
    price=1,
)

UNBLINKING_WATCHER = UnitBlueprint(
    name="Unblinking Watcher",
    health=2,
    speed=1,
    sight=2,
    size=Size.SMALL,
    price=1,
)

CRAWLING_URCHIN = UnitBlueprint(
    name="Crawling Urchin",
    health=5,
    speed=1,
    sight=1,
    facets=[Prickly],
    price=2,
)

GOBLIN_SLINGSHOT = UnitBlueprint(
    "Goblin Slingshot",
    health=3,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[SlingShot],
    price=2,
)

LUMBERING_PILLAR = UnitBlueprint(
    name="Lumbering Pillar",
    health=7,
    speed=1,
    sight=0,
    armor=1,
    size=Size.LARGE,
    price=2,
)

SNAPPING_TURTLE = UnitBlueprint(
    "Snapping Turtle",
    health=2,
    speed=2,
    armor=1,
    sight=1,
    size=Size.SMALL,
    facets=[SnappingBeak, Aquatic],
    price=2,
)

SNAP_JAW = UnitBlueprint(
    "Snap Jaw",
    health=3,
    speed=1,
    sight=1,
    facets=[Chomp],
    price=2,
)

WEATHERED_ARMADILLO = UnitBlueprint(
    "Weathered Armadillo",
    health=5,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[StubbyClaws, ToughSkin],
    price=2,
)

BLOOD_CONDUIT = UnitBlueprint(
    "Blood Conduit",
    health=3,
    speed=3,
    sight=2,
    energy=3,
    facets=[VitalityTransfusion],
    price=3,
)

FROST_SPRITE = UnitBlueprint(
    "Frost Sprite",
    health=4,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[Frostbite],
    price=3,
)

GNOME_COMMANDO = UnitBlueprint(
    "Gnome Commando",
    health=4,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[GnomeSpear, TerrainSavvy],
    price=3,
)

INFERNAL_IMP = UnitBlueprint(
    "Infernal Imp",
    health=3,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[Swelter],
    price=3,
)

LIGHT_ARCHER = UnitBlueprint(
    name="Light Archer",
    health=4,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[LightBow],
    price=3,
)

MARSHMALLOW_TITAN = UnitBlueprint(
    name="Marshmallow Titan",
    health=11,
    speed=2,
    sight=1,
    armor=-1,
    size=Size.LARGE,
    facets=[MarshmallowFist],
    price=3,
)

PANGOLIN_FAMILIAR = UnitBlueprint(
    "Pangolin Familiar",
    health=5,
    speed=2,
    sight=1,
    size=Size.SMALL,
    facets=[SturdyClaws, AntiMagicHide],
    price=3,
)

SHRINE_KEEPER = UnitBlueprint(
    "Shrine Keeper",
    health=3,
    speed=3,
    sight=2,
    energy=4,
    size=Size.SMALL,
    facets=[RaiseShrine, GrantCharm, TidyUp],
    price=3,
)

SKITTISH_SOOT_PUFF = UnitBlueprint(
    "Skittish Soot Puff",
    health=3,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[SquirtSoot, PuffAway, FoulBurst, SootDweller],
    price=3,
    flavor="OMG, it's literally the fucking puff-puff. Are you fucking kidding me with this shit?",
)

ANKLE_BITER_NUISANCE = UnitBlueprint(
    "Ankle Biter Nuisance",
    health=3,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[AnkleBite],
    price=4,
)

ARTHRITIC_GIANT = UnitBlueprint(
    "Arthritic Giant",
    health=7,
    speed=2,
    sight=1,
    size=Size.LARGE,
    facets=[GranGransOlClub, OldBones],
    price=4,
)

BOMBARD_CANON = UnitBlueprint(
    "Bombard Canon",
    health=3,
    speed=1,
    sight=1,
    facets=[SolidMunition],
    price=4,
)

LITTLE_ENGINE = UnitBlueprint(
    "Little Engine",
    health=6,
    speed=1,
    sight=1,
    facets=[StrainedPusher],
    price=4,
)

OTTER_SCOUT = UnitBlueprint(
    "Otter Scout",
    health=5,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[OtterBite, Diver],
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
)

STIM_DRONE = UnitBlueprint(
    "Stim Drone",
    health=3,
    speed=2,
    sight=1,
    energy=3,
    size=Size.SMALL,
    facets=[StimulatingInjection],
    price=4,
    flavor="Just the refreshments this time, thanks.",
)

AP_GUNNER = UnitBlueprint(
    "AP Gunner",
    health=3,
    speed=2,
    sight=2,
    facets=[APGun],
    price=5,
)

BUGLING = UnitBlueprint(
    "Bugling",
    health=4,
    speed=4,
    sight=2,
    size=Size.SMALL,
    facets=[Scratch],
    price=5,
)

GNARLED_SHAMAN = UnitBlueprint(
    "Gnarled Shaman",
    health=3,
    speed=3,
    sight=2,
    energy=5,
    facets=[SpiritProjection, SweatItOut, GuidedTrance],
    price=5,
)

GOBLIN_ASSASSIN = UnitBlueprint(
    "Goblin Assassin",
    health=3,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[HiddenBlade, Stealth],
    price=5,
)

MEDIC = UnitBlueprint(
    "Medic",
    health=3,
    speed=3,
    sight=2,
    energy=5,
    facets=[HealBeam],
    price=5,
)

MINE_LAYER_BEETLE = UnitBlueprint(
    "Mine Layer Beetle",
    health=5,
    speed=3,
    sight=1,
    energy=3,
    facets=[Slice, LayMine],
    price=5,
)

MORTAR_SQUAD = UnitBlueprint(
    "Mortar Squad",
    health=3,
    speed=2,
    sight=2,
    facets=[Mortar],
    price=5,
    flavor="MOOORTAR COOOMBAT",
)

UNDERHANDED_HEXMAGE = UnitBlueprint(
    name="Underhanded Hexmage",
    health=5,
    speed=3,
    sight=2,
    energy=4,
    facets=[EnfeeblingHex],
    price=5,
)

ANCIENT_ALTRUIST = UnitBlueprint(
    "Ancient Altruist",
    health=4,
    speed=2,
    sight=2,
    energy=5,
    facets=[CriticalAid, Evacuate, CuringWord],
    price=6,
)

BOMB_TRUCK = UnitBlueprint(
    "Bomb Truck",
    health=3,
    speed=3,
    sight=1,
    facets=[SelfDestruct, Explosive],
    price=6,
    flavor="Nothing stops the mail.",
)

GLASS_GOLEM = UnitBlueprint(
    "Glass Golem",
    health=1,
    speed=3,
    armor=2,
    sight=2,
    facets=[GlassFist, GlassSkin],
    price=6,
)

RECON_SPECIALIST = UnitBlueprint(
    "Recon Specialist",
    health=5,
    speed=3,
    sight=2,
    energy=5,
    facets=[ServicePistol, ShootFlare, MapOut, TerrainSavvy],
    price=6,
)

RHINO_BEETLE = UnitBlueprint(
    "Rhino Beetle",
    health=4,
    speed=2,
    sight=1,
    facets=[CrushingMandibles, Grapple],
    armor=1,
    price=6,
)

RIFLE_INFANTRY = UnitBlueprint(
    "Rifle Infantry",
    health=5,
    speed=3,
    sight=2,
    facets=[Rifle],
    price=6,
)

STUBBORN_GOAT = UnitBlueprint(
    "Stubborn Goat",
    health=6,
    speed=3,
    sight=2,
    facets=[CurvedHorns, ToughSkin, Ornery],
    price=6,
)

VOID_SPRITE = UnitBlueprint(
    "Void Sprite",
    health=3,
    speed=1,
    sight=1,
    energy=6,
    size=Size.SMALL,
    facets=[EtherealSting, Jaunt],
    price=6,
)

BLOOD_FEUD_WARLOCK = UnitBlueprint(
    "Blood Feud Warlock",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[SowDiscord, Scorn, SpurIntoRage],
    price=7,
)

GIANT_SLAYER_MOUSE = UnitBlueprint(
    "Giant Slayer Mouse",
    health=5,
    speed=3,
    sight=2,
    size=Size.SMALL,
    facets=[Slay, LastStand],
    price=7,
)

TRACTOR = UnitBlueprint(
    "Tractor",
    health=7,
    speed=3,
    sight=1,
    size=Size.LARGE,
    facets=[Hitch],
    energy=4,
    price=7,
)

ZONE_SKIRMISHER = UnitBlueprint(
    "ZONE Skirmisher",
    health=6,
    speed=3,
    sight=2,
    facets=[Blaster, Bayonet],
    price=7,
)

BLIND_ABOMINATION = UnitBlueprint(
    "Blind Abomination",
    health=9,
    speed=3,
    sight=0,
    size=Size.LARGE,
    facets=[Vomit],
    price=8,
)

GIANT_TOAD = UnitBlueprint(
    "Giant Toad",
    health=8,
    speed=2,
    sight=2,
    energy=2,
    facets=[TongueLash, Jump, ToxicSkin],
    price=8,
)

REMORSELESS_SNIPER = UnitBlueprint(
    "Remorseless Sniper",
    health=2,
    speed=2,
    sight=2,
    facets=[SniperRifle, Binoculars, Stakeout],
    price=8,
)

DJINN = UnitBlueprint(
    "Djinn",
    health=4,
    speed=3,
    sight=2,
    energy=4,
    facets=[DancingSaber, GrantWish, MagicForm],
    price=9,
)

EFFORTLESS_ATHLETE = UnitBlueprint(
    "Effortless Athlete",
    health=6,
    speed=3,
    sight=2,
    facets=[RoundhouseKick, Vault, BatonPass],
    price=9,
)

ELITE_COMMANDO = UnitBlueprint(
    "Elite Commando",
    health=6,
    speed=3,
    sight=2,
    energy=5,
    facets=[
        RifleSalvo,
        HandGrenade,
        FlashBang,
        SmokeGrenade,
        TerrainSavvy,
        Swimmer,
    ],
    price=9,
)

INK_WITCH = UnitBlueprint(
    "Ink Witch",
    health=5,
    speed=3,
    sight=2,
    energy=5,
    facets=[BloodExpunge, InkRing, MalevolentStare],
    price=9,
)

SLUDGE_SLUG = UnitBlueprint(
    "Sludge Slug",
    health=10,
    speed=1,
    sight=1,
    size=Size.LARGE,
    energy=3,
    facets=[Spew, SludgeBelch, SludgeTrail, SlimyLocomotion, SlimySkin],
    price=9,
)

VELOCIRAPTOR = UnitBlueprint(
    "Velociraptor",
    health=5,
    speed=5,
    sight=2,
    facets=[ViciousBite],
    price=9,
)

BELL_STRIKER_BRUTE = UnitBlueprint(
    "Bell-Striker Brute",
    health=8,
    speed=3,
    sight=2,
    facets=[BellHammer],
    price=10,
)

BLITZ_TROOPER = UnitBlueprint(
    "Blitz Trooper",
    health=6,
    speed=3,
    sight=2,
    facets=[LightBlaster, Strafe],
    price=10,
)

BOULDER_HURLER_OAF = UnitBlueprint(
    "Boulder Hurler Oaf",
    health=7,
    speed=2,
    sight=2,
    size=Size.LARGE,
    facets=[
        HurlBoulder,
        Farsighted,
    ],
    price=10,
)

BULLDOZER = UnitBlueprint(
    "Bulldozer",
    health=9,
    speed=2,
    sight=1,
    size=Size.LARGE,
    armor=1,
    facets=[Pusher],
    price=10,
)

HOODED_EXECUTIONER = UnitBlueprint(
    "Hooded Executioner",
    health=6,
    speed=3,
    sight=2,
    facets=[GuillotineAxe, PublicExecution, DreadfulVisage],
    price=10,
)

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
    price=10,
    flavor="I need justice in my life: Here it comes.",
)

CHAINSAW_SADIST = UnitBlueprint(
    "Chainsaw Sadist",
    health=7,
    speed=3,
    sight=2,
    facets=[Chainsaw, FightFlightFreeze, GrizzlyMurderer],
    price=11,
)

COMBAT_ENGINEER = UnitBlueprint(
    "Combat Engineer",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[Wrench, ConstructTurret, FixErUp, TurboTune],
    price=11,
)

DIRE_WOLF = UnitBlueprint(
    "Dire Wolf",
    health=7,
    speed=4,
    sight=2,
    facets=[Bite, PackHunter],
    price=11,
)

HORROR = UnitBlueprint(
    "Horror",
    health=7,
    speed=4,
    sight=2,
    energy=4,
    facets=[SerratedClaws, VenomousSpine],
    price=11,
)

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
    price=11,
)

PESTILENCE_PRIEST = UnitBlueprint(
    "Pestilence Priest",
    health=5,
    speed=3,
    sight=2,
    energy=6,
    facets=[SummonScarab, InducePanic, Schadenfreude],
    price=11,
)

VILE_TRANSMUTER = UnitBlueprint(
    "Vile Transmuter",
    health=5,
    speed=3,
    sight=2,
    energy=5,
    facets=[DrainingGrasp, WringEssence, FatalBonding, FalseCure],
    price=11,
)

FRONTLINE_TACTICIAN = UnitBlueprint(
    "Frontline Tactician",
    health=6,
    speed=3,
    sight=2,
    energy=4,
    facets=[CommandersPistol, CoordinatedManeuver, InspiringPresence],
    price=12,
)

GATE_FIEND = UnitBlueprint(
    "Gate Fiend",
    health=8,
    speed=3,
    sight=2,
    energy=4,
    facets=[InfernalBlade, OpenGate],
    price=12,
)

INFERNO_TANK = UnitBlueprint(
    "Inferno Tank",
    health=7,
    speed=2,
    sight=1,
    armor=1,
    energy=6,
    size=Size.LARGE,
    facets=[
        Scorch,
        FlameWall,
        FlameResistant,
    ],
    price=12,
)

INSCRUTABLE_CHIMERA = UnitBlueprint(
    "Inscrutable Chimera",
    health=7,
    speed=3,
    sight=2,
    energy=5,
    facets=[CrypticClaws, Riddle, PsychicCommand, InstilFocus],
    price=12,
)

STAUNCH_IRON_HEART = UnitBlueprint(
    "Staunch Iron-Heart",
    health=7,
    speed=2,
    armor=1,
    sight=2,
    energy=4,
    facets=[HammerBlow, MightyBlow, IronBlessing],
    price=12,
)

WITCH_ENGINE = UnitBlueprint(
    "Witch Engine",
    health=7,
    speed=2,
    sight=2,
    energy=8,
    facets=[ChokingSoot, Terrorize, GreaseTheGears, ToxicPresence],
    price=14,
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

GIANT_BATTLE_CRAB = UnitBlueprint(
    "Giant Battle Crab",
    health=9,
    speed=2,
    sight=1,
    armor=2,
    facets=[GiantPincers, Aquatic, CrabShuffle],
    price=15,
)

ZONE_MECH = UnitBlueprint(
    "ZONE Mech",
    health=7,
    speed=2,
    armor=1,
    sight=2,
    energy=3,
    size=Size.LARGE,
    facets=[HammerCannon, SmokeCanister, TerrainSavvy],
    price=18,
)

BEE_SHAMAN = UnitBlueprint(
    "Bee Shaman", health=4, speed=3, sight=2, energy=3, facets=[SummonBees], price=None
)

BEE_SWARM = UnitBlueprint(
    "Bee Swarm",
    health=2,
    speed=3,
    sight=1,
    size=Size.SMALL,
    facets=[Stinger],
    price=None,
)

BLOOD_HOMUNCULUS = UnitBlueprint(
    "Blood Homunculus",
    health=6,
    speed=2,
    sight=1,
    facets=[Gnaw],
    price=None,
)

CACTUS = UnitBlueprint(
    name="Cactus",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    facets=[Prickly, Immobile, Grow],
    price=None,
)

DOOMBOT_3000 = UnitBlueprint(
    "Doombot 3000",
    identifier="doombot_3000",
    health=7,
    speed=1,
    sight=2,
    energy=4,
    armor=1,
    size=Size.LARGE,
    facets=[DeathLaser, FlameThrower, SelfDestruct, Explosive],
    price=None,
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

LOTUS_BUD = UnitBlueprint(
    name="Lotus Bud",
    health=3,
    speed=0,
    sight=0,
    energy=2,
    starting_energy=0,
    size=Size.SMALL,
    facets=[Immobile, Nourishing, Bloom],
    price=None,
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

SENTRY_TURRET = UnitBlueprint(
    "Sentry Turret",
    health=4,
    speed=0,
    sight=2,
    facets=[MiniGun, Immobile, Automated],
    price=None,
)

TELEPATH = UnitBlueprint(
    "Telepath",
    health=4,
    speed=3,
    sight=1,
    energy=4,
    facets=[InternalStruggle, TelepathicSpy],
    price=None,
)

CAPRICIOUS_TRICKSTER = UnitBlueprint(
    "Capricious Trickster",
    health=6,
    speed=3,
    sight=2,
    energy=5,
    facets=[Shiv, Vault, Shove, Poof, JukeAndJive],
    price=11,
    max_count=0,
)

DIAMOND_GOLEM = UnitBlueprint(
    "Diamond Golem",
    health=1,
    speed=3,
    armor=3,
    sight=2,
    facets=[DiamondFist, DiamondSkin],
    price=11,
    max_count=0,
)

WAR_HOG = UnitBlueprint(
    "War Hog",
    health=8,
    speed=3,
    sight=2,
    facets=[RazorTusk, Furious],
    price=11,
    max_count=0,
)

MAD_SCIENTIST = UnitBlueprint(
    "Mad Scientist",
    health=6,
    speed=3,
    sight=2,
    energy=8,
    facets=[ShrinkRay, Translocate, AssembleTheDoombot, Inspiration],
    price=13,
    max_count=0,
)

RHINO_BEAST = UnitBlueprint(
    "Rhino",
    health=10,
    speed=4,
    sight=2,
    size=Size.LARGE,
    facets=[Gore],
    price=15,
    max_count=0,
)
