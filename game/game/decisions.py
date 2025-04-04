import dataclasses
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, TypeAlias, Mapping


O = TypeVar("O")

JSON: TypeAlias = Mapping[str, Any]


class DecisionPoint(ABC, Generic[O]):

    @abstractmethod
    def get_explanation(self) -> str: ...

    @abstractmethod
    def serialize_payload(self) -> JSON: ...

    def serialize(self) -> JSON:
        return {
            "explanation": self.get_explanation(),
            "payload": self.serialize_payload(),
        }

    @abstractmethod
    def parse_response(self, v: Any) -> O: ...


# class Option(ABC):
#
#     @abstractmethod
#     def serialize_values(self) -> JSON: ...
#
#     def serialize(self) -> JSON:
#         return {"type": type(self).__name__, "values": self.serialize_values()}
#
#
# @dataclasses.dataclass
# class SelectOptionAction(Action[Option]):
#     options: list[Option]
#     explanation: str
#
#     def get_explanation(self) -> str:
#         return self.explanation
#
#     def serialize_payload(self) -> JSON:
#         return {"options": [option.serialize() for option in self.options]}
#
#     def parse_response(self, v: Any) -> Option:
#         return self.options[v["index"]]


class TargetProfile(ABC, Generic[O]):
    @abstractmethod
    def serialize_values(self) -> JSON: ...

    def serialize(self) -> JSON:
        return {"type": type(self).__name__, "values": self.serialize_values()}

    @abstractmethod
    def parse_response(self, v: Any) -> O: ...


# T = TypeVar("T", bound=TargetProfile)

# @dataclasses.dataclass
# class OneOfUnits(TargetProfile):
#     ...


@dataclasses.dataclass(kw_only=True)
class Option(ABC, Generic[O]):
    target_profile: TargetProfile[O]

    @abstractmethod
    def serialize_values(self) -> JSON: ...

    def serialize(self) -> JSON:
        return {
            "type": type(self).__name__,
            "values": self.serialize_values(),
            "target_profile": self.target_profile.serialize(),
        }


@dataclasses.dataclass
class OptionDecision(Generic[O]):
    option: Option[O]
    target: O


@dataclasses.dataclass
class SelectOptionDecisionPoint(DecisionPoint[OptionDecision]):
    options: list[Option]
    explanation: str

    def get_explanation(self) -> str:
        return self.explanation

    def serialize_payload(self) -> JSON:
        return {"options": [option.serialize() for option in self.options]}

    def parse_response(self, v: Any) -> OptionDecision:
        option = self.options[v["index"]]
        return OptionDecision(
            option=option, target=option.target_profile.parse_response(v["target"])
        )
