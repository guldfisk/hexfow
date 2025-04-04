from typing import Sequence, Any

from game.game.decisions import Option
from game.game.core import Unit


def select_unit(units: Sequence[Unit]) -> Unit:
    ...


def select_targeted_option(options: list[Option]) -> tuple[Option, Any]:
    ...