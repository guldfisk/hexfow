from __future__ import annotations

import dataclasses
import functools
import inspect
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
    Callable,
)


T = TypeVar("T")
V = TypeVar("V")
C = TypeVar("C")
A = TypeVar("A", bound=Callable)


# TODO maybe triggers can't cause triggers to trigger?
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

        # TODO prob want both event begins and ends.
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
        self._evaluated_state_modifiers: set[tuple[object, Any]] = set()

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

    def determine_modifiable(self, obj: object, key: Any, request: Any, value: V) -> V:
        for attribute_modifier in sorted(
            (
                _modifier
                for _modifier in self._get_effects(StateModifierEffect, key)
                if (obj, key) not in self._evaluated_state_modifiers
                and _modifier.should_modify(obj, request, value)
            ),
            key=lambda e: e.priority,
        ):
            self._evaluated_state_modifiers.add((obj, key))
            value = attribute_modifier.modify(obj, request, value)
            self._evaluated_state_modifiers.remove((obj, key))
        return value

    def resolve(self, event: Event[V]) -> EventResolution:
        if not event.is_valid():
            return EventResolution([])

        if eligible_replacements := [
            replacement_effect
            for replacement_effect in self._get_effects(ReplacementEffect, event.name)
            if replacement_effect not in self._exhausted_replacement_effects
            and replacement_effect.can_replace(event)
        ]:
            replacement_effect = min(eligible_replacements, key=lambda r: r.priority)

            self._exhausted_replacement_effects.add(replacement_effect)
            previous_active_replacement_effect = self._active_replacement_effect
            self._active_replacement_effect = replacement_effect
            previous_replacement_results = self._replacement_results
            replacement_effect.resolve(event)
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
            if trigger_effect.should_trigger(event):
                self._pending_triggers.append((trigger_effect, event))
                if trigger_effect.should_deregister(event):
                    self.deregister_effect(trigger_effect)

        previous_active_replacement_effect = self._active_replacement_effect
        previous_active_event = self._active_event
        if not previous_active_replacement_effect:
            self._active_event = event
        self._active_replacement_effect = None

        event.result = event.resolve()

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
                    trigger_effect.resolve(trigger_event)
                    self._active_event = previous_active_event
                    self._exhausted_replacement_effects = previous_replacement_effects
                    self._active_replacement_effect = previous_active_replacement_effect
                    self._replacement_results = previous_replacement_results
            else:
                return
        raise TriggerLoopError()


class ScopedEventSystem(EventSystem):

    def __init__(self):
        self._es: EventSystem | None = None

    @property
    def history(self) -> list[Event]:
        return self._es.history

    def bind(self, es: EventSystem) -> None:
        self._es = es

    def has_pending_triggers(self) -> bool:
        return self._es.has_pending_triggers()

    def register_effect(self, effect: F) -> F:
        return self._es.register_effect(effect)

    def _get_effects(self, effect_type: type[F] | F, target: Any) -> list[F]:
        return self._es._get_effects(effect_type, target)

    def deregister_effect(self, effect: F) -> F:
        return self._es.deregister_effect(effect)

    def determine_modifiable(self, obj: object, key: Any, request: Any, value: V) -> V:
        return self._es.determine_modifiable(obj, key, request, value)

    def resolve(self, event: Event[V]) -> EventResolution:
        return self._es.resolve(event)

    def last_event_of_type(self, event_type: type[E]) -> E | None:
        return self._es.last_event_of_type(event_type)

    def resolve_pending_triggers(self, parent_event: Event | None = None) -> None:
        self._es.resolve_pending_triggers(parent_event)


ES = ScopedEventSystem()


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
    def resolve(self) -> V: ...

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

    def can_replace(self, event: E) -> bool:
        return True

    @abstractmethod
    def resolve(self, event: E) -> None: ...


class TriggerEffect(EventEffect, Generic[E], ABC):
    effect_type = "trigger"

    def should_trigger(self, event: E) -> bool:
        return True

    def should_deregister(self, event: E) -> bool:
        return False

    @abstractmethod
    def resolve(self, event: E) -> None: ...


@dataclasses.dataclass
class _BoundModifiableAttribute(Generic[T, V]):
    attribute: ModifiableAttribute[T, V]
    instance: object

    def get_base(self) -> V:
        return self.attribute.get_base(self.instance)

    def get(self, request: T) -> V:
        return self.attribute.get(self.instance, request)

    def set(self, value: V) -> None:
        setattr(self.instance, self.attribute.source_name, value)


@dataclasses.dataclass(frozen=True)
class ModifiableAttribute(Generic[T, V]):
    name: str
    source_name: str

    def get(self, instance: object, request: T) -> V:
        return ES.determine_modifiable(
            instance, self, request, getattr(instance, self.source_name)
        )

    def get_base(self, instance: object) -> V:
        return getattr(instance, self.source_name)

    def __get__(
        self, instance: object | None, owner
    ) -> _BoundModifiableAttribute[T, V] | ModifiableAttribute:
        if instance is None:
            return self
        return _BoundModifiableAttribute(self, instance)


@dataclasses.dataclass
class _GetFreezer:
    v: Any

    def __get__(self, instance: object | None, owner):
        return self.v


class _StateModifierMeta(_EffectMeta):
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

            if isinstance(target, ModifiableAttribute):
                # Very ugly hack, to make sure the ModifiableAttribute is never bound
                # to an instance when accessed from the modifier.
                klass.target = _GetFreezer(klass.target)
            elif getattr(target, "__target__", None):
                klass.target = target.__target__
            else:
                raise ValueError(f"{klass} has invalid target {target}")

        return klass


class StateModifierEffect(Effect, Generic[T, C, V], ABC, metaclass=_StateModifierMeta):
    effect_type = "state_modifier"

    def should_modify(self, obj: T, request: C, value: V) -> bool:
        return True

    @abstractmethod
    def modify(self, obj: T, request: C, value: V) -> V: ...


def modifiable(f: A) -> A:
    f.__modifiable__ = True
    return f


def _wrap_method(f: A) -> A:
    @functools.wraps(f)
    def _wrapper(self: object, request: Any) -> Any:
        v = f(self, request)
        return ES.determine_modifiable(self, f.__target__, request, v)

    return _wrapper


class ModifiableMeta(ABCMeta):

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
        **kwargs,
    ) -> type:
        modifiable_methods = []
        if ABC not in bases:
            for key, value in attributes.items():
                if not key.startswith("_") and getattr(value, "__modifiable__", None):
                    assert len(inspect.signature(value).parameters) == 2
                    attributes[key] = _wrap_method(value)
                    modifiable_methods.append((key, value, attributes[key]))

        for key, annotation in attributes.get("__annotations__", {}).items():
            if isinstance(annotation, str):
                annotation = eval(annotation)
            if hasattr(annotation, "__origin__") and issubclass(
                annotation.__origin__, ModifiableAttribute
            ):
                attributes[key] = ModifiableAttribute(key, "_" + key)
        klass = super().__new__(metacls, name, bases, attributes)
        for name, modifiable_method, wrapper in modifiable_methods:
            modifiable_method.__target__ = wrapper.__target__ = (klass, name)
        return klass


class Modifiable(ABC, metaclass=ModifiableMeta): ...
