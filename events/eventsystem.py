from __future__ import annotations

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


class TriggerLoopError(Exception):
    ...


class EventSystem:
    MAX_TRIGGER_RECURSION: ClassVar[int] = 128
    thread_local: ClassVar[threading.local] = threading.local()

    def __init__(self):
        self._effects: MutableMapping[
            str, MutableMapping[str, list[Effect]]
        ] = defaultdict(lambda: defaultdict(list))
        self._pending_triggers: list[tuple[int, Callable[[], None]]] = []

    @classmethod
    def init(cls) -> None:
        cls.thread_local.instance = cls()

    @classmethod
    def i(cls) -> Self:
        return cls.thread_local.instance

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
        if eligible_replacements := [
            replacement_effect
            for replacement_effect in self._get_effects(ReplacementEffect, event.name)
            if replacement_effect not in event.replaced_by
            and replacement_effect.can_replace(event)
        ]:
            event.replaced_by.add(
                (
                    replacement_effect := min(
                        eligible_replacements, key=lambda r: r.priority
                    )
                )
            )
            return EventResolution(list(replacement_effect.resolve(event)))
        if event.parent:
            event.parent.children.append(event)
        # TODO after instead?
        for trigger_effect in self._get_effects(TriggerEffect, event.name):
            if callback := trigger_effect.should_trigger(event):
                self._pending_triggers.append((trigger_effect.priority, callback))
        event.result = event.resolve()
        return EventResolution([event])

    def resolve_pending_triggers(self) -> None:
        for _ in range(self.MAX_TRIGGER_RECURSION):
            if self._pending_triggers:
                triggers = self._pending_triggers
                self._pending_triggers = []
                for _, callback in sorted(triggers, key=lambda vs: vs[0]):
                    callback()
            else:
                return
        raise TriggerLoopError()


def es() -> EventSystem:
    return EventSystem.i()


@dataclasses.dataclass
class EventResolution:
    events: list[Event | EventResolution]

    # def __init__(self):

    def iter_type(self, event_type: type[E]) -> Iterator[E]:
        for item in self.events:
            if isinstance(item, EventResolution):
                yield from item
            else:
                for event in item:
                    if isinstance(event, event_type):
                        yield event


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
    replaced_by: set[ReplacementEffect] = dataclasses.field(default_factory=set)
    parent: Event | None = None
    children: list[Event] = dataclasses.field(default_factory=list)
    result: V | None = None

    # def __post_init__(self):
    #     if self.parent:
    #         self.parent.children.append(self)

    # def value_as(self, event_type: type[Event[V]]) -> V | None:
    #     if isinstance(self, event_type):
    #         return self.result
    #     return None

    def __iter__(self) -> Iterator[Event]:
        yield self
        for child in self.children:
            yield from child

    def iter_type(self, event_type: type[E]) -> Iterator[E]:
        for event in self:
            if isinstance(event, event_type):
                yield event

    @abstractmethod
    def resolve(self) -> V:
        ...

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


class ReplacementEvent(Event):
    replacement_effect: ReplacementEffect
    replacing: Event

    def resolve(self) -> None:
        self.replacement_effect.resolve(self.replacing)


class Effect:
    effect_type: ClassVar[str]
    target_name: ClassVar[str]
    priority: ClassVar[int]


E = TypeVar("E", bound=Event)
F = TypeVar("F", bound=Effect)


class ReplacementEffect(Effect, Generic[E], ABC):
    effect_type = "replacement"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "target_name"):
            cls.target_name = get_args(cls.__orig_bases__[0])[0].name

    @abstractmethod
    def can_replace(self, event: E) -> bool:
        ...

    @abstractmethod
    def resolve(self, event: E) -> Iterator[EventResolution]:
        ...


class TriggerEffect(Effect, Generic[E], ABC):
    effect_type = "trigger"

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "target_name"):
            cls.target_name = get_args(cls.__orig_bases__[0])[0].name

    @abstractmethod
    def should_trigger(self, event: E) -> Callable[[], None] | None:
        ...


@dataclasses.dataclass(frozen=True)
class ModifiableAttribute(Generic[T, V]):
    name: str
    source_name: str | None = None

    def __post_init__(self):
        if self.source_name is None:
            object.__setattr__(self, "source_name", f"_{self.name}")

    def get(self, instance: T) -> V:
        return EventSystem.i().determine_attribute(
            instance, self.name, getattr(instance, self.source_name)
        )

    def get_base(self, instance: T) -> V:
        return getattr(instance, self.source_name)

    def __get__(self, instance: T | None, owner) -> V | ModifiableAttribute:
        if instance is None:
            return self
        return self.get(instance)

    def __set__(self, instance: T, value: V) -> None:
        setattr(instance, self.source_name, value)


class AttributeModifierEffect(Effect, Generic[T, V], ABC):
    effect_type = "attribute_modification"

    @abstractmethod
    def should_modify(self, obj: T, value: V) -> bool:
        ...

    @abstractmethod
    def modify(self, obj: T, value: V) -> V:
        ...
