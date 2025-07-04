import re
from abc import ABC
from typing import ClassVar, Any

from events.eventsystem import ModifiableMeta
from game.descriptions import description_from_docstring


def get_registered_meta():
    class _RegisteredMeta(ModifiableMeta):
        registry: ClassVar[dict[str, type]] = {}

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
                        s.lower()
                        for s in re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
                    )
                if "name" not in attributes:
                    attributes["name"] = " ".join(
                        re.findall("[A-Z][^A-Z]+|[A-Z]+(?![^A-Z])", name)
                    )
            cls = super().__new__(metacls, name, bases, attributes, **kwargs)
            if ABC not in bases:
                metacls.registry[cls.identifier] = cls
                if "description" not in attributes and cls.__doc__:
                    cls.description = description_from_docstring(cls.__doc__)
            return cls

    return _RegisteredMeta


class Registered(ABC):
    identifier: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str | None] = None
    related_statuses: ClassVar[list[str]] = []
