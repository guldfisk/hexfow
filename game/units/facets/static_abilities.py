from __future__ import annotations

from game.core import (
    ActivatedAbilityFacet,
    AttackFacet,
    HexStatus,
    HexStatusSignature,
    StaticAbilityFacet,
    Status,
    Terrain,
    UnitStatus,
    UnitStatusSignature,
)
from game.effects.modifiers import (
    AquaticModifier,
    CamouflageModifier,
    CrabShuffleModifier,
    CrushableModifier,
    FarsightedModifier,
    FightFlightFreezeModifier,
    IgnoreMoveInOnTerrainModifier,
    IncreaseSpeedAuraModifier,
    NegativeAttackPowerAuraModifier,
    NotMovedStealthModifier,
    PusherModifier,
    ResistanceModifier,
    RootedModifier,
    SoilCommunionModifier,
    SourceTypeResistanceModifier,
    StealthModifier,
    StealthOnTerrainModifier,
    TelepathicSpyModifier,
    UnitCapSpeedModifier,
    UnitNoCaptureModifier,
    UnitSightMinModifier,
    UnwieldySwimmerModifier,
)
from game.effects.replacements import (
    CrushableReplacement,
    ExternallyImmobileReplacement,
    IgnoresMoveOutPenaltyReplacement,
    LastStandReplacement,
    PerTurnMovePenaltyIgnoreReplacement,
    PusherReplacement,
    StayingPowerReplacement,
    StrainedPusherReplacement,
    UnitImmuneToStatusReplacement,
)
from game.effects.triggers import (
    AutomatedTrigger,
    CaughtInTheMatchTrigger,
    DebuffOnMeleeAttackTrigger,
    ExplosiveTrigger,
    FleetingTrigger,
    FoulBurstTrigger,
    FuriousTrigger,
    GrizzlyMurdererTrigger,
    HeelTurnTrigger,
    InspirationTrigger,
    JukeAndJiveTrigger,
    OldBonesTrigger,
    OrneryTrigger,
    PackHunterTrigger,
    PricklyTrigger,
    PuffAwayTrigger,
    QuickTrigger,
    RecurringUnitBuffTrigger,
    SchadenfreudeDamageTrigger,
    SchadenfreudeDebuffTrigger,
    ScurryInTheShadowsTrigger,
    ToxicPresenceTrigger,
    UnitAppliesStatusOnMoveTrigger,
)
from game.map.terrain import Water
from game.statuses.unit_statuses import Burn
from game.values import Resistance


class Prickly(StaticAbilityFacet):
    """
    When this unit is hit with a melee attack, this ability deals 2 damage to the attacker.
    """

    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.parent, self, 2))


class ToxicSkin(StaticAbilityFacet):
    """
    When this unit is melee attacked, apply 1 stack of <poison> to the attacking unit.
    """

    def create_effects(self) -> None:
        self.register_effects(
            DebuffOnMeleeAttackTrigger(
                self.parent,
                UnitStatusSignature(UnitStatus.get("poison"), self, stacks=1),
            )
        )


class Immobile(StaticAbilityFacet):
    """
    This unit can't take move actions.
    """

    def create_effects(self) -> None:
        self.register_effects(RootedModifier(self.parent))


class Farsighted(StaticAbilityFacet):
    """
    Can't see adjacent spaces.
    """

    def create_effects(self) -> None:
        self.register_effects(FarsightedModifier(self.parent))


class PackHunter(StaticAbilityFacet):
    """
    When another allied unit melee attacks a unit adjacent to this unit, this unit hits the attacked unit with its primary melee attack.
    """

    def create_effects(self) -> None:
        self.register_effects(PackHunterTrigger(self.parent))


class Nourishing(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            CrushableReplacement(self.parent, self), CrushableModifier(self.parent)
        )


class Pusher(StaticAbilityFacet):
    """
    This unit can move into occupied spaces. If it would do so, it first pushes the occupying unit one space, repeating
    if that unit would be pushed into an occupied space as well. If units can't be pushed back due to being blocked, they're dealt 2 damage.
    If this is sufficient to kill them, it does, and the space is freed up to be moved in by the next unit in the chain.
    """

    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.parent), PusherReplacement(self.parent, self)
        )


class StrainedPusher(StaticAbilityFacet):
    """
    This unit can move into occupied spaces. If it would do so, it first pushes the occupying unit one space, repeating
    if that unit would be pushed into an occupied space as well. This unit is dealt 1 pure damage for each unit it attempts to
    push this way beyond the first.
    """

    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.parent), StrainedPusherReplacement(self.parent, self)
        )


class TerrainSavvy(StaticAbilityFacet):
    """Ignores the first movement penalty (not additional move in costs) each turn."""

    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.parent, 1))


class RockSteady(StaticAbilityFacet):
    """
    This unit can't be moved by other units, and it's speed can't be more than 1.
    """

    def create_effects(self) -> None:
        self.register_effects(
            ExternallyImmobileReplacement(self.parent),
            UnitCapSpeedModifier(self.parent, 1),
        )


class Wild(StaticAbilityFacet):
    """
    This unit can't capture objectives.
    """

    def create_effects(self) -> None:
        self.register_effects(UnitNoCaptureModifier(self.parent))


class Furious(StaticAbilityFacet):
    """
    When this unit is hit by an attack, it is readied.
    """

    def create_effects(self) -> None:
        self.register_effects(FuriousTrigger(self.parent))


class Stealth(StaticAbilityFacet):
    """
    Can't be seen by units not adjacent to this unit.
    """

    def create_effects(self) -> None:
        self.register_effects(StealthModifier(self.parent))


class FightFlightFreeze(StaticAbilityFacet):
    """
    Opponents units adjacent to this units can't take any actions that aren't attacking this unit, moving away from this unit,
    or skipping.
    """

    def create_effects(self) -> None:
        self.register_effects(FightFlightFreezeModifier(self.parent))


class Explosive(StaticAbilityFacet):
    """When this unit dies, it deals 5 aoe damage to unit within 1 range."""

    def create_effects(self) -> None:
        self.register_effects(ExplosiveTrigger(self.parent, self, 5))


class Schadenfreude(StaticAbilityFacet):
    """
    Whenever an adjacent unit is damaged or debuffed, this unit gains 1 energy.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SchadenfreudeDamageTrigger(self.parent, self),
            SchadenfreudeDebuffTrigger(self.parent, self),
        )


class GrizzlyMurderer(StaticAbilityFacet):
    """
    When this unit kills an opposing unit with a melee attack, apply <shocked> for
    2 rounds to each unit allied to the killed units that could see it.
    """

    def create_effects(self) -> None:
        self.register_effects(GrizzlyMurdererTrigger(self.parent, self))


class TelepathicSpy(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(TelepathicSpyModifier(self.parent))


class CaughtInTheMatch(StaticAbilityFacet):
    """
    Whenever an enemy unit disengages this unit, the enemy unit loses 1 movement point.
    """

    def create_effects(self) -> None:
        self.register_effects(CaughtInTheMatchTrigger(self.parent))


class HeelTurn(StaticAbilityFacet):
    """
    When this unit suffers damage, if its health is exactly 1, it gains <they_ve_got_a_steel_chair>.
    """

    def create_effects(self) -> None:
        self.register_effects(HeelTurnTrigger(self.parent, self))


class Fleeting(StaticAbilityFacet):
    """
    At the end of the second round, this unit dies.
    """

    def create_effects(self) -> None:
        self.register_effects(FleetingTrigger(self.parent, 2, self))


class CrabShuffle(StaticAbilityFacet):
    """
    This unit can't move in the same direction two times in a row in the same turn.
    """

    def create_effects(self) -> None:
        self.register_effects(CrabShuffleModifier(self.parent))


class DreadfulVisage(StaticAbilityFacet):
    """
    Adjacent enemy units have -1 attack power.
    """

    def create_effects(self) -> None:
        self.register_effects(NegativeAttackPowerAuraModifier(self.parent, 1))


class Quick(StaticAbilityFacet):
    """
    At the end of this units turn, it may move one hex (unaffected by movement points).
    """

    def create_effects(self) -> None:
        self.register_effects(QuickTrigger(self.parent))


class GlassSkin(StaticAbilityFacet):
    """
    Reduces damage dealt to this unit by statues to half, rounded down.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(self.parent, Status, Resistance.MAJOR)
        )


class DiamondSkin(StaticAbilityFacet):
    """
    Immune to damage from statuses.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(self.parent, Status, Resistance.IMMUNE)
        )


class FlameResistant(StaticAbilityFacet):
    """
    Reduce damage dealt to this unit by the <burn> status to half (after armor), rounded down.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(self.parent, Burn, Resistance.MAJOR)
        )


class SootDweller(StaticAbilityFacet):
    """
    Immune to damage from the soot status.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(
                self.parent, HexStatus.get("soot"), Resistance.IMMUNE
            )
        )


class OldBones(StaticAbilityFacet):
    """
    When this unit ends its turn, if it acted, apply 1 stack of <tired> to it.
    """

    def create_effects(self) -> None:
        self.register_effects(OldBonesTrigger(self.parent, self))


class SoilCommunion(StaticAbilityFacet):
    """
    Allied units with 1 range on forests have +1 energy regen.
    """

    def create_effects(self) -> None:
        self.register_effects(SoilCommunionModifier(self.parent, 1))


class ForestDweller(StaticAbilityFacet):
    """
    Ignores move in penalties on Forests.
    """

    def create_effects(self) -> None:
        self.register_effects(
            IgnoreMoveInOnTerrainModifier(self.parent, Terrain.get_class("forest"))
        )


class Stakeout(StaticAbilityFacet):
    """
    Stealth while this unit hasn't moved this turn.
    """

    def create_effects(self) -> None:
        self.register_effects(NotMovedStealthModifier(self.parent))


class AntiMagicHide(StaticAbilityFacet):
    """
    Reduce damage dealt to this unit by abilities and statuses to half, rounded down.
    """

    name = "Anti-Magic Hide"

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(
                self.parent,
                (ActivatedAbilityFacet, StaticAbilityFacet, Status),
                Resistance.MAJOR,
            )
        )


class ResistantSkin(StaticAbilityFacet):
    """
    Reduce damage dealt to this unit by abilities and statuses to two thirds, rounded up.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(
                self.parent,
                (ActivatedAbilityFacet, StaticAbilityFacet, Status),
                Resistance.MINOR,
            )
        )


class MagicForm(StaticAbilityFacet):
    """
    Reduce damage dealt to this unit by attacks to half, rounded up.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(self.parent, AttackFacet, Resistance.NORMAL)
        )


class FoulBurst(StaticAbilityFacet):
    """
    When this unit dies, apply <soot> to the hex it was on for 2 rounds.
    """

    def create_effects(self) -> None:
        self.register_effects(FoulBurstTrigger(self.parent, self))


class ToughSkin(StaticAbilityFacet):
    """
    Reduce damage dealt to this unit to two thirds, rounded up.
    """

    def create_effects(self) -> None:
        self.register_effects(ResistanceModifier(self.parent, Resistance.MINOR))


class Ornery(StaticAbilityFacet):
    """
    When a debuff is applied to this unit, it heals 1.
    """

    def create_effects(self) -> None:
        self.register_effects(OrneryTrigger(self.parent, self))


class PuffAway(StaticAbilityFacet):
    """
    When an enemy engages this unit while this unit is ready, you may have this unit move one hex away from the
    engaging unit. If you do, apply <soot> to the hex this unit previously occupied, and exhaust this unit.
    """

    def create_effects(self) -> None:
        self.register_effects(PuffAwayTrigger(self.parent, self))


class LastStand(StaticAbilityFacet):
    """
    If this unit would die, and it isn't mortally wounded, instead set its health to
    1, dispel all debuffs from it, and it gains <mortally_wounded> for 1 round.
    """

    def create_effects(self) -> None:
        self.register_effects(LastStandReplacement(self.parent, self))


class ToxicPresence(StaticAbilityFacet):
    """
    At the end of this units turn it applies 1 <poison> to each adjacent unit.
    """

    def create_effects(self) -> None:
        self.register_effects(ToxicPresenceTrigger(self.parent, self, 1))


class Aquatic(StaticAbilityFacet):
    """
    This unit can move on water.
    """

    def create_effects(self) -> None:
        self.register_effects(AquaticModifier(self.parent))


class Diver(StaticAbilityFacet):
    """
    This unit can move on water.
    Stealth on water.
    """

    def create_effects(self) -> None:
        self.register_effects(
            AquaticModifier(self.parent), StealthOnTerrainModifier(self.parent, Water)
        )


class Camouflage(StaticAbilityFacet):
    """
    +1 ranged terrain protection against non-adjacent units.
    """

    def create_effects(self) -> None:
        self.register_effects(CamouflageModifier(self.parent))


class Swimmer(StaticAbilityFacet):
    """
    This unit can move on water.
    Disarmed and silenced while on water.
    """

    def create_effects(self) -> None:
        self.register_effects(
            AquaticModifier(self.parent), UnwieldySwimmerModifier(self.parent)
        )


class ScurryInTheShadows(StaticAbilityFacet):
    """
    When this unit is activated, if it is unseen by the enemy, it gains +2 movement points.
    """

    def create_effects(self) -> None:
        self.register_effects(ScurryInTheShadowsTrigger(self.parent))


class JukeAndJive(StaticAbilityFacet):
    """
    At the end of each of this units actions, if it isn't visible to the enemy, and it was at the
    beginning of it's action, or vice versa, it gains a stack of <all_in_jest>.
    """

    def create_effects(self) -> None:
        self.register_effects(JukeAndJiveTrigger(self.parent, self))


class Inspiration(StaticAbilityFacet):
    """
    When this unit sees another unit activate an ability costing 3 or more energy, this unit gains 1 energy, or 2 if it cost 4 or more.
    """

    def create_effects(self) -> None:
        self.register_effects(InspirationTrigger(self.parent, self))


class InspiringPresence(StaticAbilityFacet):
    """
    Adjacent allied units have +1 speed.
    """

    def create_effects(self) -> None:
        self.register_effects(IncreaseSpeedAuraModifier(self.parent, 1))


class SlimyLocomotion(StaticAbilityFacet):
    """
    Ignores move out penalties.
    """

    def create_effects(self) -> None:
        self.register_effects(IgnoresMoveOutPenaltyReplacement(self.parent))


class SlimySkin(StaticAbilityFacet):
    """
    Immune to <slimed>.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitImmuneToStatusReplacement(self.parent, UnitStatus.get("slimed"))
        )


class ForceShield(StaticAbilityFacet):
    """
    At the beginning of each round, if this unit doesn't have a stack of <buffer>, apply 1 stack of <buffer> to it.
    """

    def create_effects(self) -> None:
        self.register_effects(
            RecurringUnitBuffTrigger(self.parent, self, UnitStatus.get("buffer"))
        )


class Vigorous(StaticAbilityFacet):
    """
    At the beginning of each round, if this unit doesn't have a stack of <vigor>, apply 1 stack of <vigor> to it.
    """

    def create_effects(self) -> None:
        self.register_effects(
            RecurringUnitBuffTrigger(self.parent, self, UnitStatus.get("vigor"))
        )


class StayingPower(StaticAbilityFacet):
    """
    If this unit would suffer damage while it has more than 1 health, that damage is non-lethal.
    """

    def create_effects(self) -> None:
        self.register_effects(StayingPowerReplacement(self.parent))


class TactileSensing(StaticAbilityFacet):
    """
    This unit has at least 1 sight.
    """

    def create_effects(self) -> None:
        self.register_effects(UnitSightMinModifier(self.parent, 1))


class SludgeTrail(StaticAbilityFacet):
    """
    When this unit moves into a space, it applies <sludge> to it for 2 rounds.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitAppliesStatusOnMoveTrigger(
                self.parent,
                HexStatusSignature(HexStatus.get("sludge"), self, duration=2),
            )
        )


class Structure(StaticAbilityFacet):
    """
    This unit can't take move actions and can't capture points.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitNoCaptureModifier(self.parent), RootedModifier(self.parent)
        )


class Automated(StaticAbilityFacet):
    """
    Whenever an enemy unit moves, if this unit is ready and can hit the moving unit with its primary attack, it does so,
    and is then exhausted.
    """

    def create_effects(self) -> None:
        self.register_effects(AutomatedTrigger(self.parent))
