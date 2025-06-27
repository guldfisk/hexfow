from __future__ import annotations

import dataclasses
import re
from abc import ABC, abstractmethod, ABCMeta
from collections import defaultdict
from typing import (
    ClassVar,
    Literal,
    Any,
    TypeVar,
    Iterator,
    Generic,
    Self,
    Iterable,
    TypeAlias,
)
from typing import Mapping

from bidict import bidict

from debug_utils import dp
from events.eventsystem import (
    Modifiable,
    ModifiableAttribute,
    modifiable,
    ES,
    ModifiableMeta,
)
from game.decisions import (
    DecisionPoint,
    Option,
    TargetProfile,
    O,
    JSON,
    NoTarget,
    Serializable,
    SerializationContext,
    IDMap,
)
from game.has_effects import HasEffects
from game.interface import Connection
from game.map.coordinates import CC, line_of_sight_obstructed
from game.map.geometry import hex_circle
from game.player import Player
from game.turn_order import TurnOrder
from game.values import (
    Size,
    DamageType,
    VisionObstruction,
    StatusIntention,
    Resistance,
)
from game.tests.conftest import EventLogger


A = TypeVar("A", bound=DecisionPoint)
T = TypeVar("T")
S = TypeVar("S")


# TODO wtf if this
class VisionBound(Serializable):
    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"id": context.id_map.get_id_for(self), **self.serialize_values(context)}


class MoveOption(Option[O]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class EffortOption(Option[O]):
    facet: EffortFacet

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"facet": self.facet.serialize()}


@dataclasses.dataclass
class ActivateUnitOption(Option[O]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


class SkipOption(Option[None]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class HasStatuses(HasEffects, Generic[S]):
    statuses: list[Status] = dataclasses.field(default_factory=list, init=False)

    # TODO by player, we need controller?
    def add_status(self, status: S) -> S:
        # TODO should prob set parent
        for existing_status in self.statuses:
            if type(existing_status) == type(status) and existing_status.merge(status):
                return existing_status
        self.statuses.append(status)
        status.create_effects()
        return status

    def remove_status(self, status: Status) -> None:
        try:
            self.statuses.remove(status)
        except ValueError:
            pass
        status.deregister()


H = TypeVar("H", bound=HasStatuses)


class _FacetMeta(ModifiableMeta):

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        if ABC not in bases:
            if "identifier" not in attributes:
                attributes["identifier"] = "_".join(
                    s.lower() for s in re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
                )
            if "name" not in attributes:
                attributes["name"] = " ".join(
                    re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
                )
        cls = super().__new__(metacls, name, bases, attributes, **kwargs)
        if ABC not in bases and "description" not in attributes and cls.__doc__:
            cls.description = "\n".join(
                ln.strip() for ln in cls.__doc__.split("\n")
            ).strip()
        return cls


# TODO a facet should not have statuses
class Facet(HasStatuses, Modifiable, ABC, metaclass=_FacetMeta):
    # TODO hmm
    # name: ClassVar[str]
    # TODO hm
    identifier: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[str] = "not defined"
    description: ClassVar[str | None] = None
    flavor: ClassVar[str | None] = None

    def __init__(self, owner: Unit):
        super().__init__(parent=owner)

        # TODO should be able to unify this with parent from has_statuses or whatever
        self.owner = owner

    # TODO common interface?
    def create_effects(self) -> None: ...

    # TODO lmao
    @classmethod
    def serialize(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
        }


class EffortCost(ABC):

    @abstractmethod
    def can_be_payed(self, context: ActiveUnitContext) -> bool:
        pass

    @abstractmethod
    def pay(self, context: ActiveUnitContext) -> None:
        pass

    @classmethod
    @abstractmethod
    def merge(cls, instances: list[Self]) -> Self: ...

    def __or__(self, other: EffortCost | EffortCostSet) -> EffortCostSet:
        return EffortCostSet(
            [self, other]
            if isinstance(other, EffortCost)
            else [self, *other.costs.values()]
        )

    @abstractmethod
    def serialize_values(self) -> dict[str, Any]: ...

    def serialize(self) -> dict[str, Any]:
        return {"type": self.__class__.__name__, **self.serialize_values()}


class EffortCostSet:

    def __init__(self, costs: Iterable[EffortCost] = ()):
        grouped: dict[type[EffortCost], list[EffortCost]] = defaultdict(list)
        for cost in costs:
            grouped[type(cost)].append(cost)
        self.costs = {
            cost_type: cost_type.merge(_costs) for cost_type, _costs in grouped.items()
        }

    @abstractmethod
    def can_be_payed(self, context: ActiveUnitContext) -> bool:
        return all(cost.can_be_payed(context) for cost in self.costs.values())

    @abstractmethod
    def pay(self, context: ActiveUnitContext) -> None:
        for cost in self.costs.values():
            cost.pay(context)

    def __or__(self, other: EffortCost | EffortCostSet) -> EffortCostSet:
        return EffortCostSet(
            [*self.costs.values(), other]
            if isinstance(other, EffortCost)
            else [self.costs.values(), *other.costs.values()]
        )

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__, ", ".join(str(c) for c in self.costs.values())
        )

    def __bool__(self) -> bool:
        return bool(self.costs)

    def serialize(self) -> dict[str, Any]:
        return {"atoms": [cost.serialize() for cost in self.costs.values()]}


@dataclasses.dataclass
class MovementCost(EffortCost):
    amount: int

    def can_be_payed(self, context: ActiveUnitContext) -> bool:
        return not context.has_acted or self.amount <= context.movement_points

    def pay(self, context: ActiveUnitContext) -> None:
        context.movement_points -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class ExclusiveCost(EffortCost):

    def can_be_payed(self, context: ActiveUnitContext) -> bool:
        return not context.has_acted

    def pay(self, context: ActiveUnitContext) -> None:
        context.movement_points = min(context.movement_points, 0)
        context.should_stop = True

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls()

    def serialize_values(self) -> dict[str, Any]:
        return {}


@dataclasses.dataclass
class EnergyCost(EffortCost):
    amount: int

    def can_be_payed(self, context: ActiveUnitContext) -> bool:
        return self.amount <= context.unit.energy

    def pay(self, context: ActiveUnitContext) -> None:
        context.unit.energy -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class EffortFacet(Facet, Modifiable):
    cost: ClassVar[EffortCostSet | EffortCost | None] = None
    # TODO these should be some signature together
    combinable: ClassVar[bool] = False
    max_activations: int | None = 1

    # TODO how does overriding work with modifiable? also, can it be abstract?
    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]: ...

    @classmethod
    def get_cost_set(cls) -> EffortCostSet:
        if isinstance(cls.cost, EffortCost):
            return EffortCostSet([cls.cost])
        return cls.cost or EffortCostSet()

    # TODO should prob be modifyable. prob need some way to lock in costs for effort
    #  options then.
    def get_cost(self) -> EffortCostSet:
        return self.get_cost_set()

    # TODO how does overriding work with modifiable?
    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            (
                self.max_activations is None
                or context.activated_facets[self.__class__.__name__]
                < self.max_activations
            )
            and self.get_cost().can_be_payed(context)
            and self.get_legal_targets(None)
        )

    @classmethod
    def serialize(cls) -> JSON:
        return {
            **super().serialize(),
            "cost": cls.get_cost_set().serialize(),
            "combineable": cls.combinable,
            "max_activations": cls.max_activations,
        }


class AttackFacet(EffortFacet): ...


# TODO cleanup typevar definitions and names
C = TypeVar("C", bound=AttackFacet)


# TODO maybe this is all attacks, and "aoe attacks" are all abilities?
class SingleTargetAttackFacet(AttackFacet):
    damage_type: ClassVar[DamageType]
    damage: ClassVar[int]
    ap: ClassVar[int] = 0

    def get_damage_modifier_against(self, unit: Unit) -> int | None:
        # TODO blah internal hook
        ...

    @modifiable
    def get_damage_signature_against(self, unit: Unit) -> DamageSignature:
        return DamageSignature(
            max(
                self.damage
                + (self.get_damage_modifier_against(unit) or 0)
                + self.owner.attack_power.g(),
                0,
            ),
            self,
            type=self.damage_type,
            ap=self.ap,
        )

    def resolve_pre_damage_effects(self, defender: Unit) -> None: ...
    def resolve_post_damage_effects(self, defender: Unit) -> None: ...

    @classmethod
    def serialize(cls) -> JSON:
        return {**super().serialize(), "damage": cls.damage, "ap": cls.ap}


class MeleeAttackFacet(SingleTargetAttackFacet):
    category = "melee_attack"
    damage_type = DamageType.MELEE

    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]:
        # TODO handle vision
        return [
            unit
            for unit in GS().map.get_neighboring_units_off(self.owner)
            if unit.controller != self.owner.controller
            and unit.is_visible_to(self.owner.controller)
            and unit.can_be_attacked_by(self)
            # TODO test
            and GS().map.hex_off(unit).is_passable_to(self.owner)
        ]

    def get_cost(self) -> EffortCostSet:
        return (self.cost or EffortCostSet()) | MovementCost(1)

    # TODO should prob be modifiable.
    def should_follow_up(self) -> bool:
        return True


# TODO where should logic for these be?
def is_vision_obstructed_for_unit_at(unit: Unit, cc: CC) -> bool:
    match GS().vision_obstruction_map[unit.controller][cc]:
        case VisionObstruction.FULL:
            return True
        case VisionObstruction.HIGH_GROUND:
            return not GS().map.hex_off(unit).terrain.is_highground()
        case _:
            return False


def line_of_sight_obstructed_for_unit(unit: Unit, line_from: CC, line_to: CC) -> bool:
    return line_of_sight_obstructed(
        line_from, line_to, lambda cc: is_vision_obstructed_for_unit_at(unit, cc)
    )


class RangedAttackFacet(SingleTargetAttackFacet):
    category = "ranged_attack"
    damage_type = DamageType.RANGED
    range: ClassVar[int]

    @modifiable
    def get_legal_targets(self, _: None = None) -> list[Unit]:
        return [
            unit
            for unit in GS().map.get_units_within_range_off(self.owner, self.range)
            if unit.controller != self.owner.controller
            # TODO test on this
            and unit.is_visible_to(self.owner.controller)
            and not line_of_sight_obstructed_for_unit(
                self.owner,
                GS().map.position_off(self.owner),
                GS().map.position_off(unit),
            )
            and unit.can_be_attacked_by(self)
        ]

    @classmethod
    def serialize(cls) -> JSON:
        return {**super().serialize(), "range": cls.range}


class ActivatedAbilityFacet(EffortFacet, Generic[O]):
    category = "activated_ability"

    @abstractmethod
    def get_target_profile(self) -> TargetProfile[O] | None: ...

    @abstractmethod
    def perform(self, target: O) -> None: ...

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            (
                self.max_activations is None
                or context.activated_facets[self.__class__.__name__]
                < self.max_activations
            )
            and self.get_cost().can_be_payed(context)
            and self.get_target_profile() is not None
        )


class StaticAbilityFacet(Facet):
    category = "static_ability"


class _StatusMeta(ABCMeta):
    registry: ClassVar[dict[str, Status]] = {}

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        if ABC not in bases:
            if "identifier" not in attributes:
                attributes["identifier"] = "_".join(
                    s.lower() for s in re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
                )
        cls = super().__new__(metacls, name, bases, attributes, **kwargs)
        if ABC not in bases:
            metacls.registry[cls.identifier] = cls
        return cls


class Status(HasEffects[H], Serializable, ABC, metaclass=_StatusMeta):
    registry: ClassVar[dict[str, Status]]
    identifier: ClassVar[str]

    def __init__(
        self,
        *,
        controller: Player | None = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: H | None,
    ):
        super().__init__(parent=parent)
        self.controller = controller
        self.duration = duration
        self.stacks = stacks

    def merge(self, incoming: Self) -> bool:
        return False

    def is_hidden_for(self, player: Player) -> bool:
        return False

    def create_effects(self) -> None: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "type": self.identifier,
            "duration": self.duration,
            "stacks": self.stacks,
        }

    def on_expires(self) -> None:
        # TODO blah
        pass

    def remove(self) -> None:
        # TODO is this all?
        self.parent.remove_status(self)

    def decrement_duration(self) -> None:
        if self.duration is None:
            return
        self.duration -= 1
        if self.duration <= 0:
            self.on_expires()
            self.remove()

    def decrement_stacks(self) -> None:
        self.stacks -= 1
        if self.stacks <= 0:
            self.remove()


FULL_ENERGY: Literal["FULL_ENERGY"] = "FULL_ENERGY"


class UnitBlueprint:
    registry: ClassVar[dict[str, UnitBlueprint]] = {}

    def __init__(
        self,
        name: str,
        *,
        health: int,
        speed: int,
        sight: int,
        armor: int = 0,
        energy: int = 0,
        starting_energy: int | FULL_ENERGY = FULL_ENERGY,
        size: Size = Size.MEDIUM,
        # TODO should this be a stat?
        aquatic: bool = False,
        facets: list[type[Facet]] | None = None,
        price: int | None,
        max_count: int = 1,
    ):
        self.name = name
        self.health = health
        self.speed = speed
        self.sight = sight
        self.armor = armor
        self.energy = energy
        self.starting_energy = starting_energy
        self.size = size
        self.aquatic = aquatic
        self.facets = facets or []
        self.identifier = re.sub("_+", "_", re.sub("[^a-z]", "_", self.name.lower()))
        self.registry[self.identifier] = self

        self.price = price
        self.max_count = max_count

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"

    def serialize(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            # TODO how should this work?
            "small_image": f"/src/images/units/{self.identifier}_small.png",
            "health": self.health,
            "speed": self.speed,
            "sight": self.sight,
            "armor": self.armor,
            "energy": self.energy,
            # TODO
            "size": self.size.name[0],
            "aquatic": self.aquatic,
            "facets": [facet.serialize() for facet in self.facets],
            "price": self.price,
        }


class Unit(HasStatuses, Modifiable, VisionBound):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    armor: ModifiableAttribute[None, int]
    max_energy: ModifiableAttribute[None, int]
    energy_regen: ModifiableAttribute[None, int]
    size: ModifiableAttribute[None, Size]
    attack_power: ModifiableAttribute[None, int]
    aquatic: ModifiableAttribute[None, bool]
    is_broken: ModifiableAttribute[None, bool]

    def __init__(
        self, controller: Player, blueprint: UnitBlueprint, exhausted: bool = False
    ):
        super().__init__()

        self.controller = controller
        self.blueprint = blueprint

        self.damage: int = 0
        self.max_health.set(blueprint.health)
        self.speed.set(blueprint.speed)
        self.sight.set(blueprint.sight)
        self.armor.set(blueprint.armor)
        self.max_energy.set(blueprint.energy)
        self.energy_regen.set(1)
        self.energy: int = (
            blueprint.starting_energy
            if isinstance(blueprint.starting_energy, int)
            else blueprint.energy
        )
        self.size.set(blueprint.size)
        self.attack_power.set(0)
        self.aquatic.set(blueprint.aquatic)
        self.is_broken.set(False)
        self.exhausted = exhausted

        self.attacks: list[AttackFacet] = []
        self.activated_abilities: list[ActivatedAbilityFacet] = []
        self.static_abilities: list[StaticAbilityFacet] = []

        for facet in blueprint.facets:
            if issubclass(facet, AttackFacet):
                self.attacks.append(facet(self))
            elif issubclass(facet, ActivatedAbilityFacet):
                self.activated_abilities.append(facet(self))
            elif issubclass(facet, StaticAbilityFacet):
                self.static_abilities.append(facet(self))

        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.create_effects()

    def get_primary_attack(self, of_type: type[C] | None = None) -> C | None:
        for attack in self.attacks:
            if of_type is None or isinstance(attack, of_type):
                return attack
        return None

    @modifiable
    def get_resistance_against(self, signature: DamageSignature) -> Resistance:
        return Resistance.NONE

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return GS().map.hex_off(self).get_terrain_protection_for(request)

    def suffer_damage(self, signature: DamageSignature) -> int:
        damage = min(
            signature.amount, self.health - 1 if not signature.lethal else self.health
        )
        self.damage += damage
        return damage

    @modifiable
    def can_be_activated(self, _: None = None) -> bool:
        return not self.exhausted

    @modifiable
    def can_be_attacked_by(self, attack: AttackFacet) -> bool:
        return True

    @modifiable
    def blocks_vision_for(self, player: Player) -> bool:
        size = self.size.g()
        if size == Size.LARGE:
            return True
        if size == Size.SMALL:
            return False
        return player != self.controller

    @modifiable
    def provides_vision_for(self, _: None) -> set[Player]:
        return {self.controller}

    @modifiable
    def can_see(self, space: Hex) -> bool:
        if space.map.distance_between(self, space) > self.sight.g():
            return False
        return not line_of_sight_obstructed_for_unit(
            self, space.map.position_off(self), space.position
        )

    @modifiable
    def is_hidden_for(self, player: Player) -> bool:
        return False

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return (
            player == self.controller or GS().map.hex_off(self).is_visible_to(player)
        ) and not self.is_hidden_for(player)

    # TODO should effects modifying get_legal_options on movement modify this instead?
    @modifiable
    def get_potential_move_destinations(self, _: None) -> list[Hex]:
        return [
            _hex
            for _hex in GS().map.get_neighbors_off(self)
            if not _hex.is_visible_to(self.controller) or _hex.can_move_into(self)
        ]

    @modifiable
    def get_legal_options(self, context: ActiveUnitContext) -> list[Option]:
        options = []
        if context.movement_points > 0:
            if moveable_hexes := self.get_potential_move_destinations(None):
                options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))
        if context.movement_points >= 0:
            for facet in self.attacks:
                if isinstance(
                    facet, (MeleeAttackFacet, RangedAttackFacet)
                ) and facet.can_be_activated(GS().active_unit_context):
                    options.append(
                        EffortOption(
                            facet,
                            target_profile=OneOfUnits(facet.get_legal_targets(None)),
                        )
                    )
            for facet in self.activated_abilities:
                if facet.can_be_activated(GS().active_unit_context):
                    options.append(
                        EffortOption(facet, target_profile=facet.get_target_profile())
                    )
        if not context.has_acted or options:
            options.append(SkipOption(target_profile=NoTarget()))
        return options

    def on_map(self) -> bool:
        return self in GS().map.unit_positions

    @property
    def health(self) -> int:
        return self.max_health.g() - self.damage

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "blueprint": self.blueprint.identifier,
            "controller": self.controller.name,
            "max_health": self.max_health.g(),
            "damage": self.damage,
            "speed": self.speed.g(),
            "sight": self.sight.g(),
            "max_energy": self.max_energy.g(),
            "energy": self.energy,
            # TODO
            "size": self.size.g().name[0],
            "armor": self.armor.g(),
            "exhausted": self.exhausted,
            "statuses": [
                status.serialize(context)
                for status in self.statuses
                if not status.is_hidden_for(context.player)
            ],
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.blueprint.name}, {self.controller.name}, {id(self)})"


class UnitStatus(Status[Unit], ABC):
    default_intention: ClassVar[StatusIntention | None] = None

    def __init__(
        self,
        *,
        controller: Player | None = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: H | None,
        intention: StatusIntention,
    ):
        super().__init__(
            controller=controller, duration=duration, stacks=stacks, parent=parent
        )
        self.intention = intention

    @classmethod
    def get(cls, identifier: str) -> type[UnitStatus]:
        return cls.registry[identifier]

    def serialize(self, context: SerializationContext) -> JSON:
        return {**super().serialize(context), "intention": self.intention.value}


@dataclasses.dataclass
class StatusSignature:
    status_type: type[UnitStatus]
    source: Source
    stacks: int | None = None
    duration: int | None = None
    intention: StatusIntention | None = None


@dataclasses.dataclass
class OneOfUnits(TargetProfile[Unit]):
    units: list[Unit]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.units]
        }

    def parse_response(self, v: Any) -> Unit:
        return self.units[v["index"]]


@dataclasses.dataclass
class NOfUnits(TargetProfile[list[Unit]]):
    units: list[Unit]
    select_count: int
    labels: list[str]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.units],
            "select_count": self.select_count,
            "labels": self.labels,
        }

    def parse_response(self, v: Any) -> list[Unit]:
        indexes = v["indexes"]
        # TODO nice validation LMAO
        assert len(indexes) == self.select_count
        assert len(indexes) == len(set(indexes))
        return [self.units[idx] for idx in indexes]


class DurationStatusMixin:
    duration: int | None

    def merge(self, incoming: Self) -> bool:
        if (
            incoming.duration is None
            or self.duration is None
            or (incoming.duration > self.duration)
        ):
            self.duration = incoming.duration
        return True


# TODO ABC, where should this be?
# TODO just use the mixin instead
class RefreshableDurationUnitStatus(DurationStatusMixin, UnitStatus, ABC): ...


class NoTargetActivatedAbility(ActivatedAbilityFacet[None]):
    def get_target_profile(self) -> TargetProfile[None] | None:
        return NoTarget()


class SingleTargetActivatedAbility(ActivatedAbilityFacet[Unit]):
    range: ClassVar[int] = 1
    requires_los: ClassVar[bool] = True

    def can_target_unit(self, unit: Unit) -> bool:
        return True

    def get_target_profile(self) -> TargetProfile[Unit] | None:
        if units := [
            unit
            for unit in GS().map.get_units_within_range_off(self.owner, self.range)
            if self.can_target_unit(unit)
            and unit.is_visible_to(self.owner.controller)
            and (
                not self.requires_los
                or not line_of_sight_obstructed_for_unit(
                    self.owner,
                    GS().map.position_off(self.owner),
                    GS().map.position_off(unit),
                )
            )
        ]:
            return OneOfUnits(units)


class SingleAllyActivatedAbility(SingleTargetActivatedAbility):
    can_target_self: ClassVar[bool] = True

    def can_target_unit(self, unit: Unit) -> bool:
        return unit.controller == self.owner.controller and (
            self.can_target_self or unit != self.owner
        )


class SingleEnemyActivatedAbility(SingleTargetActivatedAbility):

    def can_target_unit(self, unit: Unit) -> bool:
        return unit.controller != self.owner.controller


@dataclasses.dataclass
class HexSpec:
    terrain_type: type[Terrain]
    is_objective: bool


@dataclasses.dataclass
class Landscape:
    terrain_map: Mapping[CC, HexSpec]
    # deployment_zones: Collection[AbstractSet[CubeCoordinate]]


@dataclasses.dataclass
class TerrainProtectionRequest:
    unit: Unit
    damage_type: DamageType


class Terrain(HasEffects, ABC):
    # TODO
    identifier: ClassVar[str]

    def create_effects(self, space: Hex) -> None: ...

    def is_water(self) -> bool:
        return False

    def blocks_vision(self) -> bool:
        return False

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return 0

    # TODO modifyable or whatever
    def is_highground(self) -> bool:
        return False


@dataclasses.dataclass
class Hex(Modifiable, HasStatuses, Serializable):
    position: CC
    terrain: Terrain
    is_objective: bool
    map: HexMap

    @modifiable
    def is_passable_to(self, unit: Unit) -> bool:
        if self.terrain.is_water():
            return unit.aquatic.g()
        return True

    @modifiable
    def is_occupied_for(self, unit: Unit) -> bool:
        # TODO should prob be inverted?
        return not self.map.unit_on(self)

    @modifiable
    def can_move_into(self, unit: Unit) -> bool:
        return self.is_occupied_for(unit) and self.is_passable_to(unit)

    @modifiable
    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_in_penalty_for(unit)

    @modifiable
    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_out_penalty_for(unit)

    @modifiable
    def blocks_vision_for(self, player: Player) -> VisionObstruction:
        if self.terrain.blocks_vision():
            return VisionObstruction.FULL
        if (unit := self.map.unit_on(self)) and unit.blocks_vision_for(player):
            return VisionObstruction.FULL
        if self.terrain.is_highground():
            return VisionObstruction.HIGH_GROUND
        return VisionObstruction.NONE

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return GS().vision_map[player][self.position]

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return self.terrain.get_terrain_protection_for(request)

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "cc": self.position.serialize(),
            "terrain": self.terrain.__class__.identifier,
            "is_objective": self.is_objective,
            **(
                {
                    "visible": True,
                    "last_visible_round": GS().round_counter,
                    "unit": (
                        unit.serialize(context)
                        if (unit := self.map.unit_on(self))
                        and unit.is_visible_to(context.player)
                        else None
                    ),
                    "statuses": [
                        status.serialize(context)
                        for status in self.statuses
                        if not status.is_hidden_for(context.player)
                    ],
                }
                if self.is_visible_to(context.player)
                else (
                    {
                        "visible": False,
                        "last_visible_round": old_hex["last_visible_round"],
                        # TODO big hmm
                        # "unit": (
                        #     old_hex["unit"]
                        #     if old_hex["unit"]
                        #     and not context.id_map.has_id(old_hex["unit"]["id"])
                        #     else None
                        # ),
                        "unit": old_hex["unit"],
                        "statuses": old_hex["statuses"],
                    }
                    if context.last_hex_states
                    and (old_hex := context.last_hex_states.get(self.position))
                    else {
                        "visible": False,
                        "last_visible_round": None,
                        "unit": None,
                        "statuses": [],
                    }
                )
            ),
        }

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(id(self))

    def __repr__(self):
        return f"{type(self).__name__}({self.position.r}, {self.position.h})"


Source: TypeAlias = Facet | Status | None


@dataclasses.dataclass
class DamageSignature:
    amount: int
    source: Source
    type: DamageType = DamageType.PHYSICAL
    ap: int = 0
    lethal: bool = True

    def branch(self, **kwargs: Any) -> DamageSignature:
        return type(self)(
            **{
                field.name: getattr(self, field.name)
                for field in dataclasses.fields(self)
            }
            | kwargs
        )

    def with_damage(self, amount: int) -> DamageSignature:
        return self.branch(amount=amount)


class HexStatus(Status[Hex], ABC):

    @classmethod
    def get(cls, identifier: str) -> type[HexStatus]:
        return cls.registry[identifier]


# TODO inherit from status signature base?
@dataclasses.dataclass
class HexStatusSignature:
    status_type: type[HexStatus]
    source: Source
    stacks: int | None = None
    duration: int | None = None


class SingleHexTargetActivatedAbility(ActivatedAbilityFacet[Hex]):
    range: ClassVar[int] = 1
    requires_los: ClassVar[bool] = True
    requires_vision: ClassVar[bool] = True

    def can_target_hex(self, hex_: Hex) -> bool:
        return True

    def get_target_profile(self) -> TargetProfile[Hex] | None:
        if hexes := [
            _hex
            for _hex in GS().map.get_hexes_within_range_off(self.owner, self.range)
            if (not self.requires_vision or _hex.is_visible_to(self.owner.controller))
            and (
                not self.requires_los
                or not line_of_sight_obstructed_for_unit(
                    self.owner,
                    GS().map.position_off(self.owner),
                    _hex.position,
                )
            )
            and self.can_target_hex(_hex)
        ]:
            return OneOfHexes(hexes)


@dataclasses.dataclass
class OneOfHexes(TargetProfile[Hex]):
    hexes: list[Hex]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"options": [_hex.position.serialize() for _hex in self.hexes]}

    def parse_response(self, v: Any) -> Hex:
        return self.hexes[v["index"]]


# TODO where, maybe in "aoe_target_profiles.py"?
@dataclasses.dataclass
class ConsecutiveAdjacentHexes(TargetProfile[list[Hex]]):
    adjacent_to: Hex
    arm_length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "adjacent_to": self.adjacent_to.position.serialize(),
            "arm_length": self.arm_length,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        selected_cc = CC(**v["cc"])
        hexes = list(GS().map.get_neighbors_off(self.adjacent_to.position))
        for idx, _hex in enumerate(hexes):
            if _hex.position == selected_cc:
                return [
                    hexes[(idx + offset) % len(hexes)]
                    for offset in range(-self.arm_length, self.arm_length + 1)
                ]
        # TODO some sorta standardized error for this. just need actual validation
        #  general.
        raise ValueError("invalid response")


# TODO terrible name
@dataclasses.dataclass
class HexHexes(TargetProfile[list[Hex]]):
    centers: list[Hex]
    radius: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "centers": [_hex.position.serialize() for _hex in self.centers],
            "radius": self.radius,
        }

    def parse_response(self, v: Any) -> list[Hex]:
        return list(
            GS().map.get_hexes_within_range_off(self.centers[v["index"]], self.radius)
        )


@dataclasses.dataclass
class RadiatingLine(TargetProfile[list[Hex]]):
    from_hex: Hex
    to_hexes: list[Hex]
    length: int

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "from_hex": self.from_hex.position.serialize(),
            "to_hexes": [h.position.serialize() for h in self.to_hexes],
            "length": self.length,
        }

    def parse_response(self, v: Any) -> O:
        selected_cc = self.to_hexes[v["index"]].position
        difference = selected_cc - self.from_hex.position
        return [
            projected
            for i in range(self.length)
            if (projected := GS().map.hexes.get(selected_cc + difference * i))
        ]


class MovementException(Exception): ...


CCArg: TypeAlias = CC | Hex | Unit


# TODO reasonable and consistent utils interface for this disaster
class HexMap:
    def __init__(self, landscape: Landscape):
        # TODO all these should be private
        self.hexes = {
            position: Hex(
                position=position,
                terrain=hex_spec.terrain_type(),
                is_objective=hex_spec.is_objective,
                map=self,
            )
            for position, hex_spec in landscape.terrain_map.items()
        }
        for _hex in self.hexes.values():
            _hex.terrain.create_effects(_hex)
        self.unit_positions: bidict[Unit, Hex] = bidict()
        # TODO better plan for handling this
        self.last_known_positions: dict[Unit, Hex] = {}

    @property
    def units(self) -> list[Unit]:
        return list(self.unit_positions.keys())

    def units_controlled_by(self, player: Player) -> Iterator[Unit]:
        for unit in self.units:
            if unit.controller == player:
                yield unit

    def hex_off(self, unit: Unit) -> Hex:
        return self.unit_positions.get(unit) or self.last_known_positions[unit]

    def position_off(self, unit: Unit) -> CC:
        return self.hex_off(unit).position

    def _to_cc(self, value: CCArg) -> CC:
        if isinstance(value, Hex):
            return value.position
        if isinstance(value, Unit):
            return self.hex_off(value).position
        return value

    def _to_hex(self, value: CCArg) -> Hex:
        if isinstance(value, CC):
            return self.hexes[value]
        if isinstance(value, Unit):
            return self.hex_off(value)
        return value

    def move_unit_to(self, unit: Unit, to: CCArg) -> None:
        _hex = self._to_hex(to)
        if self.unit_positions.inverse.get(_hex) is not None:
            raise MovementException()
        self.unit_positions[unit] = _hex

    def remove_unit(self, unit: Unit) -> None:
        self.last_known_positions[unit] = self.unit_positions[unit]
        del self.unit_positions[unit]

    def unit_on(self, on: CCArg) -> Unit | None:
        return self.unit_positions.inverse.get(self._to_hex(on))

    def distance_between(self, from_: CCArg, to_: CCArg) -> int:
        return self._to_cc(from_).distance_to(self._to_cc(to_))

    def get_neighbors_off(self, off: CCArg) -> Iterator[Hex]:
        for neighbor_coordinate in self._to_cc(off).neighbors():
            if _hex := self.hexes.get(neighbor_coordinate):
                yield _hex

    def get_neighboring_units_off(
        self, off: CCArg, controlled_by: Player | None = None
    ) -> Iterator[Unit]:
        for _hex in self.get_neighbors_off(off):
            if unit := self.unit_positions.inverse.get(_hex):
                if controlled_by is None or controlled_by == unit.controller:
                    yield unit

    def get_hexes_within_range_off(self, off: CCArg, distance: int) -> Iterator[Hex]:
        for cc in hex_circle(distance, center=self._to_cc(off)):
            if cc in self.hexes:
                yield self.hexes[cc]

    def get_units_within_range_off(self, off: CCArg, distance: int) -> Iterator[Unit]:
        for _hex in self.get_hexes_within_range_off(off, distance):
            if unit := self.unit_positions.inverse.get(_hex):
                yield unit

    def serialize(self, context: SerializationContext) -> JSON:
        return {"hexes": [_hex.serialize(context) for _hex in self.hexes.values()]}


@dataclasses.dataclass
class ActiveUnitContext(Serializable):
    unit: Unit
    movement_points: int
    has_acted: bool = False
    should_stop: bool = False
    activated_facets: defaultdict[str, int] = dataclasses.field(
        default_factory=lambda: defaultdict(int)
    )
    locked_into: EffortFacet | None = None

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "unit": self.unit.serialize(context),
            "movement_points": self.movement_points,
        }


class GameState:
    instance: GameState | None = None

    def __init__(
        self,
        player_count: int,
        # interface_class: type[Interface],
        connection_class: type[Connection],
        landscape: Landscape,
    ):
        self.turn_order = TurnOrder(
            [Player(f"player {i+1}") for i in range(player_count)]
        )
        self.connections = {
            player: connection_class(player) for player in self.turn_order.players
        }
        # self.map = HexMap(settings.map_spec.generate_landscape())
        self.map = HexMap(landscape)
        self.active_unit_context: ActiveUnitContext | None = None
        self.activation_queued_units: set[Unit] = set()
        # self.points: dict[Player]
        self.target_points = 21
        self.round_counter = 0

        # TODO move to player
        # self._id_map = IDMap()
        self.id_maps: dict[Player, IDMap] = {
            player: IDMap() for player in self.turn_order.players
        }
        self.previous_hex_states: dict[Player, dict[CC, dict[str, Any]] | None] = {
            player: None for player in self.turn_order.players
        }

        self.vision_obstruction_map: dict[Player, dict[CC, VisionObstruction]] = {}
        self.vision_map: dict[Player, dict[CC, bool]] = {}

        # TODO for debugging
        self._event_log: list[str] = []
        ES.register_event_callback(EventLogger(self._event_log.append))

    def update_vision(self) -> None:
        unit_vision_map: dict[player, list[Unit]] = defaultdict(list)
        for unit in self.map.unit_positions.keys():
            for player in unit.provides_vision_for(None):
                unit_vision_map[player].append(unit)

        for player in self.turn_order.players:
            self.vision_obstruction_map[player] = {
                position: _hex.blocks_vision_for(player)
                for position, _hex in self.map.hexes.items()
            }

        for player in self.turn_order.players:
            self.vision_map[player] = {
                position: any(unit.can_see(_hex) for unit in unit_vision_map[player])
                for position, _hex in self.map.hexes.items()
            }

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        serialized_game_state = {
            "player": context.player.name,
            "players": [player.serialize() for player in self.turn_order.players],
            "round": self.round_counter,
            "map": self.map.serialize(context),
            "decision": decision_point.serialize(context) if decision_point else None,
            "active_unit_context": (
                self.active_unit_context.serialize(context)
                if self.active_unit_context
                else None
            ),
            # TODO for debugging
            "event_log": self._event_log,
        }
        # TODO yikes
        self.previous_hex_states[context.player] = {
            CC(**hex_values["cc"]): hex_values
            for hex_values in serialized_game_state["map"]["hexes"]
        }
        # TODO lmao
        context.id_map.prune()
        return serialized_game_state

    def make_decision(self, player: Player, decision_point: DecisionPoint[O]) -> O:
        for _player in self.turn_order.players:
            if _player != player:
                self.connections[_player].send(
                    self.serialize_for(
                        SerializationContext(
                            _player,
                            self.id_maps[_player],
                            self.previous_hex_states[_player],
                        ),
                        None,
                    )
                )
        response = self.connections[player].get_response(
            self.serialize_for(
                SerializationContext(
                    player, self.id_maps[player], self.previous_hex_states[player]
                ),
                decision_point,
            )
        )
        # TODO
        print("response in game state", response)
        return decision_point.parse_response(response)


# TODO
def GS() -> GameState:
    return GameState.instance
