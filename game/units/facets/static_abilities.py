from __future__ import annotations

from game.core import (
    HexStatus,
    HexStatusSignature,
    StaticAbilityFacet,
    Status,
    StatusSignature,
    UnitStatus,
)
from game.effects.modifiers import (
    CamouflageModifier,
    CrushableModifier,
    FarsightedModifier,
    FightFlightFreezeModifier,
    IncreaseSpeedAuraModifier,
    PusherModifier,
    RootedModifier,
    ScurryInTheShadowsModifier,
    SourceTypeResistance,
    StealthModifier,
    TelepathicSpyModifier,
    TerrainProtectionModifier,
    UnwieldySwimmerModifier,
)
from game.effects.replacements import (
    CrushableReplacement,
    IgnoresMoveOutPenaltyReplacement,
    LastStandReplacement,
    PerTurnMovePenaltyIgnoreReplacement,
    PusherReplacement,
    UnitImmuneToStatusReplacement,
)
from game.effects.triggers import (
    CaughtInTheMatchTrigger,
    DebuffOnMeleeAttackTrigger,
    ExplosiveTrigger,
    FuriousTrigger,
    GrizzlyMurdererTrigger,
    HeelTurnTrigger,
    InspirationTrigger,
    JukeAndJiveTrigger,
    PackHunterTrigger,
    PricklyTrigger,
    QuickTrigger,
    SchadenfreudeDamageTrigger,
    SchadenfreudeDebuffTrigger,
    ToxicPresenceTrigger,
    UnitAppliesStatusOnMoveTrigger,
)
from game.map.terrain import Water
from game.statuses.unit_statuses import Burn
from game.values import Resistance


class Prickly(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.owner, self, 2))


class ToxicSkin(StaticAbilityFacet):
    """
    When this unit is melee attacked, the attacking unit suffers 1 stack of <poison>.
    """

    def create_effects(self) -> None:
        self.register_effects(
            DebuffOnMeleeAttackTrigger(
                self.owner, StatusSignature(UnitStatus.get("poison"), self, stacks=1)
            )
        )


class Immobile(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(RootedModifier(self.owner))


class Farsighted(StaticAbilityFacet):
    """
    Can't see adjacent spaces.
    """

    def create_effects(self) -> None:
        self.register_effects(FarsightedModifier(self.owner))


class PackHunter(StaticAbilityFacet):
    """
    When another allied unit melee attacks a unit adjacent to this unit, this unit hits the attacked unit with its primary melee attack.
    """

    def create_effects(self) -> None:
        self.register_effects(PackHunterTrigger(self.owner))


class Nourishing(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            CrushableReplacement(self.owner), CrushableModifier(self.owner)
        )


class Pusher(StaticAbilityFacet):
    """
    This unit can move into occupied spaces. If it would do so, it first pushes the occupying unit one space, repeating
    if that unit would be pushed into an occupied space as well. If occupying units can't be pushed back due to impassable
    terrain, each unit that would be pushed this way suffers 2 damage.
    """

    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.owner), PusherReplacement(self.owner, self)
        )


class TerrainSavvy(StaticAbilityFacet):
    """Ignores the first movement penalty each turn."""

    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.owner, 1))


class Furious(StaticAbilityFacet):
    """
    When this unit is hit by an attack, it is readied.
    """

    def create_effects(self) -> None:
        self.register_effects(FuriousTrigger(self.owner))


class Stealth(StaticAbilityFacet):
    """
    Can't be seen by units not adjacent to this unit.
    """

    def create_effects(self) -> None:
        self.register_effects(StealthModifier(self.owner))


class FightFlightFreeze(StaticAbilityFacet):
    """
    Opponents units adjacent to this units can't take any actions that aren't attacking this unit, moving away from this unit,
    or skipping.
    """

    def create_effects(self) -> None:
        self.register_effects(FightFlightFreezeModifier(self.owner))


class Explosive(StaticAbilityFacet):
    """When this unit dies, it deals 5 aoe damage to unit within 1 range."""

    def create_effects(self) -> None:
        self.register_effects(ExplosiveTrigger(self.owner, self, 5))


class Schadenfreude(StaticAbilityFacet):
    """
    Whenever an adjacent unit is damaged or debuffed, this unit gains 1 energy.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SchadenfreudeDamageTrigger(self.owner),
            SchadenfreudeDebuffTrigger(self.owner),
        )


class GrizzlyMurderer(StaticAbilityFacet):
    """
    When this unit kills an opposing unit with a melee attack, each unit allied to
    the killed units that could see it suffers <terrified> for 2 rounds.
    """

    def create_effects(self) -> None:
        self.register_effects(GrizzlyMurdererTrigger(self.owner, self))


class TelepathicSpy(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(TelepathicSpyModifier(self.owner))


class CaughtInTheMatch(StaticAbilityFacet):
    """
    Whenever an enemy unit disengages this unit, the enemy unit loses 1 movement point.
    """

    def create_effects(self) -> None:
        self.register_effects(CaughtInTheMatchTrigger(self.owner))


class HeelTurn(StaticAbilityFacet):
    """
    When this unit suffers 4 or more damage at once, it gains <they_ve_got_a_steel_chair>.
    """

    def create_effects(self) -> None:
        self.register_effects(HeelTurnTrigger(self.owner, self))


class Quick(StaticAbilityFacet):
    """
    At the end of this units turn, it may move on space (unaffected by movement points).
    """

    def create_effects(self) -> None:
        self.register_effects(QuickTrigger(self.owner))


class GlassSkin(StaticAbilityFacet):
    """
    Major resistance to damage from statuses.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.MAJOR)
        )


class DiamondSkin(StaticAbilityFacet):
    """
    Immune to damage from statuses.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.IMMUNE)
        )


class FlameResistant(StaticAbilityFacet):
    """
    Major resistant to damage from the <burn> status.
    """

    def create_effects(self) -> None:
        self.register_effects(SourceTypeResistance(self.owner, Burn, Resistance.MAJOR))


class LastStand(StaticAbilityFacet):
    """
    If this unit would die, and it isn't mortally wounded, instead set its health to
    1, dispel all debuffs from it, and it gains <mortally_wounded> for 1 round.
    """

    def create_effects(self) -> None:
        self.register_effects(LastStandReplacement(self.owner, self))


class ToxicPresence(StaticAbilityFacet):
    """
    At the end of this units turn it applies 1 <poison> to each adjacent unit.
    """

    def create_effects(self) -> None:
        self.register_effects(ToxicPresenceTrigger(self.owner, self, 1))


class Diver(StaticAbilityFacet):
    """
    +1 terrain protection on water.
    """

    def create_effects(self) -> None:
        self.register_effects(TerrainProtectionModifier(self.owner, Water, 1))


class Camouflage(StaticAbilityFacet):
    """
    +1 ranged terrain protection against non-adjacent units.
    """

    def create_effects(self) -> None:
        self.register_effects(CamouflageModifier(self.owner))


class UnwieldySwimmer(StaticAbilityFacet):
    """
    Disarmed and silenced while on water.
    """

    def create_effects(self) -> None:
        self.register_effects(UnwieldySwimmerModifier(self.owner))


class ScurryInTheShadows(StaticAbilityFacet):
    """
    As long as no enemy can see this unit, it has +2 speed.
    """

    def create_effects(self) -> None:
        self.register_effects(ScurryInTheShadowsModifier(self.owner, 2))


class JukeAndJive(StaticAbilityFacet):
    """
    At the end of each of this units actions, if it isn't visible to the enemy, and it was at the
    beginning of it's action, or vice versa, it gains a stack of <all_in_jest>.
    """

    def create_effects(self) -> None:
        self.register_effects(JukeAndJiveTrigger(self.owner, self))


class Inspiration(StaticAbilityFacet):
    """
    When this unit sees another unit activate an ability costing 3 or more energy, this unit gains 1 energy, or 2 if it cost 4 or more.
    """

    def create_effects(self) -> None:
        self.register_effects(InspirationTrigger(self.owner))


class InspiringPresence(StaticAbilityFacet):
    """
    Adjacent allied units have +1 speed.
    """

    def create_effects(self) -> None:
        self.register_effects(IncreaseSpeedAuraModifier(self.owner, 1))


class SlimyLocomotion(StaticAbilityFacet):
    """
    Ignores move out penalties.
    """

    def create_effects(self) -> None:
        self.register_effects(IgnoresMoveOutPenaltyReplacement(self.owner))


class SlimySkin(StaticAbilityFacet):
    """
    Immune to <slimed>.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitImmuneToStatusReplacement(self.owner, UnitStatus.get("slimed"))
        )


class SludgeTrail(StaticAbilityFacet):
    """
    When this unit moves into a space, it applies <sludge> to it for 2 rounds.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitAppliesStatusOnMoveTrigger(
                self.owner,
                HexStatusSignature(HexStatus.get("sludge"), self, duration=2),
            )
        )
