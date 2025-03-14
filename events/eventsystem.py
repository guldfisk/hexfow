from __future__ import annotations

import dataclasses
import re
from abc import ABC, abstractmethod, ABCMeta
from collections import defaultdict
from typing import (
    TypeVar,
    ClassVar,
    MutableMapping,
    Self,
    Any,
    Generic,
    get_args,
    Iterator,
    Sequence,
)

from debug_utils import dp


T = TypeVar("T")
V = TypeVar("V")
C = TypeVar("C")


class TriggerLoopError(Exception): ...


# TODO need some way to handle ordering for stuff with the same priority.
#  Prob some sorta timestamp, but the issue is that most units will be spawned
#  simultaneously. Maybe update the timestamp when unit is activated, but that
#  an ugly partial solution only.


class EventSystem:
    MAX_TRIGGER_RECURSION: ClassVar[int] = 128

    def __init__(self):
        # TODO ordered set?
        self._effects: MutableMapping[str, MutableMapping[Any, list[Effect]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self._pending_triggers: list[tuple[TriggerEffect, Event]] = []

        self.history: list[Event] = []

        self._active_event: Event | None = None

        # The same replacement effect only gets to modify something a single time
        # within a subtree of events. This keeps track of that.
        self._exhausted_replacement_effects: set[ReplacementEffect] = set()
        # We keep track of results on events resolved directly as a result of
        # a replacement effect, so we can return them as the result of the original
        # replaced event.
        self._replacement_results: list[EventResolution] = []
        # To do that, we keep track of the current active replacement effect.
        self._active_replacement_effect: ReplacementEffect | None = None

        # The same attribute modifier can only modify the attribute once during
        # each attribute get.
        self._evaluated_attributes: set[tuple[object, ModifiableAttribute]] = set()

    def has_pending_triggers(self) -> bool:
        return bool(self._pending_triggers)

    def register_effect(self, effect: F) -> F:
        self._effects[effect.effect_type][effect.target].append(effect)
        return effect

    # TODO type
    def _get_effects(self, effect_type: type[F] | F, target: Any) -> list[F]:
        return self._effects[effect_type.effect_type][target]

    def deregister_effect(self, effect: F) -> F:
        self._effects[effect.effect_type][effect.target].remove(effect)
        return effect

    def determine_attribute(
        self, obj: object, attribute: ModifiableAttribute, value: V
    ) -> V:
        for attribute_modifier in sorted(
            (
                _modifier
                for _modifier in self._get_effects(AttributeModifierEffect, attribute)
                if (obj, attribute) not in self._evaluated_attributes
                and _modifier.should_modify(obj, value, self)
            ),
            key=lambda e: e.priority,
        ):
            self._evaluated_attributes.add((obj, attribute))
            value = attribute_modifier.modify(obj, value, self)
            self._evaluated_attributes.remove((obj, attribute))
        return value

    def resolve(self, event: Event[V]) -> EventResolution:
        if not event.is_valid():
            return EventResolution([])

        if eligible_replacements := [
            replacement_effect
            for replacement_effect in self._get_effects(ReplacementEffect, event.name)
            if replacement_effect not in self._exhausted_replacement_effects
            and replacement_effect.can_replace(self, event)
        ]:

            replacement_effect = min(eligible_replacements, key=lambda r: r.priority)

            self._exhausted_replacement_effects.add(replacement_effect)
            previous_active_replacement_effect = self._active_replacement_effect
            self._active_replacement_effect = replacement_effect
            previous_replacement_results = self._replacement_results
            replacement_effect.resolve(self, event)
            self._active_replacement_effect = previous_active_replacement_effect
            self._exhausted_replacement_effects.remove(replacement_effect)
            resolution = EventResolution(self._replacement_results)
            self._replacement_results = previous_replacement_results
            return resolution

        if self._active_event:
            event.parent = self._active_event
            self._active_event.children.append(event)

        # TODO after instead?
        for trigger_effect in self._get_effects(TriggerEffect, event.name):
            if trigger_effect.should_trigger(self, event):
                self._pending_triggers.append((trigger_effect, event))
                if trigger_effect.should_deregister(self, event):
                    self.deregister_effect(trigger_effect)

        previous_active_replacement_effect = self._active_replacement_effect
        previous_active_event = self._active_event
        if not previous_active_replacement_effect:
            self._active_event = event
        self._active_replacement_effect = None

        event.result = event.resolve(self)

        if not previous_active_replacement_effect:
            self._active_event = previous_active_event
        self._active_replacement_effect = previous_active_replacement_effect

        resolution = EventResolution([event])

        if previous_active_replacement_effect:
            self._replacement_results.append(resolution)

        self.history.append(event)

        return resolution

    def last_event_of_type(self, event_type: type[E]) -> E | None:
        for event in reversed(self.history):
            if isinstance(event, event_type):
                return event

    def resolve_pending_triggers(self, parent_event: Event | None = None) -> None:
        # TODO disallow triggering multiple times in some way as well?
        for _ in range(self.MAX_TRIGGER_RECURSION):
            if self._pending_triggers:
                triggers = self._pending_triggers
                self._pending_triggers = []
                for trigger_effect, trigger_event in sorted(
                    triggers, key=lambda vs: vs[0].priority
                ):
                    previous_active_event = self._active_event
                    previous_replacement_effects = self._exhausted_replacement_effects
                    previous_active_replacement_effect = self._active_replacement_effect
                    previous_replacement_results = self._replacement_results
                    self._active_event = parent_event
                    self._exhausted_replacement_effects = set()
                    self._active_replacement_effect = None
                    self._replacement_results = []
                    trigger_effect.resolve(self, trigger_event)
                    self._active_event = previous_active_event
                    self._exhausted_replacement_effects = previous_replacement_effects
                    self._active_replacement_effect = previous_active_replacement_effect
                    self._replacement_results = previous_replacement_results
            else:
                return
        raise TriggerLoopError()


class _EventMeta(type):
    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        if "name" not in attributes:
            attributes["name"] = "_".join(
                s.lower() for s in re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
            )
        return super().__new__(metacls, name, bases, attributes, **kwargs)


@dataclasses.dataclass(kw_only=True)
class Event(Generic[V], metaclass=_EventMeta):
    name: ClassVar[str]
    parent: Event | None = None
    children: list[Event] = dataclasses.field(default_factory=list)
    result: V | None = None

    def __iter__(self) -> Iterator[Event]:
        yield self
        for child in self.children:
            yield from child

    def iter_type(self, event_type: type[E]) -> Iterator[E]:
        for event in self:
            if isinstance(event, event_type):
                yield event

    def is_valid(self) -> bool:
        return True

    @abstractmethod
    def resolve(self, es: EventSystem) -> V: ...

    def branch(self, event_type: type[Event] | None = None, **kwargs) -> Self:
        return (event_type or self.__class__)(
            **(
                {
                    f.name: getattr(self, f.name)
                    for f in dataclasses.fields(event_type or self)
                    if hasattr(self, f.name) and f.name not in ("children", "result")
                }
                | kwargs
            )
        )


class _EffectMeta(ABCMeta):
    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs,
    ) -> type:
        klass = super().__new__(metacls, name, bases, attributes, **kwargs)
        if ABC not in bases:
            if not hasattr(klass, "priority"):
                raise ValueError(f"{klass} missing priority")

        return klass


class Effect(ABC, metaclass=_EffectMeta):
    effect_type: ClassVar[str]
    target: ClassVar[Any]
    priority: ClassVar[int]


class _EventEffectMeta(_EffectMeta):
    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs,
    ) -> type:
        klass = super().__new__(metacls, name, bases, attributes, **kwargs)
        if ABC not in bases:
            if "target" not in attributes:
                klass.target = get_args(klass.__orig_bases__[0])[0].name

        return klass


class EventEffect(Effect, ABC, metaclass=_EventEffectMeta):
    target: ClassVar[str]


E = TypeVar("E", bound=Event)
F = TypeVar("F", bound=Effect)


@dataclasses.dataclass
class EventResolution:
    events: list[Event | EventResolution]

    def __iter__(self) -> Iterator[Event]:
        for item in self.events:
            if isinstance(item, EventResolution):
                yield from item
            else:
                for event in item:
                    yield event

    def iter_type(self, event_type: type[E]) -> Iterator[E]:
        for event in self:
            if isinstance(event, event_type):
                yield event

    def has_type(self, event_type: type[Event]) -> bool:
        return any(isinstance(event, event_type) for event in self)


class ReplacementEffect(EventEffect, Generic[E], ABC):
    effect_type = "replacement"

    def can_replace(self, es: EventSystem, event: E) -> bool:
        return True

    @abstractmethod
    def resolve(self, es: EventSystem, event: E) -> None: ...


class TriggerEffect(EventEffect, Generic[E], ABC):
    effect_type = "trigger"

    def should_trigger(self, es: EventSystem, event: E) -> bool:
        return True

    def should_deregister(self, es: EventSystem, event: E) -> bool:
        return False

    @abstractmethod
    def resolve(self, es: EventSystem, event: E) -> None: ...


@dataclasses.dataclass
class Modifiable(Generic[V]):
    attribute: ModifiableAttribute[V]
    instance: object

    def get_base(self) -> V:
        return self.attribute.get_base(self.instance)

    def get(self, es: EventSystem) -> V:
        return self.attribute.get(self.instance, es)

    def set(self, value: V) -> None:
        setattr(self.instance, self.attribute.source_name, value)


@dataclasses.dataclass(frozen=True)
class ModifiableAttribute(Generic[V]):
    name: str
    source_name: str

    def get(self, instance: object, es: EventSystem) -> V:
        return es.determine_attribute(
            instance, self, getattr(instance, self.source_name)
        )

    def get_base(self, instance: object) -> V:
        return getattr(instance, self.source_name)

    # TODO need context?
    def __get__(
        self, instance: object | None, owner
    ) -> Modifiable[V] | ModifiableAttribute:
        if instance is None:
            return self
        return Modifiable(self, instance)

    # TODO
    def __set__(self, instance: object, value: V):
        setattr(instance, self.source_name, value)

@dataclasses.dataclass
class _GetFreezer:
    v: Any

    def __get__(self, instance: object | None, owner):
        return self.v


class _AttributeModifierMeta(_EffectMeta):
    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs,
    ) -> type:
        klass = super().__new__(metacls, name, bases, attributes, **kwargs)
        if ABC not in bases:
            if not (target := getattr(klass, "target", None)):
                raise ValueError(f"{klass} missing target")
            if not isinstance(target, ModifiableAttribute):
                raise ValueError(f"{klass} has invalid target {target}")
            # Very ugly hack, to make sure the ModifiableAttribute is never bound
            # to an instance when accessed from the modifier.
            klass.target = _GetFreezer(klass.target)

        return klass


class AttributeModifierEffect(
    Effect, Generic[T, V], ABC, metaclass=_AttributeModifierMeta
):
    effect_type = "attribute_modifier"
    target: ClassVar[ModifiableAttribute]

    @abstractmethod
    def should_modify(self, obj: T, value: V, es: EventSystem) -> bool: ...

    @abstractmethod
    def modify(self, obj: T, value: V, es: EventSystem) -> V: ...


class WithModifiableAttributesMeta(type):

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs,
    ) -> type:
        for key, annotation in attributes.get("__annotations__", {}).items():
            if isinstance(annotation, str):
                annotation = eval(annotation)
            if (
                hasattr(annotation, "__origin__")
                and issubclass(annotation.__origin__, ModifiableAttribute)
                # TODO
                # and not key in attributes
            ):
                attributes[key] = ModifiableAttribute(key, "_" + key)
        return super().__new__(metacls, name, bases, attributes)


class WithModifiableAttributes(metaclass=WithModifiableAttributesMeta): ...
