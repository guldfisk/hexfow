from typing import NamedTuple


class CubeCoordinate(NamedTuple):
    r: int
    h: int

    @property
    def l(self) -> int:
        return -sum(self)

