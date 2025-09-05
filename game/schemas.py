from typing import Any

from pydantic import BaseModel


class DecisionValidationError(Exception): ...


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
    # TODO these should be positive
    indexes: set[int]


class OrderedIndexesSchema(BaseModel):
    # TODO these should be positive
    indexes: list[int]


# TODO should just use index?
class SelectOptionAtHexDecisionPointSchema(BaseModel):
    index: int


class DeployArmyDecisionPointSchema(BaseModel):
    deployment: list[tuple[str, CCSchema]]
