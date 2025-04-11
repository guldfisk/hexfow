from __future__ import annotations

from typing import NamedTuple, Iterator, Mapping, Any


class CC(NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)

    def __add__(self, other: CC) -> CC:
        return CC(self.r + other.r, self.h + other.h)

    def __sub__(self, other: CC) -> CC:
        return CC(self.r - other.r, self.h - other.h)

    def neighbors(self) -> Iterator[CC]:
        for offset in neighbor_offsets:
            yield self + offset

    def serialize(self) -> Mapping[str, Any]:
        return {"r": self.r, "h": self.h}

    def distance_to(self, to_: CC) -> int:
        difference = self - to_
        return (
            abs(difference.r) + abs(difference.r + difference.h) + abs(difference.h)
        ) // 2


neighbor_offsets = [
    CC(1, 0),
    CC(1, -1),
    CC(0, -1),
    CC(-1, 0),
    CC(-1, 1),
    CC(0, 1),
]
