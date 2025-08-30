from __future__ import annotations

from game.core import (
    HexStatus,
    HexStatusSignature,
    StaticAbilityFacet,
    Status,
    UnitStatus,
    UnitStatusSignature,
)
from game.effects.modifiers import (
    AquaticModifier,
    CamouflageModifier,
    CrushableModifier,
    FarsightedModifier,
    FightFlightFreezeModifier,
    IncreaseSpeedAuraModifier,
    PusherModifier,
    RootedModifier,
    SourceTypeResistance,
    StealthModifier,
    TelepathicSpyModifier,
    TerrainProtectionModifier,
    UnitNoCaptureModifier,
    UnwieldySwimmerModifier,
)
from game.effects.replacements import (
    CrushableReplacement,
    IgnoresMoveOutPenaltyReplacement,
    LastStandReplacement,
    PerTurnMovePenaltyIgnoreReplacement,
    PusherReplacement,
    StrainedPusherReplacement,
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
    ScurryInTheShadowsTrigger,
    ToxicPresenceTrigger,
    UnitAppliesStatusOnMoveTrigger,
)
from game.map.terrain import Water
from game.statuses.unit_statuses import Burn
from game.values import Resistance


class Prickly(StaticAbilityFacet):
    """
    When this unit is hit with a melee attack, the attacker suffers 2 damage.
    """

    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.parent, self, 2))


class ToxicSkin(StaticAbilityFacet):
    """
    When this unit is melee attacked, the attacking unit suffers 1 stack of <poison>.
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
            CrushableReplacement(self.parent), CrushableModifier(self.parent)
        )


class Pusher(StaticAbilityFacet):
    """
    This unit can move into occupied spaces. If it would do so, it first pushes the occupying unit one space, repeating
    if that unit would be pushed into an occupied space as well. If units can't be pushed back due to being blocked, they suffer 2 damage.
    If this is sufficient to kill them, it does, and the space is freed up to be moved in by the next unit in the chain.
    """

    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.parent), PusherReplacement(self.parent, self)
        )


class StrainedPusher(StaticAbilityFacet):
    """
    This unit can move into occupied spaces. If it would do so, it first pushes the occupying unit one space, repeating
    if that unit would be pushed into an occupied space as well. This unit suffers 1 pure damage for each unit it attempts to
    push this way beyond the first.
    """

    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.parent), StrainedPusherReplacement(self.parent, self)
        )


class TerrainSavvy(StaticAbilityFacet):
    """Ignores the first movement penalty each turn."""

    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.parent, 1))


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
    When this unit kills an opposing unit with a melee attack, each unit allied to
    the killed units that could see it suffers <shocked> for 2 rounds.
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


class Quick(StaticAbilityFacet):
    """
    At the end of this units turn, it may move one hex (unaffected by movement points).
    """

    def create_effects(self) -> None:
        self.register_effects(QuickTrigger(self.parent))


class GlassSkin(StaticAbilityFacet):
    """
    Major resistance to damage from statuses.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.parent, Status, Resistance.MAJOR)
        )


class DiamondSkin(StaticAbilityFacet):
    """
    Immune to damage from statuses.
    """

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.parent, Status, Resistance.IMMUNE)
        )


class FlameResistant(StaticAbilityFacet):
    """
    Reduce damage from the <burn> status by half (after armor), rounding the reduction up.
    """

    def create_effects(self) -> None:
        self.register_effects(SourceTypeResistance(self.parent, Burn, Resistance.MAJOR))


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
    +1 terrain protection on water.
    """

    def create_effects(self) -> None:
        self.register_effects(
            AquaticModifier(self.parent),
            TerrainProtectionModifier(self.parent, Water, 1),
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


class Automated(StaticAbilityFacet):
    """
    This unit can't capture objectives.
    """

    def create_effects(self) -> None:
        self.register_effects(UnitNoCaptureModifier(self.parent))
