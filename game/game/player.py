import dataclasses


@dataclasses.dataclass(eq=False)
class Player:
    name: str
    points: int = 0
