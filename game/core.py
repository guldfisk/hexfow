from __future__ import annotations

import contextlib
import dataclasses
import json
import re
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Self,
    Sequence,
    TypeAlias,
    TypeVar,
)

from bidict import bidict
from pydantic import BaseModel, ValidationError

from events.eventsystem import (
    EventResolution,
    Modifiable,
    ModifiableAttribute,
    modifiable,
)
from game.has_effects import HasEffectChildren, HasEffects
from game.identification import IDMap
from game.info.registered import Registered, UnknownIdentifierError, get_registered_meta
from game.map.coordinates import CC, Corner, CornerPosition, line_of_sight_obstructed
from game.map.geometry import hex_circle
from game.schemas import (
    DecisionResponseSchema,
    DecisionValidationError,
    DeployArmyDecisionPointSchema,
    EmptySchema,
    IndexSchema,
    PremoveSchema,
    SelectArmyDecisionPointSchema,
    SelectOptionAtHexDecisionPointSchema,
    SelectOptionDecisionPointSchema,
)
from game.values import (
    ControllerTargetOption,
    DamageType,
    Resistance,
    Size,
    StatusIntention,
    VisionObstruction,
)


G_Status = TypeVar("G_Status", bound="Status")
G_StatusSignature = TypeVar("G_StatusSignature", bound="StatusSignature")
G_decision_result = TypeVar("G_decision_result")
G_HasStatuses = TypeVar("G_HasStatuses", bound="HasStatuses")
G_EffortCost = TypeVar("G_EffortCost", bound="EffortCost")
G_AttackFacet = TypeVar("G_AttackFacet", bound="AttackFacet")

JSON: TypeAlias = Mapping[str, Any]


@dataclasses.dataclass
class SerializationContext:
    player: Player
    last_hex_states: dict[CC : dict[str, Any]] | None
    visible_unit_ids: set[str]
    visible_blueprint_ids: set[str]


class Serializable(ABC):
    @abstractmethod
    def serialize(self, context: SerializationContext) -> JSON: ...


class DecisionPoint(Serializable, Generic[G_decision_result]):
    response_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    def get_explanation(self) -> str: ...

    @abstractmethod
    def serialize_payload(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "explanation": self.get_explanation(),
            "type": self.__class__.__name__,
            "payload": self.serialize_payload(context),
        }

    @abstractmethod
    def parse_response_schema(self, v: BaseModel) -> G_decision_result: ...

    def parse_response(self, v: Mapping[str, Any]) -> G_decision_result:
        return self.parse_response_schema(self.response_schema.model_validate(v))


class TargetProfile(ABC, Generic[G_decision_result]):
    response_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"type": type(self).__name__, "values": self.serialize_values(context)}

    @abstractmethod
    def parse_response_schema(self, v: BaseModel) -> G_decision_result: ...

    def parse_response(self, v: Mapping[str, Any]) -> G_decision_result:
        return self.parse_response_schema(self.response_schema.model_validate(v))


class NoTarget(TargetProfile[None]):
    response_schema = EmptySchema

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}

    def parse_response_schema(self, v: EmptySchema) -> None:
        return None


@dataclasses.dataclass(kw_only=True)
class Option(ABC, Generic[G_decision_result]):
    target_profile: TargetProfile[G_decision_result]

    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "type": type(self).__name__,
            "values": self.serialize_values(context),
            "target_profile": self.target_profile.serialize(context),
        }


@dataclasses.dataclass
class OptionDecision(Generic[G_decision_result]):
    option: Option[G_decision_result]
    target: G_decision_result


@dataclasses.dataclass
class SelectOptionDecisionPoint(DecisionPoint[OptionDecision]):
    response_schema: ClassVar[type[BaseModel]] = SelectOptionDecisionPointSchema

    options: list[Option]
    explanation: str

    def get_explanation(self) -> str:
        return self.explanation

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {"options": [option.serialize(context) for option in self.options]}

    def parse_response_schema(
        self, v: SelectOptionDecisionPointSchema
    ) -> OptionDecision:
        if v.index >= len(self.options):
            raise DecisionValidationError("invalid index")
        option = self.options[v.index]
        return OptionDecision(
            option=option,
            target=option.target_profile.parse_response(v.target),
        )


@dataclasses.dataclass
class SelectArmyDecisionPoint(DecisionPoint[list[tuple["UnitBlueprint", "Hex"]]]):
    response_schema: ClassVar[type[BaseModel]] = SelectArmyDecisionPointSchema

    deployment_zone: list[Hex]
    deployment_spec: DeploymentSpec

    def get_explanation(self) -> str:
        return "Select army of max {} units and max {} points".format(
            self.deployment_spec.max_army_units, self.deployment_spec.max_army_points
        )

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {
            "deployment_spec": self.deployment_spec.serialize(),
            "deployment_zone": [
                hex_.position.serialize() for hex_ in self.deployment_zone
            ],
        }

    def parse_response_schema(
        self, v: SelectArmyDecisionPointSchema
    ) -> list["UnitBlueprint"]:
        try:
            units = [
                UnitBlueprint.get_class(blueprint_name) for blueprint_name in v.units
            ]
        except UnknownIdentifierError as e:
            raise DecisionValidationError(f"unknown blueprint {e.identifier}")

        if len(units) != len(set(units)):
            raise DecisionValidationError("duplicat units not allowed")

        if (
            len(units) > self.deployment_spec.max_army_units
            or sum(u.price for u in units) > self.deployment_spec.max_army_points
        ):
            raise DecisionValidationError("price exceeded")

        return units


@dataclasses.dataclass
class DeployArmyDecisionPoint(DecisionPoint[list[tuple["UnitBlueprint", "Hex"]]]):
    response_schema: ClassVar[type[BaseModel]] = DeployArmyDecisionPointSchema

    units: list[UnitBlueprint]
    deployment_spec: DeploymentSpec
    deployment_zone: list[Hex]

    def get_explanation(self) -> str:
        return "Deploy army of max {} units and max {} points".format(
            self.deployment_spec.max_deployment_units,
            self.deployment_spec.max_deployment_points,
        )

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {
            "units": [unit.identifier for unit in self.units],
            "deployment_spec": self.deployment_spec.serialize(),
            "deployment_zone": [
                hex_.position.serialize() for hex_ in self.deployment_zone
            ],
        }

    def parse_response_schema(
        self, v: DeployArmyDecisionPointSchema
    ) -> list[tuple["UnitBlueprint", "Hex"]]:
        try:
            deployments = [
                (UnitBlueprint.get_class(blueprint_name), GS.map.hexes[CC(cc.r, cc.h)])
                for blueprint_name, cc in v.deployments
            ]
        except UnknownIdentifierError as e:
            raise DecisionValidationError(f"unknown blueprint {e.identifier}")
        except IndexError:
            raise DecisionValidationError("invalid position")

        if len(deployments) != len({u for u, _ in deployments}):
            raise DecisionValidationError("duplicat units not allowed")

        if (
            len(deployments) > self.deployment_spec.max_deployment_units
            or sum(u.price for u, _ in deployments)
            > self.deployment_spec.max_deployment_points
        ):
            raise DecisionValidationError("price exceeded")

        return deployments


@dataclasses.dataclass
class SelectOptionAtHexDecisionPoint(DecisionPoint[str]):
    response_schema: ClassVar[type[BaseModel]] = SelectOptionAtHexDecisionPointSchema

    hex_: Hex
    options: list[str]
    explanation: str

    def get_explanation(self) -> str:
        return self.explanation

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {"hex": self.hex_.position.serialize(), "options": self.options}

    def parse_response_schema(self, v: SelectOptionAtHexDecisionPointSchema) -> str:
        if v.index >= len(self.options):
            raise DecisionValidationError("invalid index")
        return self.options[v.index]


class MoveOption(Option[G_decision_result]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


@dataclasses.dataclass
class EffortOption(Option[G_decision_result]):
    facet: EffortFacet

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"facet": self.facet.serialize_type()}


@dataclasses.dataclass
class ActivateUnitOption(Option[G_decision_result]):
    actions_previews: dict[Unit, list[Option]]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "actions_preview": {
                context.player.id_map.get_id_for(unit): [
                    option.serialize(context) for option in options
                ]
                for unit, options in self.actions_previews.items()
            }
        }


class SkipOption(Option[None]):
    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}


class HasStatuses(HasEffects, Generic[G_Status, G_StatusSignature]):
    def __init__(self, parent: HasEffectChildren | None = None):
        super().__init__(parent=parent)
        self.statuses: list[G_Status] = []

    def add_status(self, signature: G_StatusSignature) -> G_Status | None:
        if not (signature := signature.status_type.pre_merge(signature, self)):
            return None
        for existing_status in self.statuses:
            if type(existing_status) is signature.status_type:
                if (
                    merge_result := existing_status.merge(signature)
                ) == MergeResult.REJECTED:
                    return None
                if merge_result == MergeResult.MERGED:
                    return existing_status

        status = signature.realize(self)
        self.statuses.append(status)
        status.create_effects()
        status.on_apply()
        return status

    def get_statuses(self, status_type: type[G_Status]) -> list[G_Status]:
        return [status for status in self.statuses if isinstance(status, status_type)]

    def has_status(self, status_type: type[G_Status] | str) -> bool:
        status_type = (
            Status.registry[status_type]
            if isinstance(status_type, str)
            else status_type
        )
        return any(isinstance(status, status_type) for status in self.statuses)

    def remove_status(self, status: G_Status) -> None:
        try:
            self.statuses.remove(status)
        except ValueError:
            pass
        status.deregister()


class Facet(HasEffects["Unit"], Registered, ABC, metaclass=get_registered_meta()):
    registry: ClassVar[dict[str, Facet]]

    # TODO common interface?
    def create_effects(self) -> None: ...

    # TODO lmao
    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
            "related_units": cls.related_units,
        }


class EffortCost(ABC):
    @abstractmethod
    def can_be_paid(self, context: ActiveUnitContext) -> bool:
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

    def get(self, cost_type: type[G_EffortCost]) -> G_EffortCost | None:
        return self.costs.get(cost_type)

    @abstractmethod
    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return all(cost.can_be_paid(context) for cost in self.costs.values())

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

    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return not context.has_acted or self.amount <= context.movement_points

    def pay(self, context: ActiveUnitContext) -> None:
        context.movement_points -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class ExclusiveCost(EffortCost):
    def can_be_paid(self, context: ActiveUnitContext) -> bool:
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

    def can_be_paid(self, context: ActiveUnitContext) -> bool:
        return self.amount <= context.unit.energy

    def pay(self, context: ActiveUnitContext) -> None:
        context.unit.energy -= self.amount

    @classmethod
    def merge(cls, instances: list[Self]) -> Self:
        return cls(amount=sum(cost.amount for cost in instances))

    def serialize_values(self) -> dict[str, Any]:
        return {"amount": self.amount}


class EffortFacet(Facet, ABC):
    cost: ClassVar[EffortCostSet | EffortCost | None] = None
    combinable: ClassVar[bool] = False
    max_activations: int | None = 1

    # TODO how does overriding work with modifiable? also, can it be abstract?
    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]: ...

    @classmethod
    def get_cost_set(cls) -> EffortCostSet:
        if isinstance(cls.cost, EffortCost):
            return EffortCostSet([cls.cost])
        return cls.cost or EffortCostSet()

    # TODO should prob be modifiable. prob need some way to lock in costs for effort
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
            and self.get_cost().can_be_paid(context)
            and self.get_legal_targets(context)
        )

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            **super().serialize_type(),
            "cost": cls.get_cost_set().serialize(),
            "combineable": cls.combinable,
            "max_activations": cls.max_activations,
        }


class AttackFacet(EffortFacet, ABC):
    damage_type: ClassVar[DamageType] = DamageType.PHYSICAL
    damage: ClassVar[int]
    ap: ClassVar[int] = 0
    benefits_from_attack_power: ClassVar[bool] = True

    def get_damage_modifier_against(self, unit: Unit) -> int | None: ...

    def get_attack_power_modifier(self) -> int:
        return (
            self.parent.attack_power.g()
            if self.benefits_from_attack_power
            else min(self.parent.attack_power.g(), 0)
        )

    @modifiable
    def get_damage_signature_against(self, unit: Unit) -> DamageSignature:
        return DamageSignature(
            max(
                self.damage
                + (self.get_damage_modifier_against(unit) or 0)
                + self.get_attack_power_modifier(),
                0,
            ),
            self,
            type=self.damage_type,
            ap=self.ap,
        )

    def resolve_pre_damage_effects(self, defender: Unit) -> None: ...
    def resolve_post_damage_effects(
        self, defender: Unit, result: EventResolution
    ) -> None: ...

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            **super().serialize_type(),
            "damage": cls.damage,
            "ap": cls.ap,
            "benefits_from_attack_power": cls.benefits_from_attack_power,
        }


class MeleeAttackFacet(AttackFacet, ABC):
    category = "melee_attack"

    # TODO wrap in get_legal_targets to align with activated ability
    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]:
        return [
            unit
            for unit in GS.map.get_neighboring_units_off(self.parent)
            if unit.controller != self.parent.controller
            and unit.is_visible_to(self.parent.controller)
            and unit.can_be_attacked_by(self)
        ]


# TODO where should logic for these be?
def is_vision_obstructed_for_unit_at(unit: Unit, cc: CC) -> bool:
    match GS.vision_obstruction_map[unit.controller].get(cc):
        case VisionObstruction.FULL:
            return True
        case VisionObstruction.FOR_LOW_GROUND:
            return not GS.map.hex_off(unit).terrain.is_high_ground
        case _:
            return False


def line_of_sight_obstructed_for_unit(unit: Unit, line_from: CC, line_to: CC) -> bool:
    return line_of_sight_obstructed(
        line_from, line_to, lambda cc: is_vision_obstructed_for_unit_at(unit, cc)
    )


class RangedAttackFacet(AttackFacet, ABC):
    category = "ranged_attack"
    range: ClassVar[int]

    @modifiable
    def get_legal_targets(self, context: ActiveUnitContext) -> list[Unit]:
        return find_units_within_range(
            self.parent,
            self.range,
            with_controller=ControllerTargetOption.ENEMY,
            additional_filter=lambda u: u.can_be_attacked_by(self),
        )

    @classmethod
    def serialize_type(cls) -> JSON:
        return {**super().serialize_type(), "range": cls.range}


class ActivatedAbilityFacet(EffortFacet, Generic[G_decision_result], ABC):
    category = "activated_ability"
    hidden_target: ClassVar[bool] = False

    @classmethod
    def get_target_explanation(cls) -> str | None: ...

    @abstractmethod
    def get_target_profile(self) -> TargetProfile[G_decision_result] | None: ...

    @abstractmethod
    def perform(self, target: G_decision_result) -> None: ...

    @modifiable
    def can_be_activated(self, context: ActiveUnitContext) -> bool:
        return (
            (
                self.max_activations is None
                or context.activated_facets[self.__class__.__name__]
                < self.max_activations
            )
            and self.get_cost().can_be_paid(context)
            and self.get_target_profile() is not None
        )

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            **super().serialize_type(),
            "target_explanation": cls.get_target_explanation(),
            "hidden_target": cls.hidden_target,
        }


class StaticAbilityFacet(Facet, ABC):
    category = "static_ability"


class MergeResult(Enum):
    MERGED = 0
    REJECTED = 1
    STACK = 2


class Status(
    Registered,
    HasEffects[G_HasStatuses],
    Serializable,
    Generic[G_HasStatuses, G_StatusSignature],
    ABC,
    metaclass=get_registered_meta(),
):
    registry: ClassVar[dict[str, Status]]
    # TODO should prob be modifiable, and also something something dispel costs.
    dispellable: ClassVar[bool] = True

    def __init__(
        self,
        *,
        source: Source = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: G_HasStatuses | None,
    ):
        super().__init__(parent=parent)
        self.source = source
        self.duration = duration
        self.stacks = stacks

        self.links: list[StatusLink] = []

    @property
    def controller(self) -> Player | None:
        return get_source_controller(self.source)

    @classmethod
    def get_stacking_info(cls) -> str:
        return "unstackable"

    @classmethod
    def pre_merge(
        cls, signature: G_StatusSignature, to: G_HasStatuses
    ) -> G_StatusSignature | None:
        return signature

    def merge(self, signature: G_StatusSignature) -> MergeResult:
        return MergeResult.REJECTED

    def is_hidden_for(self, player: Player) -> bool:
        return False

    def create_effects(self) -> None: ...

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
            "related_units": cls.related_units,
            "stacking_info": cls.get_stacking_info(),
            "dispellable": cls.dispellable,
        }

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "type": self.identifier,
            "duration": self.duration,
            "stacks": self.stacks,
        }

    def on_apply(self) -> None: ...

    def on_expires(self) -> None: ...

    def on_fully_decremented(self) -> None: ...

    def on_remove(self) -> None: ...

    def remove(self) -> None:
        self.on_remove()
        for link in list(self.links):
            link.remove_status(self)
        # TODO is this all?
        self.parent.remove_status(self)

    def decrement_duration(self) -> None:
        if self.duration is None:
            return
        self.duration -= 1
        if self.duration <= 0:
            self.on_expires()
            self.remove()

    def decrement_stacks(self, n: int = 1) -> None:
        self.stacks = max(self.stacks - n, 0)
        if not self.stacks:
            self.on_fully_decremented()
            self.remove()


class StatusLink(HasEffects, Generic[G_Status], ABC):
    def __init__(self, statuses: list[G_Status]):
        super().__init__()

        self.statuses: list[G_Status] = []

        for status in statuses:
            self.add_status(status)

        self.create_effects()

    def on_remove(self) -> None: ...

    def remove(self) -> None:
        self.on_remove()
        for status in list(self.statuses):
            self.remove_status(status)
        self.statuses = []
        self.deregister()

    def add_status(self, status: G_Status) -> None:
        self.statuses.append(status)
        status.links.append(self)

    def on_status_removed(self, status: G_Status) -> None: ...

    def remove_status(self, status: G_Status) -> None:
        if status in self.statuses:
            self.statuses.remove(status)
            self.on_status_removed(status)
            if not self.statuses:
                self.remove()

    def create_effects(self) -> None: ...


class StatusLinkMixin(ABC):
    statuses: list[G_Status] = []
    remove: Callable[[], None]

    @abstractmethod
    def on_remove(self) -> None: ...
    @abstractmethod
    def on_status_removed(self, status: G_Status) -> None: ...


class LooseGroupMixin(StatusLinkMixin):
    def on_remove(self) -> None:
        for status in list(self.statuses):
            status.remove()

    def on_status_removed(self, status: G_Status) -> None: ...


class CohesiveGroupMixin(StatusLinkMixin):
    def on_remove(self) -> None:
        for status in list(self.statuses):
            status.remove()

    def on_status_removed(self, status: G_Status) -> None:
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
        facets: list[type[Facet]] | None = None,
        price: int | None,
        max_count: int = 1,
        flavor: str | None = None,
        identifier: str | None = None,
    ):
        self.name = name
        self.health = health
        self.speed = speed
        self.sight = sight
        self.armor = armor
        self.energy = energy
        self.starting_energy = starting_energy
        self.size = size
        self.facets = facets or []

        self.flavor = flavor

        self.identifier = identifier or re.sub(
            "_+", "_", re.sub("[^a-z]", "_", self.name.lower())
        )
        self.registry[self.identifier] = self

        self.price = price
        self.max_count = max_count

    # TODO nice name lol
    @classmethod
    def get_class(cls, identifier: str) -> Self:
        try:
            return cls.registry[identifier]
        except KeyError:
            raise UnknownIdentifierError(cls, identifier)

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"

    def serialize(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "health": self.health,
            "speed": self.speed,
            "sight": self.sight,
            "armor": self.armor,
            "energy": self.energy,
            "size": self.size.value,
            "facets": [facet.identifier for facet in self.facets],
            "price": self.price,
            "max_count": self.max_count,
            "flavor": self.flavor,
        }


class Unit(HasStatuses["UnitStatus", "UnitStatusSignature"], Modifiable, Serializable):
    speed: ModifiableAttribute[None, int]
    sight: ModifiableAttribute[None, int]
    max_health: ModifiableAttribute[None, int]
    armor: ModifiableAttribute[None, int]
    max_energy: ModifiableAttribute[None, int]
    energy_regen: ModifiableAttribute[None, int]
    size: ModifiableAttribute[None, Size]
    attack_power: ModifiableAttribute[None, int]
    is_broken: ModifiableAttribute[None, bool]

    statuses: list[UnitStatus]

    def __init__(
        self,
        controller: Player,
        blueprint: UnitBlueprint,
        exhausted: bool = False,
        spawned: bool = False,
    ):
        super().__init__()

        self.controller = controller
        self.blueprint = blueprint
        self.original_blueprint = blueprint

        self.is_spawned = spawned

        self.damage: int = 0
        self.last_damaged_by: Source = None

        self.energy_regen.set(1)
        self.energy: int = (
            blueprint.starting_energy
            if isinstance(blueprint.starting_energy, int)
            else blueprint.energy
        )
        self.attack_power.set(0)
        self.is_broken.set(False)
        self.exhausted = exhausted

        self.attacks: list[AttackFacet] = []
        self.activated_abilities: list[ActivatedAbilityFacet] = []
        self.static_abilities: list[StaticAbilityFacet] = []

        self.set_blueprint(blueprint)

    def set_blueprint(self, blueprint: UnitBlueprint) -> None:
        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.deregister()

        self.blueprint = blueprint

        self.max_health.set(blueprint.health)
        self.speed.set(blueprint.speed)
        self.sight.set(blueprint.sight)
        self.armor.set(blueprint.armor)
        self.max_energy.set(blueprint.energy)
        self.size.set(blueprint.size)

        self.attacks = [
            facet(self) for facet in blueprint.facets if issubclass(facet, AttackFacet)
        ]
        self.activated_abilities = [
            facet(self)
            for facet in blueprint.facets
            if issubclass(facet, ActivatedAbilityFacet)
        ]
        self.static_abilities = [
            facet(self)
            for facet in blueprint.facets
            if issubclass(facet, StaticAbilityFacet)
        ]

        for facet in self.attacks + self.activated_abilities + self.static_abilities:
            facet.create_effects()

    def get_primary_attack(
        self, of_type: type[G_AttackFacet] | None = None
    ) -> G_AttackFacet | None:
        for attack in self.attacks:
            if of_type is None or isinstance(attack, of_type):
                return attack
        return None

    @property
    def ready(self) -> bool:
        return not self.exhausted

    @modifiable
    def is_aquatic(self, _: None) -> bool:
        return False

    @modifiable
    def get_resistance_against(self, signature: DamageSignature) -> Resistance:
        return Resistance.NONE

    @modifiable
    def can_capture_objectives_on(self, space: Hex) -> bool:
        return True

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return GS.map.hex_off(self).get_terrain_protection_for(request)

    def suffer_damage(self, signature: DamageSignature) -> int:
        damage = (
            signature.amount
            if signature.lethal
            else min(signature.amount, self.health - 1)
        )
        self.damage += damage
        self.last_damaged_by = signature.source
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
        distance = space.map.distance_between(self, space)
        if distance == 0:
            return True
        if distance > self.sight.g():
            return False
        if distance == 1:
            return True
        return not line_of_sight_obstructed_for_unit(
            self, space.map.position_off(self), space.position
        )

    @modifiable
    def is_hidden_for(self, player: Player) -> bool:
        return False

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return (
            player == self.controller or GS.map.hex_off(self).is_visible_to(player)
        ) and not self.is_hidden_for(player)

    @modifiable
    def get_potential_move_destinations(self, _: None) -> list[Hex]:
        return [
            _hex
            for _hex in GS.map.get_neighbors_off(self)
            if not _hex.is_visible_to(self.controller)
            or _hex.can_move_into(self)
            or (
                (unit := GS.map.unit_on(_hex))
                and unit.controller != self.controller
                and not _hex.is_occupied_for(self)
                and _hex.is_passable_to(self)
                and unit.is_hidden_for(self.controller)
            )
        ]

    @modifiable
    def get_legal_options(self, context: ActiveUnitContext) -> list[Option]:
        options = []
        if context.movement_points > 0:
            if moveable_hexes := [
                h
                for h in self.get_potential_move_destinations(None)
                if not context.has_acted
                or h.get_move_in_cost_for(self) <= context.movement_points
            ]:
                options.append(MoveOption(target_profile=OneOfHexes(moveable_hexes)))
        if context.movement_points >= 0:
            for facet in self.attacks:
                if isinstance(
                    facet, (MeleeAttackFacet, RangedAttackFacet)
                ) and facet.can_be_activated(context):
                    options.append(
                        EffortOption(
                            facet,
                            target_profile=OneOfUnits(facet.get_legal_targets(context)),
                        )
                    )
            for facet in self.activated_abilities:
                if facet.can_be_activated(context):
                    options.append(
                        EffortOption(facet, target_profile=facet.get_target_profile())
                    )
        if not context.has_acted or options:
            options.append(SkipOption(target_profile=NoTarget()))
        return options

    # TODO alive?
    def on_map(self) -> bool:
        return self in GS.map.unit_positions

    @property
    def health(self) -> int:
        return self.max_health.g() - self.damage

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "id": context.player.id_map.get_id_for(self),
            "blueprint": self.blueprint.identifier,
            "controller": self.controller.name,
            "max_health": self.max_health.g(),
            "damage": self.damage,
            "speed": self.speed.g(),
            "sight": self.sight.g(),
            "max_energy": self.max_energy.g(),
            "energy": self.energy,
            "size": self.size.g().value,
            "armor": self.armor.g(),
            "attack_power": self.attack_power.g(),
            "exhausted": self.exhausted,
            "is_ghost": False,
            "statuses": [
                status.serialize(context)
                for status in self.statuses
                if not status.is_hidden_for(context.player)
            ],
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.blueprint.name}, {self.controller.name}, {id(self)})"


class UnitStatus(Status[Unit, "UnitStatusSignature"], ABC):
    category: ClassVar[str] = "unit"
    default_intention: ClassVar[StatusIntention | None] = None

    def __init__(
        self,
        *,
        source: Source = None,
        duration: int | None = None,
        stacks: int | None = None,
        parent: Unit,
        intention: StatusIntention,
    ):
        super().__init__(source=source, duration=duration, stacks=stacks, parent=parent)
        self.intention = intention

    @classmethod
    def get(cls, identifier: str) -> type[UnitStatus]:
        return cls.registry[identifier]

    def serialize(self, context: SerializationContext) -> JSON:
        return {**super().serialize(context), "intention": self.intention.value}


@dataclasses.dataclass
class StatusSignature(Generic[G_HasStatuses, G_Status]):
    status_type: type[G_Status]
    source: Source
    stacks: int | None = None
    duration: int | None = None

    @property
    def controller(self) -> Player | None:
        return get_source_controller(self.source)

    @abstractmethod
    def realize(self, for_: G_HasStatuses) -> G_Status: ...

    def branch(self, **kwargs) -> Self:
        return self.__class__(
            **(
                {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
                | kwargs
            )
        )


@dataclasses.dataclass
class UnitStatusSignature(StatusSignature[Unit, UnitStatus]):
    intention: StatusIntention | None = None

    def get_intention(self, unit: Unit) -> StatusIntention:
        return (
            self.intention
            or self.status_type.default_intention
            or (
                (
                    StatusIntention.BUFF
                    if unit.controller == get_source_controller(self.source)
                    else StatusIntention.DEBUFF
                )
                if self.source
                else StatusIntention.NEUTRAL
            )
        )

    def realize(self, unit: Unit) -> UnitStatus:
        return self.status_type(
            source=self.source,
            duration=self.duration,
            stacks=self.stacks,
            parent=unit,
            intention=self.get_intention(unit),
        )


@dataclasses.dataclass
class OneOfUnits(TargetProfile[Unit]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    units: list[Unit]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {
            "units": [
                {"id": context.player.id_map.get_id_for(unit)} for unit in self.units
            ]
        }

    def parse_response_schema(self, v: IndexSchema) -> Unit:
        try:
            return self.units[v.index]
        except IndexError:
            raise DecisionValidationError("invalid index")


class StatusMixin:
    controller: Player
    source: Source
    duration: int | None
    stacks: int | None

    @classmethod
    @abstractmethod
    def get_stacking_info(cls) -> str: ...

    @abstractmethod
    def merge(self, signature: StatusSignature) -> MergeResult: ...


def refresh_duration(
    existing_status: Status | StatusMixin, signature: StatusSignature
) -> MergeResult:
    if (
        signature.duration is None
        or existing_status.duration is None
        or (signature.duration > existing_status.duration)
    ):
        existing_status.duration = signature.duration
        return MergeResult.MERGED
    return MergeResult.REJECTED


class RefreshableMixin(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        return refresh_duration(self, signature)


class LowestRefreshableMixin(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "lowest refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        if self.duration is None or (
            signature.duration is not None and signature.duration < self.duration
        ):
            self.duration = signature.duration
            return MergeResult.MERGED
        return MergeResult.REJECTED


class StackableMixin(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "stackable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        self.stacks += signature.stacks
        return MergeResult.MERGED


class StackableRefreshableMixin(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "stackable, refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        refresh_duration(self, signature)
        self.stacks += signature.stacks
        return MergeResult.MERGED


class HighestStackableRefreshableMixin(StackableMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "highest stackable, refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        refresh_result = refresh_duration(self, signature)
        if signature.stacks > self.stacks:
            self.stacks = signature.stacks
            return MergeResult.MERGED
        return refresh_result


class LowestStackableRefreshableMixin(StackableMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "lowest stackable, refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        refresh_result = refresh_duration(self, signature)
        if signature.stacks < self.stacks:
            self.stacks = signature.stacks
            return MergeResult.MERGED
        return refresh_result


class PerPlayerRefreshable(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "per-player - refreshable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        if signature.controller == self.controller:
            return refresh_duration(self, signature)
        return MergeResult.STACK


class PerPlayerUnstackable(StatusMixin):
    @classmethod
    def get_stacking_info(cls) -> str:
        return "per-player - unstackable"

    def merge(self, signature: StatusSignature) -> MergeResult:
        if signature.controller == self.controller:
            return MergeResult.REJECTED
        return MergeResult.STACK


@dataclasses.dataclass
class HexSpec:
    terrain_type: type[Terrain]
    is_objective: bool
    deployment_zone_of: int | None = None
    statuses: list[HexStatusSignature] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Landscape:
    terrain_map: Mapping[CC, HexSpec]


@dataclasses.dataclass
class DeploymentSpec:
    max_army_units: int
    max_army_points: int
    max_deployment_units: int
    max_deployment_points: int

    def serialize(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Scenario:
    landscape: Landscape
    units: list[Mapping[CC, UnitBlueprint]]
    deployment_spec: DeploymentSpec
    to_points: int


@dataclasses.dataclass
class TerrainProtectionRequest:
    unit: Unit
    damage_signature: DamageSignature


class Terrain(HasEffects, Registered, ABC, metaclass=get_registered_meta()):
    registry: dict[str, type[Terrain]]
    is_water: ClassVar[bool] = False
    blocks_vision: ClassVar[bool] = False
    is_high_ground: ClassVar[bool] = False

    def create_effects(self, space: Hex) -> None: ...

    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return 0

    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return 0

    @classmethod
    def serialize_type(cls) -> JSON:
        return {
            "identifier": cls.identifier,
            "name": cls.name,
            "description": cls.description,
            "related_statuses": cls.related_statuses,
            "is_water": cls.is_water,
            "is_high_ground": cls.is_high_ground,
            "blocks_vision": cls.blocks_vision,
        }


class Hex(Modifiable, HasStatuses["HexStatus", "HexStatusSignature"], Serializable):
    def __init__(
        self, position: CC, terrain: Terrain, is_objective: bool, map_: HexMap
    ):
        super().__init__()
        self.position = position
        self.terrain = terrain
        self.is_objective = is_objective

        self.original_terrain_type = type(terrain)

        self.captured_by: Player | None = None
        # TODO name?
        self.map = map_

    @modifiable
    def is_passable_to(self, unit: Unit) -> bool:
        if self.terrain.is_water:
            return unit.is_aquatic(None)
        return True

    @modifiable
    def is_occupied_for(self, unit: Unit) -> bool:
        # TODO should prob be inverted?
        return not self.map.unit_on(self)

    @modifiable
    def can_move_into(self, unit: Unit) -> bool:
        return self.is_occupied_for(unit) and self.is_passable_to(unit)

    @modifiable
    def get_move_in_cost_for(self, unit: Unit) -> int:
        # if (
        #     self.terrain.is_high_ground
        #     and not GS.map.hex_off(unit).terrain.is_high_ground
        # ):
        #     return 2
        return 1

    @modifiable
    def get_move_in_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_in_penalty_for(unit)

    @modifiable
    def get_move_out_penalty_for(self, unit: Unit) -> int:
        return self.terrain.get_move_out_penalty_for(unit)

    @modifiable
    def blocks_vision_for(self, player: Player) -> VisionObstruction:
        if self.terrain.blocks_vision:
            if self.terrain.is_high_ground:
                return VisionObstruction.FULL
            return VisionObstruction.FOR_LOW_GROUND
        if (unit := self.map.unit_on(self)) and unit.blocks_vision_for(player):
            if self.terrain.is_high_ground:
                return VisionObstruction.FULL
            return VisionObstruction.FOR_LOW_GROUND
        if self.terrain.is_high_ground:
            return VisionObstruction.FOR_LOW_GROUND
        return VisionObstruction.NONE

    @modifiable
    def is_visible_to(self, player: Player) -> bool:
        return GS.vision_map[player][self.position]

    @modifiable
    def get_terrain_protection_for(self, request: TerrainProtectionRequest) -> int:
        return self.terrain.get_terrain_protection_for(request) + (
            1
            if request.damage_signature.type == DamageType.PHYSICAL
            and isinstance(request.damage_signature.source, Facet)
            and GS.map.hex_off(request.unit).terrain.is_high_ground
            and not GS.map.hex_off(
                request.damage_signature.source.parent
            ).terrain.is_high_ground
            else 0
        )

    def serialize(self, context: SerializationContext) -> JSON:
        old_hex = (context.last_hex_states or {}).get(self.position)
        return {
            "cc": self.position.serialize(),
            "is_objective": self.is_objective,
            **(
                {
                    "visible": True,
                    "last_visible_round": GS.round_counter,
                    "terrain": self.terrain.identifier,
                    "captured_by": self.captured_by.name if self.captured_by else None,
                    "unit": (
                        unit.serialize(context)
                        if (unit := self.map.unit_on(self))
                        and unit.is_visible_to(context.player)
                        else (
                            old_hex["unit"] | {"is_ghost": True}
                            if old_hex
                            and old_hex["unit"]
                            and old_hex["unit"]["blueprint"]
                            not in context.visible_blueprint_ids
                            and old_hex["unit"]["id"] not in context.visible_unit_ids
                            else None
                        )
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
                        "terrain": old_hex["terrain"],
                        "captured_by": old_hex["captured_by"],
                        "unit": (
                            old_hex["unit"] | {"is_ghost": True}
                            if old_hex["unit"]
                            and old_hex["unit"]["blueprint"]
                            not in context.visible_blueprint_ids
                            and old_hex["unit"]["id"] not in context.visible_unit_ids
                            else None
                        ),
                        "statuses": old_hex["statuses"],
                    }
                    if old_hex
                    else {
                        "visible": False,
                        "last_visible_round": None,
                        "terrain": self.original_terrain_type.identifier,
                        "captured_by": None,
                        "unit": None,
                        "statuses": [],
                    }
                )
            ),
        }

    def __repr__(self):
        return f"{type(self).__name__}({self.position.r}, {self.position.h})"


Source: TypeAlias = Facet | Status | None


def get_source_controller(source: Source) -> Player | None:
    return (
        (source.parent.controller if isinstance(source, Facet) else source.controller)
        if source
        else None
    )


def get_source_unit(source: Source) -> Unit | None:
    return source.parent if isinstance(source, Facet) else None


@dataclasses.dataclass
class DamageSignature:
    amount: int
    source: Source
    type: DamageType = DamageType.ABILITY
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

    def get_unit_source(self) -> Unit | None:
        return get_source_unit(self.source)


class HexStatus(Status[Hex, "HexStatusSignature"], ABC):
    category: ClassVar[str] = "hex"

    # TODO obsolete?
    @classmethod
    def get(cls, identifier: str) -> type[HexStatus]:
        return cls.registry[identifier]


@dataclasses.dataclass
class HexStatusSignature(StatusSignature[Hex, HexStatus]):
    def realize(self, for_: Hex) -> HexStatus:
        return self.status_type(
            source=self.source,
            duration=self.duration,
            stacks=self.stacks,
            parent=for_,
        )


class HexStatusLink(StatusLink[HexStatus], ABC): ...


class UnitStatusLink(StatusLink[UnitStatus], ABC): ...


@dataclasses.dataclass
class OneOfHexes(TargetProfile[Hex]):
    response_schema: ClassVar[type[BaseModel]] = IndexSchema

    hexes: list[Hex]

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {"options": [_hex.position.serialize() for _hex in self.hexes]}

    def parse_response_schema(self, v: IndexSchema) -> Hex:
        try:
            return self.hexes[v.index]
        except IndexError:
            raise DecisionValidationError("invalid index")


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
                map_=self,
            )
            for position, hex_spec in landscape.terrain_map.items()
        }
        for _hex in self.hexes.values():
            _hex.terrain.create_effects(_hex)
        self.unit_positions: bidict[Unit, Hex] = bidict()
        # TODO better plan for handling this?
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

    def move_unit_to(self, unit: Unit, to: CCArg) -> bool:
        _hex = self._to_hex(to)
        if self.unit_positions.inverse.get(_hex) is not None:
            return False
        self.unit_positions[unit] = _hex
        return True

    def remove_unit(self, unit: Unit) -> None:
        self.last_known_positions[unit] = self.unit_positions[unit]
        del self.unit_positions[unit]

    def unit_on(self, on: CCArg) -> Unit | None:
        return self.unit_positions.inverse.get(self._to_hex(on))

    def units_on(self, on: Iterable[CCArg]) -> Iterator[Unit]:
        for o in on:
            if unit := self.unit_on(o):
                yield unit

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

    def get_corners_within_range_off(
        self, off: CCArg, distance: int
    ) -> Iterator[Corner]:
        for cc in hex_circle(distance, center=(center := self._to_cc(off))):
            for position in CornerPosition:
                corner = Corner(cc, position)
                if all(
                    cc in self.hexes and cc.distance_to(center) <= distance
                    for cc in corner.get_adjacent_positions()
                ):
                    yield corner

    def get_units_within_range_off(self, off: CCArg, distance: int) -> Iterator[Unit]:
        for _hex in self.get_hexes_within_range_off(off, distance):
            if unit := self.unit_positions.inverse.get(_hex):
                yield unit

    def get_hexes_of_positions(self, positions: Iterable[CC]) -> Iterator[Hex]:
        for position in positions:
            if position in self.hexes:
                yield self.hexes[position]

    def serialize(self, context: SerializationContext) -> JSON:
        return {"hexes": [_hex.serialize(context) for _hex in self.hexes.values()]}


def find_units_within_range(
    from_unit: Unit,
    within_range: int,
    *,
    require_los: bool = True,
    with_controller: ControllerTargetOption | None = None,
    can_include_self: bool = True,
    additional_filter: Callable[[Unit], bool] | None = None,
) -> list[Unit]:
    return [
        unit
        for unit in GS.map.get_units_within_range_off(from_unit, within_range)
        if (
            not with_controller
            or (
                (unit.controller == from_unit.controller)
                if with_controller == ControllerTargetOption.ALLIED
                else (unit.controller != from_unit.controller)
            )
        )
        and unit.is_visible_to(from_unit.controller)
        and (
            not require_los
            or within_range <= 1
            or not line_of_sight_obstructed_for_unit(
                from_unit,
                GS.map.position_off(from_unit),
                GS.map.position_off(unit),
            )
        )
        and (can_include_self or unit != from_unit)
        and (not additional_filter or additional_filter(unit))
    ]


def find_hexs_within_range(
    from_unit: Unit,
    within_range: int,
    *,
    require_vision: bool = False,
    require_los: bool = True,
    require_empty: bool = True,
    can_include_self: bool = True,
    additional_filter: Callable[[Hex], bool] | None = None,
    vision_for_player: Player | None = None,
) -> list[Hex]:
    vision_for_player = vision_for_player or from_unit.controller
    return [
        _hex
        for _hex in GS.map.get_hexes_within_range_off(from_unit, within_range)
        if (not require_vision or _hex.is_visible_to(vision_for_player))
        and (
            not require_los
            or within_range <= 1
            or not line_of_sight_obstructed_for_unit(
                from_unit,
                GS.map.position_off(from_unit),
                _hex.position,
            )
        )
        and (
            not require_empty
            or (
                (unit := GS.map.unit_on(_hex)) is None
                or (not require_vision and not _hex.is_visible_to(vision_for_player))
                or unit.is_hidden_for(vision_for_player)
            )
        )
        and (can_include_self or GS.map.hex_off(from_unit) != _hex)
        and (not additional_filter or additional_filter(_hex))
    ]


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


@dataclasses.dataclass
class LogLine:
    elements: list[
        str
        | Unit
        | Hex
        | list[Hex | Unit | UnitBlueprint]
        | Facet
        | Status
        | Player
        | UnitBlueprint
    ]
    valid_for_players: set[Player] | None = None

    def is_visible_to(self, player: Player) -> bool:
        if self.valid_for_players and player not in self.valid_for_players:
            return False
        for element in self.elements:
            if isinstance(element, list) and not any(
                e.is_visible_to(player) if isinstance(e, (Unit, Hex)) else True
                for e in element
            ):
                return False
            if isinstance(element, Unit) and not element.is_visible_to(player):
                return False
            if isinstance(element, Hex) and not element.is_visible_to(player):
                return False
            if isinstance(element, Status) and element.is_hidden_for(player):
                return False
        return True

    @classmethod
    def _serialize_element(
        cls, element: str | Unit | Hex, player: Player
    ) -> dict[str, Any]:
        if isinstance(element, Unit):
            return {
                "type": "unit",
                "identifier": player.id_map.get_id_for(element),
                "blueprint": element.blueprint.identifier,
                "controller": element.controller.name,
                "cc": GS.map.position_off(element).serialize(),
            }
        if isinstance(element, Hex):
            return {"type": "hex", "cc": element.position.serialize()}
        if isinstance(element, Facet):
            return {"type": "facet", "identifier": element.identifier}
        if isinstance(element, Status):
            return {"type": "status", "identifier": element.identifier}
        if isinstance(element, list):
            return {
                "type": "list",
                "items": [
                    cls._serialize_element(e, player)
                    for e in element
                    if not (isinstance(e, (Unit, Hex)) and not e.is_visible_to(player))
                ],
            }
        if isinstance(element, Player):
            return {"type": "player", "name": element.name}
        if isinstance(element, UnitBlueprint):
            return {"type": "blueprint", "blueprint": element.identifier}
        return {"type": "string", "message": element}

    def serialize(self, player: Player) -> list[dict[str, Any]]:
        return [self._serialize_element(element, player) for element in self.elements]


class Player:
    def __init__(self, name: str):
        self.name = name

        self.points: int = 0
        self.id_map = IDMap()

        self.recently_witnessed_kills: set[Unit] = set()

    def witness_kill(self, unit: Unit) -> None:
        self.recently_witnessed_kills.add(unit)

    def clear_witnessed_kills(self) -> None:
        self.recently_witnessed_kills.clear()

    def serialize(self) -> dict[str, Any]:
        return {"name": self.name, "points": self.points}


class TurnOrder:
    def __init__(self, players: Sequence[Player]):
        self.original_order = players
        self._players = players
        self._active_player_index = 0

    @property
    def active_player(self) -> Player:
        return self._players[self._active_player_index]

    @property
    def all_players(self) -> list[Player]:
        return [
            self._players[(i + self._active_player_index) % len(self._players)]
            for i in range(len(self._players))
        ]

    def advance(self) -> Player:
        self._active_player_index = (self._active_player_index + 1) % len(self._players)
        return self.active_player

    def set_player_order(self, players: Sequence[Player]) -> None:
        self._players = players
        self._active_player_index = 0

    def __iter__(self) -> Iterator[Player]:
        yield from self.all_players


class Connection(ABC):
    def __init__(self, player: Player):
        self.player = player

        self._game_state_counter: int = 0
        self._premove: PremoveSchema | None = None
        self._waiting_for_decision: DecisionPoint | None = None

    def send_error(self, error_type: str, error_detail: Any = None) -> None:
        print("error from client", error_type, error_detail)
        self.send(
            {
                "message_type": "error",
                "error_type": error_type,
            }
            | ({"error_detail": error_detail} if error_detail is not None else {})
        )

    def validate_decision_message(self, v: Mapping[str, Any]) -> Any | None:
        try:
            response = DecisionResponseSchema.model_validate(v)
            if response.count != self._game_state_counter:
                self.send_error("invalid_response_count")
                return None
            result = self._waiting_for_decision.parse_response(response.payload)
        except ValidationError as e:
            self.send_error("invalid_decision", e.errors())
        except DecisionValidationError as e:
            self.send_error("invalid_decision", e.args[0])
        else:
            if response.premove:
                self._premove = response.premove
            return result

    @abstractmethod
    def send(self, values: Mapping[str, Any]) -> None: ...

    def make_game_state_frame(
        self, game_state: Mapping[str, Any], decision_point: DecisionPoint | None = None
    ) -> dict[str, Any]:
        return {
            "message_type": "game_state",
            "count": self._game_state_counter,
            "game_state": game_state,
        }

    def send_game_state(
        self, game_state: Mapping[str, Any], decision_point: DecisionPoint | None = None
    ) -> None:
        self._premove = None
        self._game_state_counter += 1
        self._waiting_for_decision = decision_point
        self.send(self.make_game_state_frame(game_state, decision_point))

    @abstractmethod
    def wait_for_response(self) -> G_decision_result: ...

    def get_response(
        self,
        game_state: Mapping[str, Any],
        decision_point: DecisionPoint[G_decision_result],
    ) -> G_decision_result:
        if (
            self._premove
            and isinstance(decision_point, SelectOptionDecisionPoint)
            and self._premove.for_options
            == json.loads(json.dumps(game_state["decision"]["payload"]["options"]))
        ):
            try:
                validated_premove = decision_point.parse_response(self._premove.payload)
            except ValidationError as e:
                self.send_error("invalid_decision", e.errors())
            except DecisionValidationError as e:
                self.send_error("invalid_decision", e.args[0])
            else:
                self._premove = None
                return validated_premove
        self.send_game_state(game_state, decision_point)
        return self.wait_for_response()


class GameState:
    instance: GameState | None = None

    def __init__(
        self,
        player_count: int,
        connection_factory: Callable[[Player], Connection],
        scenario: Scenario,
    ):
        # TODO handle names
        self.turn_order = TurnOrder(
            [Player(f"player {i + 1}") for i in range(player_count)]
        )
        self.connections = {
            player: connection_factory(player) for player in self.turn_order
        }
        self.map = HexMap(scenario.landscape)
        self.active_unit_context: ActiveUnitContext | None = None
        self.activation_queued_units: set[Unit] = set()
        self.target_points = scenario.to_points
        self.round_counter = 0

        self.previous_hex_states: dict[Player, dict[CC, dict[str, Any]] | None] = {
            player: None for player in self.turn_order
        }

        self.vision_obstruction_map: dict[Player, dict[CC, VisionObstruction]] = {}
        self.vision_map: dict[Player, dict[CC, bool]] = {}

        self._player_log_levels: dict[Player, int] = {
            player: 0 for player in self.turn_order
        }
        self._pending_player_logs: dict[
            Player, list[tuple[int, list[dict[str, Any]]]]
        ] = {player: [] for player in self.turn_order}
        self._player_logs: dict[Player, list[tuple[int, list[dict[str, Any]]]]] = {
            player: [] for player in self.turn_order
        }

    @contextlib.contextmanager
    def log(self, *line_options: LogLine) -> Iterator[None]:
        incremented_players = []
        for player in self.turn_order:
            for line in line_options:
                if line.is_visible_to(player):
                    incremented_players.append(player)
                    self._pending_player_logs[player].append(
                        (self._player_log_levels[player], line.serialize(player))
                    )
                    self._player_log_levels[player] += 1
                    break
        yield
        for player in incremented_players:
            self._player_log_levels[player] -= 1

    def update_vision(self) -> None:
        unit_vision_map: dict[player, list[Unit]] = defaultdict(list)
        for unit in self.map.unit_positions.keys():
            for player in unit.provides_vision_for(None):
                unit_vision_map[player].append(unit)

        for player in self.turn_order:
            self.vision_obstruction_map[player] = {
                position: _hex.blocks_vision_for(player)
                for position, _hex in self.map.hexes.items()
            }

        for player in self.turn_order:
            self.vision_map[player] = {
                position: (
                    (unit := self.map.unit_on(_hex)) and unit.controller == player
                )
                or any(unit.can_see(_hex) for unit in unit_vision_map[player])
                for position, _hex in self.map.hexes.items()
            }

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        new_logs = self._pending_player_logs[context.player]
        self._player_logs[context.player].extend(new_logs)
        self._pending_player_logs[context.player] = []
        serialized_game_state = {
            "player": context.player.name,
            "target_points": self.target_points,
            "players": [
                player.serialize() for player in self.turn_order.original_order
            ],
            "round": self.round_counter,
            "map": self.map.serialize(context),
            "decision": decision_point.serialize(context) if decision_point else None,
            "active_unit_context": (
                self.active_unit_context.serialize(context)
                if self.active_unit_context
                and self.active_unit_context.unit.is_visible_to(context.player)
                else None
            ),
            "logs": self._player_logs[context.player],
            "new_logs": new_logs,
        }
        # TODO yikes
        self.previous_hex_states[context.player] = {
            CC(**hex_values["cc"]): hex_values
            for hex_values in serialized_game_state["map"]["hexes"]
        }
        # TODO lmao
        context.player.id_map.prune()
        context.player.clear_witnessed_kills()
        return serialized_game_state

    def _get_context_for(self, player: Player) -> SerializationContext:
        visible_units = {
            unit for unit in self.map.units if unit.is_visible_to(player)
        } | player.recently_witnessed_kills
        return SerializationContext(
            player,
            self.previous_hex_states[player],
            visible_unit_ids={player.id_map.get_id_for(unit) for unit in visible_units},
            visible_blueprint_ids={
                unit.blueprint.identifier
                for unit in visible_units
                if unit.blueprint.price is not None and unit.controller != player
            },
        )

    def update_ghosts(self) -> None:
        for player in self.turn_order:
            self.serialize_for(self._get_context_for(player), None)

    def send_to_players(self) -> None:
        for _player in self.turn_order:
            self.connections[_player].send_game_state(
                self.serialize_for(self._get_context_for(_player), None), None
            )

    def make_decision(
        self, player: Player, decision_point: DecisionPoint[G_decision_result]
    ) -> G_decision_result:
        for _player in self.turn_order:
            if _player != player:
                self.connections[_player].send_game_state(
                    self.serialize_for(self._get_context_for(_player), None), None
                )
        # TODO very dumb we are specifying decision point twice.
        return self.connections[player].get_response(
            self.serialize_for(self._get_context_for(player), decision_point),
            decision_point,
        )

    def make_parallel_decision(
        self, decision_points: dict[Player, DecisionPoint[G_decision_result]]
    ) -> dict[Player, G_decision_result]:
        for player in self.turn_order:
            self.connections[player].send_game_state(
                self.serialize_for(
                    self._get_context_for(player), decision_points.get(player)
                ),
                decision_points.get(player),
            )
        return {
            player: self.connections[player].wait_for_response()
            for player in decision_points.keys()
        }


class ScopedGameState:
    # TODO protocol/interface?
    def __init__(self):
        self._store = threading.local()

    def bind(self, gs: GameState) -> None:
        self._store.value = gs

    @property
    def _gs(self) -> GameState:
        return self._store.value

    @property
    def turn_order(self) -> TurnOrder:
        return self._gs.turn_order

    @property
    def connections(self) -> dict[Player, Connection]:
        return self._gs.connections

    @property
    def map(self) -> HexMap:
        return self._gs.map

    @property
    def active_unit_context(self) -> ActiveUnitContext | None:
        return self._gs.active_unit_context

    @active_unit_context.setter
    def active_unit_context(self, v: ActiveUnitContext) -> None:
        self._gs.active_unit_context = v

    @property
    def activation_queued_units(self) -> set[Unit]:
        return self._gs.activation_queued_units

    @property
    def target_points(self) -> int:
        return self._gs.target_points

    @property
    def round_counter(self) -> int:
        return self._gs.round_counter

    @round_counter.setter
    def round_counter(self, v: int) -> None:
        self._gs.round_counter = v

    @property
    def previous_hex_states(self) -> dict[Player, dict[CC, dict[str, Any]]]:
        return self._gs.previous_hex_states

    @property
    def vision_obstruction_map(self) -> dict[Player, dict[CC, VisionObstruction]]:
        return self._gs.vision_obstruction_map

    @property
    def vision_map(self) -> dict[Player, dict[CC, bool]]:
        return self._gs.vision_map

    # TODO pretty dumb
    @contextlib.contextmanager
    def log(self, *line_options: LogLine) -> Iterator[None]:
        with self._gs.log(*line_options):
            yield None

    def update_vision(self) -> None:
        self._gs.update_vision()

    def serialize_for(
        self, context: SerializationContext, decision_point: DecisionPoint | None
    ) -> Mapping[str, Any]:
        return self._gs.serialize_for(context, decision_point)

    def update_ghosts(self) -> None:
        self._gs.update_ghosts()

    def send_to_players(self) -> None:
        self._gs.send_to_players()

    def make_decision(
        self, player: Player, decision_point: DecisionPoint[G_decision_result]
    ) -> G_decision_result:
        return self._gs.make_decision(player, decision_point)

    def make_parallel_decision(
        self, decision_points: dict[Player, DecisionPoint[G_decision_result]]
    ) -> dict[Player, G_decision_result]:
        return self._gs.make_parallel_decision(decision_points)


GS = ScopedGameState()
