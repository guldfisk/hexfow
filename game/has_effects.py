from __future__ import annotations

from typing import Generic, TypeVar

from events.eventsystem import ES, Effect


class HasEffectChildren:
    def __init__(self):
        self.children: list[HasEffects] = []


G_HasEffectChildren = TypeVar("G_HasEffectChildren", bound=HasEffectChildren)


class HasEffects(HasEffectChildren, Generic[G_HasEffectChildren]):
    def __init__(self, parent: G_HasEffectChildren | None = None):
        super().__init__()
        self.effects: set[Effect] = set()
        self.parent = parent

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
            try:
                self.parent.children.remove(self)
            except ValueError:
                pass
