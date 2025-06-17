import dataclasses
from typing import Any


@dataclasses.dataclass(eq=False)
class Player:
    name: str
    points: int = 0

    def serialize(self) -> dict[str, Any]:
        return {"name": self.name, "points": self.points}
