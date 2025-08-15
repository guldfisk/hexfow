from __future__ import annotations

import dataclasses
import inspect
import linecache
import math
from collections.abc import Iterable
from typing import Any, ClassVar, Mapping, Self
from uuid import UUID

from pydantic import BaseModel


def get_line(cf):
    return linecache.getline(cf.f_code.co_filename, cf.f_lineno)


def get_parent_line() -> str:
    return get_line(inspect.currentframe().f_back.f_back)


def get_parent_statement() -> tuple[str, str]:
    cf = inspect.currentframe().f_back.f_back
    offset = 0
    ss = []
    opened = 0
    closed = 0
    while True:
        line = linecache.getline(cf.f_code.co_filename, cf.f_lineno + offset)
        ss.append(line)
        opened += line.count("(")
        closed += line.count(")")
        if opened == closed:
            break
        offset += 1
    return cf.f_code.co_filename.removeprefix(
        "/home/phdk/PycharmProjects/"
    ).removeprefix("/hexfow/") + "::" + str(cf.f_lineno), "".join(ss)


@dataclasses.dataclass
class UUIDNames:
    instance: ClassVar[UUIDNames | None] = None
    translation_map: dict[UUID, str]

    def __enter__(self):
        UUIDNames.instance = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        UUIDNames.instance = None


def obj_to_string(
    obj: Any, indent: int = 0, seen_objects: frozenset[int] = frozenset()
) -> str:
    idn = " " * 4 * indent
    if (
        isinstance(obj, UUID)
        and UUIDNames.instance
        and (translated := UUIDNames.instance.translation_map.get(obj))
    ):
        return f"UUID - {translated}"
    if hasattr(obj, "__table__"):
        return (
            idn
            + type(obj).__name__
            + " {\n"
            + "\n".join(
                obj_to_string(column.name, indent=indent + 1, seen_objects=seen_objects)
                + ": "
                + obj_to_string(
                    getattr(obj, column.name), indent + 1, seen_objects=seen_objects
                ).lstrip()
                + ","
                for column in obj.__table__.columns
            )
            + "\n"
            + idn
            + "}"
        )
    if isinstance(obj, BaseModel):
        return (
            idn
            + type(obj).__name__
            + " {\n"
            + "\n".join(
                obj_to_string(field_name, indent=indent + 1, seen_objects=seen_objects)
                + ": "
                + obj_to_string(
                    getattr(obj, field_name), indent + 1, seen_objects=seen_objects
                ).lstrip()
                + ","
                for field_name in obj.model_fields.keys()
            )
            + "\n"
            + idn
            + "}"
        )
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        if id(obj) in seen_objects:
            return idn + "..."
            # return idn+type(obj).__name__
        seen_objects |= frozenset((id(obj),))
        return (
            idn
            + type(obj).__name__
            + " {\n"
            + "\n".join(
                obj_to_string(field.name, indent=indent + 1, seen_objects=seen_objects)
                + ": "
                + (
                    obj_to_string(
                        getattr(obj, field.name), indent + 1, seen_objects=seen_objects
                    ).lstrip()
                    if field.name not in ("parent", "children")
                    else "..."
                )
                + ","
                for field in dataclasses.fields(obj)
            )
            + "\n"
            + idn
            + "}"
        )
    if isinstance(obj, Mapping):
        return (
            idn
            + "{\n"
            + "\n".join(
                obj_to_string(k, indent=indent + 1, seen_objects=seen_objects)
                + ": "
                + obj_to_string(v, indent + 1, seen_objects=seen_objects).lstrip()
                + ","
                for k, v in obj.items()
            )
            + "\n"
            + idn
            + "}"
        )
    if isinstance(obj, Iterable) and not isinstance(obj, str):
        brackets = "[]" if isinstance(obj, list) else "()"
        return (
            idn
            + brackets[0]
            + "\n"
            + "\n".join(
                obj_to_string(v, indent + 1, seen_objects=seen_objects) + ","
                for v in obj
            )
            + "\n"
            + idn
            + brackets[1]
        )
    return idn + repr(obj)


class Printer:
    depth: int = 0

    @classmethod
    def print(cls, *args, **kwargs) -> None:
        print(*args, **kwargs)

    @classmethod
    def dp_object(cls, v: Any) -> None:
        print(obj_to_string(v))


class DDepth:
    previous: int

    def __enter__(self):
        self.previous = Printer.depth
        Printer.depth += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        Printer.depth = self.previous


@dataclasses.dataclass
class TitledPrinter:
    title: str
    additional_title: str | None = None

    def __enter__(self) -> Self:
        title = self.title.strip()
        title = f"{title[:48]} ... {title[-27:]}" if len(title) > 80 else title
        title = f" {title} "
        title = (
            ("-" * math.floor((100 - len(title)) / 2))
            + title
            + "-" * math.ceil((100 - len(title)) / 2)
        )
        if self.additional_title:
            title += "    " + (
                "... " + self.additional_title[-96:]
                if len(self.additional_title) > 100
                else self.additional_title
            )
        Printer.print(title)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Printer.print("-" * 100)


def print_titled(vs: Iterable[Any], title: str) -> None:
    with TitledPrinter(title):
        for v in vs:
            Printer.print(v)


def dp(*vs: Any, title: str | None = None) -> None:
    line_identifier, line_content = get_parent_statement()
    with TitledPrinter(
        title
        or " ".join(_s for s in line_content.split("\n") if (_s := s.strip()))
        .removeprefix("dp(")
        .removesuffix(")")
        .removesuffix(","),
        line_identifier,
    ):
        for v in vs:
            Printer.dp_object(v)


def mark(f):
    def marked(*args, **kwargs):
        with DDepth():
            Printer.print("~" * 100)
            try:
                v = f(*args, **kwargs)
            finally:
                Printer.print("~" * 100)
            return v

    return marked
