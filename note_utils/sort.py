from __future__ import annotations

import dataclasses
import re
from typing import Iterator


# @functools.total_ordering
@dataclasses.dataclass
class Price:
    value: int
    additional: str
    payable: bool = True

    @property
    def compare_value(self) -> tuple[float, int]:
        return -1 / self.value if self.payable else 0, len(self.additional)

    # def __gt__(self, other) -> bool:
    #     if isinstance(other, Price):
    #         return other.payable and (
    #             not self.payable or (self.compare_value > other.compare_value)
    #         )
    #     return False


@dataclasses.dataclass
class Creature:
    source: str
    cost: Price
    name: str

    @classmethod
    def from_str(cls, s: str) -> Creature:
        return cls(
            s,
            Price(int(match.group(1)), match.group(2))
            if (match := re.match(r"^[^{]*\{(\d+)([a-z]*)}", s))
            else Price(0, "", False),
            match.group().strip() if (match := re.match(r"[^{\n]+", s)) else "",
        )

    def serialize(self) -> str:
        return self.source


def load_creatures() -> Iterator[Creature]:
    with open("notes/creatures.txt", "r") as f:
        for raw in f.read().split("\n\n"):
            yield Creature.from_str(raw.strip())


def sort_creatures():
    # for v in sorted((c.cost.compare_value, c.name) for c in load_creatures()):
    #     print(v)
    result = "\n\n".join(
        c.serialize()
        for c in sorted(load_creatures(), key=lambda c: (c.cost.compare_value, c.name))
    )
    with open("notes/creatures.txt", "w") as f:
        f.write(result)


if __name__ == "__main__":
    sort_creatures()
