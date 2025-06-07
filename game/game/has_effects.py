from __future__ import annotations

import dataclasses
from typing import TypeVar, Generic

from events.eventsystem import Effect, ES


@dataclasses.dataclass(kw_only=True)
class HasEffectChildren:
    children: list[HasEffects] = dataclasses.field(default_factory=list, repr=False)


P = TypeVar("P", bound=HasEffectChildren)


@dataclasses.dataclass(kw_only=True)
class HasEffects(HasEffectChildren, Generic[P]):
    effects: set[Effect] = dataclasses.field(default_factory=set, init=False)
    parent: P | None = dataclasses.field(default=None, repr=False)

    # TODO :(
    def __post_init__(self):
        if self.parent is not None:
            self.parent.children.append(self)

    def register_effects(self, *effects: Effect) -> None:
        self.effects.update(effects)
        ES.register_effects(*effects)

    def deregister_effects(self, *effects: Effect) -> None:
        for effect in effects:
            self.effects.discard(effect)
        ES.deregister_effects(*effects)

    def deregister(self) -> None:
        ES.deregister_effects(*self.effects)
        self.effects = set()
        for child in list(self.children):
            child.deregister()
        if self.parent:
            self.parent.children.remove(self)
