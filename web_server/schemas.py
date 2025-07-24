from pydantic import BaseModel
from pydantic import AfterValidator
from typing_extensions import Annotated

from model.values import GameType


def is_valid_game_type(v: str) -> str:
    assert any(gt.value == v for gt in GameType)
    return v


GameTypeValue = Annotated[str, AfterValidator(is_valid_game_type)]


class CreateGameSchema(BaseModel):
    game_type: GameTypeValue
