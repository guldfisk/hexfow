from __future__ import annotations

import dataclasses
import functools
import re
from typing import Iterator


@functools.total_ordering
@dataclasses.dataclass
class Price:
    value: int
    additional: str
    payable: bool = True

    @property
    def compare_value(self) -> tuple[int, int]:
        return self.value, len(self.additional)

    def __gt__(self, other) -> bool:
        if isinstance(other, Price):
            return other.payable and (
                not self.payable or (self.compare_value > other.compare_value)
            )
        return False


@dataclasses.dataclass
class Creature:
    source: str
    cost: Price

    @classmethod
    def from_str(cls, s: str) -> Creature:
        return cls(
            s,
            Price(int(match.group(1)), match.group(2))
            if (match := re.match(r"^[^{]*\{(\d+)([a-z]*)}", s))
            else Price(0, "", False),
        )

    def serialize(self) -> str:
        return self.source


def load_creatures() -> Iterator[Creature]:
    with open("notes/creatures.txt", "r") as f:
        for raw in f.read().split("\n\n"):
            yield Creature.from_str(raw.strip())


def sort_creatures():
    result = "\n\n".join(
        c.serialize() for c in sorted(load_creatures(), key=lambda c: c.cost)
    )
    with open("notes/creatures.txt", "w") as f:
        f.write(result)


if __name__ == "__main__":
    sort_creatures()
