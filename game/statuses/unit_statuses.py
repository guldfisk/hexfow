from events.eventsystem import ES
from game.core import (
    GS,
    HighestStackableRefreshableMixin,
    LowestRefreshableMixin,
    RefreshableMixin,
    StackableMixin,
    StackableRefreshableMixin,
    Unit,
    UnitStatus,
    UnitStatusSignature,
)
from game.effects.modifiers import (
    MustAttackModifier,
    ParanoiaModifier,
    RootedModifier,
    SilencedModifier,
    TerrorModifier,
    UnitArmorFlatModifier,
    UnitAttackPowerFlatModifier,
    UnitMaxHealthFlatModifier,
    UnitNoCaptureModifier,
    UnitProportionalSpeedModifier,
    UnitSightFlatModifier,
    UnitSizeFlatModifier,
    UnitSpeedModifier,
)
from game.effects.replacements import LuckyCharmReplacement, StunnedReplacement
from game.effects.triggers import (
    BellStruckTrigger,
    BurnTrigger,
    ExpireOnDealDamageStatusTrigger,
    HitchedTrigger,
    OneTimeModifyMovementPointsStatusTrigger,
    PanickedTrigger,
    ParasiteTrigger,
    RoundDamageTrigger,
    TurnExpiringStatusTrigger,
)
from game.events import ExhaustUnit, Kill
from game.values import StatusIntention


class Burn(StackableMixin, UnitStatus):
    """
    At the end of each round, this unit suffers damage equals to its stacks of burn, then remove a stack of burn.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BurnTrigger(self))


class Poison(StackableMixin, UnitStatus):
    """
    At the end of each round this unit suffers pure damage equals to its stacks of poison.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(
            RoundDamageTrigger(self.parent, self, lambda: self.stacks)
        )


class Panicked(RefreshableMixin, UnitStatus):
    """
    At the end of eah round, this unit suffers pure damage equal to the number of adjacent units.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(PanickedTrigger(self))


class Ephemeral(LowestRefreshableMixin, UnitStatus):
    """
    When this status expires, this unit dies.
    """

    default_intention = StatusIntention.DEBUFF

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


class Shocked(RefreshableMixin, UnitStatus):
    """
    -1 attack power.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, -1))


class Parasite(UnitStatus):
    """
    When this unit dies, an exhausted Horror Spawn (3 health, 2 speed, 1 sight, Small, 2 damage melee attack) controlled
    by the owner of this debuff is spawned on the space this unit occupied. If the space is occupied by an attacker having
    killed this unit with a melee attack, it is instead spawned on the space the attacker attacked from.
    """

    default_intention = StatusIntention.DEBUFF

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
    This unit can't move or melee attack.
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
    other modifiers), it is exhausted.
    """

    default_intention = StatusIntention.DEBUFF

    def create_effects(self) -> None:
        self.register_effects(BellStruckTrigger(self.parent))


class MortallyWounded(UnitStatus):
    """
    When this status expires, this unit dies.
    """

    default_intention = StatusIntention.DEBUFF

    def on_expires(self) -> None:
        ES.resolve(Kill(self.parent))


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
    def on_apply(
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
            MustAttackModifier(self.parent), UnitAttackPowerFlatModifier(self.parent, 1)
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
    status, this status deals that much pure damage to this unit.
    """


class Enfeebled(RefreshableMixin, UnitStatus):
    """-2 attack power."""

    def create_effects(self) -> None:
        self.register_effects(UnitAttackPowerFlatModifier(self.parent, -2))
