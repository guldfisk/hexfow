from typing import Any, Self

from pydantic import AfterValidator, BaseModel, model_validator
from typing_extensions import Annotated

from game.info.registered import UnknownIdentifierError
from game_server.game_types import GameType
from model.schemas import ScenarioSchema


def is_valid_game_type(v: str) -> str:
    assert v in GameType.registry.keys()
    return v


GameTypeValue = Annotated[str, AfterValidator(is_valid_game_type)]


class CreateGameSchema(BaseModel):
    game_type: GameTypeValue
    with_fow: bool
    custom_armies: bool
    time_bank: float | None = None
    time_grace: float | None = None
    settings: dict[str, Any]

    @model_validator(mode="after")
    def make_query(self) -> Self:
        GameType.registry[self.game_type].model_validate(self.settings)

        return self


class CreateMapSchema(BaseModel):
    name: str
    scenario: ScenarioSchema

    @model_validator(mode="after")
    def make_query(self) -> Self:
        try:
            self.scenario.get_scenario()
        except UnknownIdentifierError as e:
            raise ValueError(
                f"invalid identifier {e.identifier} for {e.registered_type.__name__}"
            )

        return self
