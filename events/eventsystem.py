from __future__ import annotations

import contextlib
import dataclasses
import re
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import (
    TypeVar,
    ClassVar,
    MutableMapping,
    Callable,
    Self,
    Any,
    Generic,
    get_args,
    Iterator,
)


T = TypeVar("T")
V = TypeVar("V")


class TriggerLoopError(Exception): ...


class EventSystem:
    MAX_TRIGGER_RECURSION: ClassVar[int] = 128

    def __init__(self):
        self._effects: MutableMapping[str, MutableMapping[str, list[Effect]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        self._pending_triggers: list[tuple[TriggerEffect, Event]] = []

        self.history: list[Event] = []

        self._active_event: Event | None = None

        # TODO names
        self._active_replacement_effects: set[ReplacementEffect] = set()
        self._active_replacement_effect: ReplacementEffect | None = None
        self._replacement_results: list[EventResolution] = []

    def has_pending_triggers(self) -> bool:
        return bool(self._pending_triggers)

    def register_effect(self, effect: F) -> F:
        self._effects[effect.effect_type][effect.target_name].append(effect)
        return effect

    def _get_effects(self, effect_type: type[F] | F, effect_name: str) -> list[F]:
        return self._effects[effect_type.effect_type][effect_name]

    def deregister_effect(self, effect: F) -> F:
        self._effects[effect.effect_type][effect.target_name].remove(effect)
        return effect

    def determine_attribute(
        self,
        obj: T,
        attribute_name: str,
        value: V,
    ) -> V:
        for attribute_modifier in sorted(
            (
                _modifier
                for _modifier in self._get_effects(
                    AttributeModifierEffect, attribute_name
                )
                if _modifier.should_modify(obj, value)
            ),
            key=lambda e: e.priority,
        ):
            value = attribute_modifier.modify(obj, value)
        return value

    def resolve_event(self, event: Event[V]) -> EventResolution:
        if not event.is_valid():
            return EventResolution([])

        if eligible_replacements := [
            replacement_effect
            for replacement_effect in self._get_effects(ReplacementEffect, event.name)
            if replacement_effect not in self._active_replacement_effects
            and replacement_effect.can_replace(event)
        ]:

            replacement_effect = min(eligible_replacements, key=lambda r: r.priority)

            self._active_replacement_effects.add(replacement_effect)
            previous_replacement_effect = self._active_replacement_effect
            self._active_replacement_effect = replacement_effect
            previous_replacement_results = self._replacement_results
            replacement_effect.resolve(self, event)
            self._active_replacement_effect = previous_replacement_effect
            self._active_replacement_effects.remove(replacement_effect)
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

        previous_replacement_effect = self._active_replacement_effect
        previous_active_event = self._active_event
        if not previous_replacement_effect:
            self._active_event = event
        self._active_replacement_effect = None

        event.result = event.resolve(self)

        if not previous_replacement_effect:
            self._active_event = previous_active_event
        self._active_replacement_effect = previous_replacement_effect

        resolution = EventResolution([event])

        if previous_replacement_effect:
            self._replacement_results.append(resolution)

        self.history.append(event)

        return resolution

    def last_event_of_type(self, event_type: type[E]) -> E | None:
        for event in reversed(self.history):
            if isinstance(event, event_type):
                return event

    def resolve_pending_triggers(self, parent_event: Event | None = None) -> None:
        for _ in range(self.MAX_TRIGGER_RECURSION):
            if self._pending_triggers:
                triggers = self._pending_triggers
                self._pending_triggers = []
                for trigger_effect, trigger_event in sorted(
                    triggers, key=lambda vs: vs[0].priority
                ):
                    previous_active_event = self._active_event
                    previous_replacement_effects = self._active_replacement_effects
                    previous_active_replacement_effect = self._active_replacement_effect
                    previous_replacement_results = self._replacement_results
                    self._active_event = parent_event
                    self._active_replacement_effects = set()
                    self._active_replacement_effect = None
                    self._replacement_results = []
                    trigger_effect.resolve(self, trigger_event)
                    self._active_event = previous_active_event
                    self._active_replacement_effects = previous_replacement_effects
                    self._active_replacement_effect = previous_active_replacement_effect
                    self._replacement_results = previous_replacement_results
            else:
                return
        raise TriggerLoopError()


class _EventMetaclass(type):
    def __new__(
        metacls: type,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        if "name" not in namespace:
            namespace["name"] = "_".join(
                s.lower() for s in re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
            )
        return super().__new__(metacls, name, bases, namespace, **kwargs)


@dataclasses.dataclass(kw_only=True)
class Event(Generic[V], metaclass=_EventMetaclass):
    name: ClassVar[str]
    parent: Event | None = None
    children: list[Event] = dataclasses.field(default_factory=list)
    # TODO
    result: V | None = None

    def __iter__(self) -> Iterator[Event]:
        yield self
        for child in self.children:
            yield from child

    # TODO
    # def __repr__(self) -> str:
    #     return "{}({})".format(
    #         type(self),
    #         ", ".join(
    #             "{}={}".format(
    #                 field.name,
    #                 (
    #                     type(v).name
    #                     if (v := getattr(self, field.name)) and field.name == "parent"
    #                     else (f"({len(v)})" if field.name == "children" else v)
    #                 ),
    #             )
    #             for field in dataclasses.fields(self)
    #         ),
    #     )

    def iter_type(self, event_type: type[E]) -> Iterator[E]:
        for event in self:
            # TODO strict check?
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


class Effect:
    effect_type: ClassVar[str]
    target_name: ClassVar[str]
    priority: ClassVar[int]


E = TypeVar("E", bound=Event)
F = TypeVar("F", bound=Effect)


# @dataclasses.dataclass
# class EventResolutionSet(Generic[E]):
#     iterator: Iterator[E]
#
#     def __iter__(self) -> Iterator[E]:
#         return self.iterator
#
#     def then(self, f: Callable[[list[E]], ...]) -> None:
#         if events := list(self):
#             f(events)


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
            # TODO strict check?
            if isinstance(event, event_type):
                yield event

    def has_type(self, event_type: type[Event]) -> bool:
        return any(isinstance(event, event_type) for event in self)


class ReplacementEffect(Effect, Generic[E], ABC):
    effect_type = "replacement"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "target_name"):
            cls.target_name = get_args(cls.__orig_bases__[0])[0].name

    def can_replace(self, event: E) -> bool:
        return True

    @abstractmethod
    def resolve(self, es: EventSystem, event: E) -> None: ...


class TriggerEffect(Effect, Generic[E], ABC):
    effect_type = "trigger"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "target_name"):
            cls.target_name = get_args(cls.__orig_bases__[0])[0].name

    def should_trigger(self, es: EventSystem, event: E) -> bool:
        return True

    @abstractmethod
    def resolve(self, es: EventSystem, event: E) -> None: ...


@dataclasses.dataclass
class Modifiable(Generic[T, V]):
    attribute: ModifiableAttribute[T, V]
    instance: T

    # def get(self, es: EventSystem) -> V:
    #     return self.attribute

    def get(self, instance: T, es: EventSystem) -> V:
        return es.determine_attribute(
            instance, self.name, getattr(instance, self.source_name)
        )


@dataclasses.dataclass(frozen=True)
class ModifiableAttribute(Generic[T, V]):
    name: str
    source_name: str | None = None

    def __post_init__(self):
        if self.source_name is None:
            object.__setattr__(self, "source_name", f"_{self.name}")

    def get(self, instance: T, es: EventSystem) -> V:
        return es.determine_attribute(
            instance, self.name, getattr(instance, self.source_name)
        )

    def get_base(self, instance: T) -> V:
        return getattr(instance, self.source_name)

    # TODO need context?
    def __get__(self, instance: T | None, owner) -> V | ModifiableAttribute:
        if instance is None:
            return self
        return self.get(instance)

    def __set__(self, instance: T, value: V) -> None:
        setattr(instance, self.source_name, value)


class AttributeModifierEffect(Effect, Generic[T, V], ABC):
    effect_type = "attribute_modifier"

    @abstractmethod
    def should_modify(self, obj: T, value: V) -> bool: ...

    @abstractmethod
    def modify(self, obj: T, value: V) -> V: ...
