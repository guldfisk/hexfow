import inspect
from importlib import import_module
from typing import Iterator

from pygments import highlight
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers import PythonLexer

from model import models
from model.models import Base


def _print_highlighted(s: str) -> None:
    print(highlight(s, PythonLexer(), TerminalFormatter()))  # noqa T201


def _import_classes_from_module(module_name: str, class_names: list[str]) -> None:
    m = import_module(module_name)
    for class_name in class_names:
        globals()[class_name] = getattr(m, class_name)
    _print_highlighted(f'from {module_name} import {", ".join(sorted(class_names))}')


def _get_model_class_names() -> Iterator[str]:
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and issubclass(obj, Base):
            yield name


_import_classes_from_module("datetime", ["date", "datetime", "timedelta", "timezone"])
_import_classes_from_module(
    "model.models", list(_get_model_class_names()) + ["create_models"]
)
_import_classes_from_module(
    "sqlalchemy",
    [
        "and_",
        "case",
        "cast",
        "delete",
        "insert",
        "literal",
        "or_",
        "select",
        "text",
        "func",
        "column",
    ],
)
_import_classes_from_module("model.engine", ["SS"])

_import_classes_from_module("model.values", ["GameStatus", "GameType"])
