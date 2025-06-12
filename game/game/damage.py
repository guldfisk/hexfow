import dataclasses

from game.game.values import DamageType


@dataclasses.dataclass
class DamageSignature:
    amount: int
    type: DamageType = DamageType.PHYSICAL
    ap: int = 0
    lethal: bool = True
