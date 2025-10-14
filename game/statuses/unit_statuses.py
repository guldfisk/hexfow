from events.eventsystem import ES
from game.core import (
    GS,
    ActivatedAbilityFacet,
    AttackFacet,
    HighestStackableRefreshableMixin,
    LowestRefreshableMixin,
    LowestStackableRefreshableMixin,
    RefreshableMixin,
    StackableMixin,
    StackableRefreshableMixin,
    StaticAbilityFacet,
    Status,
    Unit,
    UnitBlueprint,
    UnitStatus,
    UnitStatusSignature,
)
from game.effects.modifiers import (
    MustDoEffortTypeModifier,
    ParanoiaModifier,
    RootedModifier,
    SilencedModifier,
    SourceTypeResistanceModifier,
    StealthModifier,
    TerrorModifier,
    UnactivateableModifier,
    UnitArmorFlatModifier,
    UnitAttackPowerFlatModifier,
    UnitEnergyRegenFlatModifier,
    UnitMaxHealthFlatModifier,
    UnitNoCaptureModifier,
    UnitProportionalSpeedModifier,
    UnitSightFlatModifier,
    UnitSizeFlatModifier,
    UnitSpeedModifier,
)
from game.effects.replacements import (
    BufferReplacement,
    FrailReplacement,
    LuckyCharmReplacement,
    PerTurnMovePenaltyIgnoreReplacement,
    ReduceDamageReplacement,
    StunnedReplacement,
    VigorReplacement,
)
from game.effects.triggers import (
    ApplyStatusOnHitTrigger,
    BaffledTrigger,
    BellStruckTrigger,
    BurnTrigger,
    ChillTrigger,
    DecrementPerDamageTrigger,
    ExpireOnActivatedTrigger,
    ExpireOnDealDamageStatusTrigger,
    ExpireOnHitTrigger,
    ExpireOnSufferDamageStatusTrigger,
    ExpiresOnMovesTrigger,
    FleaInfestedTrigger,
    HitchedTrigger,
    OneTimeModifyMovementPointsStatusTrigger,
    PanickedTrigger,
    ParasiteTrigger,
    ParchedTrigger,
    RoundDamageTrigger,
    RoundHealTrigger,
    TiredDamageTrigger,
    TiredRestTrigger,
    TurnExpiringStatusTrigger,
)
from game.events import ExhaustUnit, Heal, Kill
from game.statuses.shortcuts import apply_status_to_unit
from game.values import Resistance, StatusIntention


class Burn(StackableMixin, UnitStatus):
    """
    At the end of each round, this unit is dealt damage equals to its stacks of burn, then remove a stack of burn.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BurnTrigger(self))


class Poison(StackableMixin, UnitStatus):
    """
    At the end of each round this unit is dealt pure damage equals to its stacks of poison.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            RoundDamageTrigger(self.parent, self, lambda: self.stacks)
        )


class Panicked(RefreshableMixin, UnitStatus):
    """
    At the end of eah round, this unit is dealt pure damage equal to the number of adjacent units.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(PanickedTrigger(self))


class Ephemeral(LowestRefreshableMixin, UnitStatus):
    """
    When this status expires, this unit dies.
    """

    default_intention = StatusIntention.DEBUFF
    dispellable = False

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent, self))


class Shocked(RefreshableMixin, UnitStatus):
    """
    -1 attack power.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, -1))


class Parasite(UnitStatus):
    """
    When this unit dies, an exhausted [horror_spawn] controlled by the owner of this debuff is spawned on
    the space this unit occupied. If the space is occupied by an attacker having
    killed this unit with a melee attack, it is instead spawned on the space the attacker attacked from.
    """

    default_intention = StatusIntention.DEBUFF
    # TODO effect when dispelled would be pretty cool?

    def create_effects(self) -> None:
        self.register_effects(ParasiteTrigger(self))


class BurstOfSpeed(UnitStatus):
    """When this unit is activated, it gains 1 movement point, and this status is removed."""

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(OneTimeModifyMovementPointsStatusTrigger(self, 1))


class Stumbling(UnitStatus):
    """
    When this unit is activated, it loses 1 movement point, and this status is removed.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(OneTimeModifyMovementPointsStatusTrigger(self, -1))


class TheyVeGotASteelChair(UnitStatus):
    """
    +2 attack power.
    """

    name = "They've Got A Steel Chair"
    default_intention = StatusIntention.BUFF
    dispellable = False

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, 2))


class SupernaturalStrength(RefreshableMixin, UnitStatus):
    """
    +2 attack power.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, 2))


class Staggered(UnitStatus):
    """Removed at the end of the turn."""

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(TurnExpiringStatusTrigger(self))


class AllInJest(StackableMixin, UnitStatus):
    """
    +1 attack power per stack.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            TurnExpiringStatusTrigger(self),
            UnitAttackPowerFlatModifier(self.parent, lambda: self.stacks),
        )


class Rooted(RefreshableMixin, UnitStatus):
    """
    This unit can't move.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(RootedModifier(self.parent))


class Fortified(HighestStackableRefreshableMixin, UnitStatus):
    """
    +1 max health per stack.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitMaxHealthFlatModifier(self.parent, lambda: self.stacks)
        )


class LuckyCharm(RefreshableMixin, UnitStatus):
    """
    If this unit would suffer exactly one damage, instead remove this buff.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(LuckyCharmReplacement(self))


class BellStruck(RefreshableMixin, UnitStatus):
    """
    When this unit receives 3 or more damage (after terrain reductions, before any
    other modifiers), apply 1 stack of <stunned> to it.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BellStruckTrigger(self.parent, self))


class MortallyWounded(UnitStatus):
    """
    When this status expires, this unit dies.
    """

    default_intention = StatusIntention.DEBUFF
    dispellable = False

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent, self))


class Tired(StackableMixin, UnitStatus):
    """
    When this unit ends its turn, it's dealt pure damage equals to the stacks of this status.
    When this unit rests, remove this status.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(TiredDamageTrigger(self), TiredRestTrigger(self))


class Terror(RefreshableMixin, UnitStatus):
    """
    This unit can't move into spaces adjacent to visible enemy units. As long as it is adjacent to an enemy unit, the only legal action this unit can take is move away.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(TerrorModifier(self.parent))


class DebilitatingVenom(RefreshableMixin, UnitStatus):
    """
    -1 attack power, and -x speed, where x half is this units speed, rounded down.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitAttackPowerFlatModifier(self.parent, -1),
            UnitProportionalSpeedModifier(self.parent, 0.5),
        )


class Shrunk(StackableRefreshableMixin, UnitStatus):
    """
    This unit has -1 attack power, -1 size and -2 max health per stack.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnitAttackPowerFlatModifier(self.parent, lambda: -self.stacks),
            UnitSizeFlatModifier(self.parent, lambda: -self.stacks),
            UnitMaxHealthFlatModifier(self.parent, lambda: -self.stacks * 2),
        )


# TODO bad name
class Blinded(RefreshableMixin, UnitStatus):
    """
    -1 sight.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitSightFlatModifier(self.parent, -1),
        )


class Silenced(RefreshableMixin, UnitStatus):
    """
    This unit can't activate abilities.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(SilencedModifier(self.parent))


class Stunned(StackableMixin, UnitStatus):
    """
    This unit cannot take any actions.
    If this unit would be become ready, instead remove a stack of this debuff.
    If this debuff would be applied to a ready unit, instead exhaust it, and apply this debuff with one less stack.
    """

    default_intention = StatusIntention.DEBUFF

    @classmethod
    def pre_merge(
        cls, signature: UnitStatusSignature, to: Unit
    ) -> UnitStatusSignature | None:
        if (context := GS.active_unit_context) and context.unit == to:
            context.should_stop = True
            return signature
        stacks = signature.stacks
        while not to.exhausted and stacks > 0:
            ES.resolve(ExhaustUnit(to))
            stacks -= 1
        return signature.branch(stacks=stacks) if stacks > 0 else None

    def create_effects(self) -> None:
        self.register_effects(StunnedReplacement(self))


class Armored(RefreshableMixin, UnitStatus):
    """
    +1 armor.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(UnitArmorFlatModifier(self.parent, 1))


class Hitched(UnitStatus):
    """
    When the applying unit moves, this unit is moved into the space it previously occupied.
    Expires at the end of the turn.
    """

    def create_effects(self) -> None:
        self.register_effects(
            HitchedTrigger(self.source.parent, self.parent),
            TurnExpiringStatusTrigger(self),
        )


class Slimed(RefreshableMixin, UnitStatus):
    """
    -1 speed.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitSpeedModifier(self.parent, -1))


class Paranoia(RefreshableMixin, UnitStatus):
    """
    When this unit isn't active, it does not provide vision for its controller. When it is, no other units does.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(ParanoiaModifier(self.parent))


class DishonorableCoward(RefreshableMixin, UnitStatus):
    """
    This unit can't capture points. Remove this status when this unit damages an enemy unit with an attack or ability.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitNoCaptureModifier(self.parent), ExpireOnDealDamageStatusTrigger(self)
        )


class SenselessRage(RefreshableMixin, UnitStatus):
    """+1 attack power. If this unit can attack, it must."""

    def create_effects(self) -> None:
        self.register_effects(
            MustDoEffortTypeModifier(self.parent, AttackFacet),
            UnitAttackPowerFlatModifier(self.parent, 1),
        )


class Compulsion(RefreshableMixin, UnitStatus):
    """
    If this unit can use an ability, it must.
    """

    def create_effects(self) -> None:
        self.register_effects(
            MustDoEffortTypeModifier(self.parent, ActivatedAbilityFacet)
        )


class Turbo(RefreshableMixin, UnitStatus):
    """+1 speed and -1 armor."""

    def create_effects(self) -> None:
        self.register_effects(
            UnitSpeedModifier(self.parent, 1), UnitArmorFlatModifier(self.parent, -1)
        )


class TaintedBond(UnitStatus):
    """
    Whenever a unit with a linked Tainted Bond status suffers damage not from a Tainted Bond
    status, this status deals 1 pure damage to this unit.
    """


class Enfeebled(RefreshableMixin, UnitStatus):
    """-2 attack power."""

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, -2))


class Focused(RefreshableMixin, UnitStatus):
    """+1 energy regen."""

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(UnitEnergyRegenFlatModifier(self.parent, 1))


class Baffled(UnitStatus):
    """
    When this unit finishes it's turn, if it acted, stun it. Then remove this status.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BaffledTrigger(self))


class Regenerating(RefreshableMixin, UnitStatus):
    """
    At the end of each round, this unit heals 1.
    When this unit is damaged, remove this status.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            RoundHealTrigger(self.parent, 1, self),
            ExpireOnSufferDamageStatusTrigger(self),
        )


class Shame(RefreshableMixin, UnitStatus):
    """
    This unit can't capture objectives.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitNoCaptureModifier(self.parent))


class Corroded(StackableRefreshableMixin, UnitStatus):
    """
    -1 armor per stack.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitArmorFlatModifier(self.parent, lambda: -self.stacks))


class Pathfinding(RefreshableMixin, UnitStatus):
    """This unit ignores one movement penalty each turn."""

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(PerTurnMovePenaltyIgnoreReplacement(self.parent, 1))


class Camouflaged(RefreshableMixin, UnitStatus):
    """This unit is stealth. Remove this status when this unit moves."""

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(StealthModifier(self.parent), ExpiresOnMovesTrigger(self))


class KeenVision(RefreshableMixin, UnitStatus):
    """+1 sight."""

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(UnitSightFlatModifier(self.parent, 1))


class Freezing(RefreshableMixin, UnitStatus):
    """-1 attack power and -1 speed."""

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitSpeedModifier(self.parent, -1),
            UnitAttackPowerFlatModifier(self.parent, -1),
        )


class Frigid(LowestStackableRefreshableMixin, UnitStatus):
    """
    Whenever this unit suffers damage, remove that many stacks. When the last is
    removed, apply 1 stack of <stunned> to this unit.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(DecrementPerDamageTrigger(self))

    def on_fully_decremented(self) -> None:
        apply_status_to_unit(self.parent, "stunned", self, stacks=1)


class FrostShield(RefreshableMixin, UnitStatus):
    """
    If this unit would suffer damage, it suffers 1 less.
    When a unit hits this unit, apply <freezing> to it for 2 rounds.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            ReduceDamageReplacement(self.parent, 1),
            ApplyStatusOnHitTrigger(
                self.parent,
                UnitStatusSignature(UnitStatus.get("freezing"), self, duration=2),
            ),
        )


class NaturesGrace(RefreshableMixin, UnitStatus):
    """
    At the end of each round, this unit heals 1.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(RoundHealTrigger(self.parent, 1, self))


class Critterized(RefreshableMixin, UnitStatus):
    """
    This unit is turned into a [rabbit] (it keeps its damage and energy).
    """

    def on_apply(self) -> None:
        self.parent.set_blueprint(UnitBlueprint.get_class("rabbit"))

    def on_remove(self) -> None:
        self.parent.set_blueprint(self.parent.original_blueprint)


class BeautySleep(RefreshableMixin, UnitStatus):
    """
    This unit can't be activated. Remove this status when this unit suffers damage.
    When this status expires (not from being removed from damage), heal this unit 3.
    """

    def create_effects(self) -> None:
        self.register_effects(
            UnactivateableModifier(self.parent), ExpireOnSufferDamageStatusTrigger(self)
        )

    def on_expires(self) -> None:
        ES.resolve(Heal(self.parent, 3, self))


class MagicStrength(RefreshableMixin, UnitStatus):
    """
    +1 attack power and energy regeneration.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitEnergyRegenFlatModifier(self.parent, 1),
            UnitAttackPowerFlatModifier(self.parent, 1),
        )


class FleaInfested(RefreshableMixin, UnitStatus):
    """
    At the end of each round, this status controller chooses an unoccupied space adjacent to this unit.
    They spawn an [annoying_flea] there.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(FleaInfestedTrigger(self.parent, self.controller))


class Chill(RefreshableMixin, UnitStatus):
    """
    At the end of each round, if this unit isn't adjacent to an allied unit, it's dealt 1 pure damage.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(ChillTrigger(self.parent, self))


class Buffer(StackableRefreshableMixin, UnitStatus):
    """
    If this unit would suffer damage, instead remove a stack of this status.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(BufferReplacement(self))


class Rolling(UnitStatus):
    """
    +3 movement. Remove this status when this unit hits another unit.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitSpeedModifier(self.parent, 3), ExpireOnHitTrigger(self)
        )


class MagicWard(RefreshableMixin, UnitStatus):
    """
    Reduce damage dealt to this unit by abilities and statuses to two thirds, rounded up.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            SourceTypeResistanceModifier(
                self.parent,
                (ActivatedAbilityFacet, StaticAbilityFacet, Status),
                Resistance.MINOR,
            )
        )


class Vigor(StackableRefreshableMixin, UnitStatus):
    """
    If a debuff would be applied to this unit, instead remove a stack of this status.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(VigorReplacement(self))


class RolledUp(UnitStatus):
    """
    +1 armor. Remove this status when this unit is activated.
    """

    default_intention = StatusIntention.BUFF

    def create_effects(self) -> None:
        self.register_effects(
            UnitArmorFlatModifier(self.parent, 1), ExpireOnActivatedTrigger(self)
        )


class Frail(HighestStackableRefreshableMixin, UnitStatus):
    """
    If this unit would suffer damage less than the amount of stacks of this debuff, it suffers damage
    equal to the stacks of this debuff instead.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(FrailReplacement(self))


class Parched(RefreshableMixin, UnitStatus):
    """
    At the end of this units turn, if it acted and doesn't have any remaining movement points,
    it is dealt 1 pure damage. (Exclusive costs sets movement points to zero).
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(ParchedTrigger(self.parent, self))
