from __future__ import annotations

from game.core import StaticAbilityFacet, Status
from game.effects.modifiers import (
    RootedModifier,
    FarsightedModifier,
    CrushableModifier,
    PusherModifier,
    StealthModifier,
    FightFlightFreezeModifier,
    TelepathicSpyModifier,
    SourceTypeResistance,
    TerrainProtectionModifier,
    ScurryInTheShadowsModifier,
)
from game.effects.replacements import (
    CrushableReplacement,
    PusherReplacement,
    PerTurnMovePenaltyIgnoreReplacement,
    LastStandReplacement,
)
from game.effects.triggers import (
    PricklyTrigger,
    PackHunterTrigger,
    FuriousTrigger,
    ExplosiveTrigger,
    SchadenfreudeDamageTrigger,
    SchadenfreudeDebuffTrigger,
    GrizzlyMurdererTrigger,
    CaughtInTheMatchTrigger,
    HeelTurnTrigger,
    QuickTrigger,
    ToxicPresenceTrigger,
    JukeAndJiveTrigger,
)
from game.map.terrain import Water
from game.statuses.units import Burn
from game.values import Resistance


class Prickly(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(PricklyTrigger(self.owner, self, 2))


class Immobile(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(RootedModifier(self.owner))


class Farsighted(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FarsightedModifier(self.owner))


class PackHunter(StaticAbilityFacet):
    """
    When another allied unit attacks a unit adjacent to this unit, this unit hits the attacked unit with its primary melee attack.
    """
    def create_effects(self) -> None:
        self.register_effects(PackHunterTrigger(self.owner))


class Nourishing(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            CrushableReplacement(self.owner), CrushableModifier(self.owner)
        )


class Pusher(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            PusherModifier(self.owner), PusherReplacement(self.owner, self)
        )


class TerrainSavvy(StaticAbilityFacet):
    """Ignores the first movement penalty each turn."""

    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.owner, 1))


class Furious(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FuriousTrigger(self.owner))


class Stealth(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(StealthModifier(self.owner))


class FightFlightFreeze(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(FightFlightFreezeModifier(self.owner))


class Explosive(StaticAbilityFacet):
    """When this unit dies, it deals 5 aoe damage to each adjacent unit."""

    def create_effects(self) -> None:
        self.register_effects(ExplosiveTrigger(self.owner, self, 5))


class Schadenfreude(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(
            SchadenfreudeDamageTrigger(self.owner),
            SchadenfreudeDebuffTrigger(self.owner),
        )


class GrizzlyMurderer(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(GrizzlyMurdererTrigger(self.owner, self))


class TelepathicSpy(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(TelepathicSpyModifier(self.owner))


class CaughtInTheMatch(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(CaughtInTheMatchTrigger(self.owner))


class HeelTurn(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(HeelTurnTrigger(self.owner, self))


class Quick(StaticAbilityFacet):

    def create_effects(self) -> None:
        self.register_effects(QuickTrigger(self.owner))


class GlassSkin(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.MAJOR)
        )


class DiamondSkin(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistance(self.owner, Status, Resistance.IMMUNE)
        )


class FlameResistant(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(SourceTypeResistance(self.owner, Burn, Resistance.MAJOR))


class LastStand(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(LastStandReplacement(self.owner, self))


class ToxicPresence(StaticAbilityFacet):
    """
    At the end of this units turn it applies 1 poison to each adjacent unit.
    """

    def create_effects(self) -> None:
        self.register_effects(ToxicPresenceTrigger(self.owner, self, 1))


class Diver(StaticAbilityFacet):
    def create_effects(self) -> None:
        self.register_effects(TerrainProtectionModifier(self.owner, Water, 1))


class ScurryInTheShadows(StaticAbilityFacet):
    """
    As long as no enemy can see this unit, it has +2 speed.
    """

    def create_effects(self) -> None:
        self.register_effects(ScurryInTheShadowsModifier(self.owner, 2))


class JukeAndJive(StaticAbilityFacet):
    """
    At the end of each of this units actions, if it isn't visible to the enemy, and it was at the
    beginning of it's action, or vice versa, it gains a stack of All In Jest.
    """

    def create_effects(self) -> None:
        self.register_effects(JukeAndJiveTrigger(self.owner, self))
