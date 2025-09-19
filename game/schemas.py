from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel


def no_duplicates(value: list[int]) -> list[int]:
    assert len(value) == len(set(value))
    return value


class DecisionValidationError(Exception): ...


class PremoveSchema(BaseModel):
    for_options: list[dict[str, Any]]
    payload: dict[str, Any]


class DecisionResponseSchema(BaseModel):
    count: int
    payload: dict[str, Any]
    premove: PremoveSchema | None = None


class EmptySchema(BaseModel): ...


class CCSchema(BaseModel):
    r: int
    h: int


class SelectOptionDecisionPointSchema(BaseModel):
    index: int
    target: dict[str, Any]


class SingleCCSchema(BaseModel):
    cc: CCSchema


class IndexSchema(BaseModel):
    # TODO these should be positive
    index: int


class IndexesSchema(BaseModel):
    indexes: Annotated[list[int], AfterValidator(no_duplicates)]


class OrderedIndexesSchema(BaseModel):
    indexes: list[int]


# TODO should just use index?
class SelectOptionAtHexDecisionPointSchema(BaseModel):
    index: int


class SelectArmyDecisionPointSchema(BaseModel):
    units: list[str]


class DeployArmyDecisionPointSchema(BaseModel):
    deployments: list[tuple[str, CCSchema]]
