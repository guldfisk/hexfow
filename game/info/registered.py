from __future__ import annotations

import dataclasses
import functools
import re
from abc import ABC
from typing import Any, ClassVar, Self

from events.eventsystem import ModifiableMeta
from game.descriptions import description_from_docstring


@dataclasses.dataclass
class UnknownIdentifierError(Exception):
    registered_type: type
    identifier: str


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

                # TODO
                def _sub(related_values: list[str], match: re.Match) -> str:
                    if match.group(1) not in related_values:
                        related_values.append(match.group(1))

                    return " ".join(e.capitalize() for e in match.group(1).split("_"))

                cls.related_statuses = list(cls.related_statuses)
                cls.related_units = list(cls.related_units)
                if cls.description:
                    cls.description = re.sub(
                        r"<([^<>]+)>",
                        functools.partial(_sub, cls.related_statuses),
                        cls.description,
                    )
                    cls.description = re.sub(
                        r"\[([^<>]+)]",
                        functools.partial(_sub, cls.related_units),
                        cls.description,
                    )

            return cls

    return _RegisteredMeta


class Registered(ABC):
    identifier: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[str]
    description: ClassVar[str | None] = None
    related_statuses: ClassVar[list[str]] = []
    related_units: ClassVar[list[str]] = []

    # TODO name
    @classmethod
    def get_class(cls, identifier: str) -> type[Self]:
        try:
            return cls.registry[identifier]
        except KeyError:
            raise UnknownIdentifierError(cls, identifier)
