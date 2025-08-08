import re
from abc import ABC, ABCMeta
from typing import Any, Callable, Protocol


def snakeify(s: str) -> str:
    return "_".join(ss.lower() for ss in re.findall("[A-Z]+(?![a-z])|[A-Z][^A-Z]+", s))


def get_suffix_remover(suffix: str) -> Callable[[str], str]:
    def remover(s: str) -> str:
        return snakeify(s.removesuffix(suffix))

    return remover


def identity(s: str) -> str:
    return s


class NamedProtocol(Protocol):
    name: str


class GroupedProtocol(NamedProtocol):
    registry: dict[str, type]


def get_named_meta(
    name_function: Callable = snakeify, *, base_class: type = ABCMeta
) -> type[NamedProtocol]:
    class NamedMeta(base_class):
        def __new__(cls, name: str, bases: Any, dct: dict[str, Any]) -> type:
            if ABC not in bases:
                if "name" not in dct:
                    dct["name"] = name_function(name)
            return super().__new__(cls, name, bases, dct)  # type: ignore

    return NamedMeta


def get_grouping_meta(
    name_function: Callable = snakeify, *, base_class: type = ABCMeta
) -> type[GroupedProtocol]:
    class GrouperMeta(base_class):
        registry: dict[str, type] = {}

        def __new__(cls, name: str, bases: Any, dct: dict[str, Any]) -> type:
            if ABC not in bases:
                if "name" not in dct:
                    dct["name"] = name_function(name)
            klass: type = super().__new__(cls, name, bases, dct)  # type: ignore
            if ABC not in bases:
                cls.registry[dct["name"]] = klass
            return klass

    return GrouperMeta
