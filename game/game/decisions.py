import dataclasses
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, TypeAlias, Mapping
from uuid import uuid4

from game.game.player import Player


O = TypeVar("O")

JSON: TypeAlias = Mapping[str, Any]


# TODO where this shit?
class IDMap:

    def __init__(self):
        self._ids: dict[int, str] = {}
        self._accessed: set[int] = set()

    def get_id_for(self, obj: Any) -> str:
        _id = id(obj)
        if _id not in self._ids:
            self._ids[_id] = str(uuid4())
        self._accessed.add(_id)
        return self._ids[_id]

    def prune(self) -> None:
        self._ids = {k: v for k, v in self._ids if k in self._accessed}
        self._accessed = set()


@dataclasses.dataclass
class SerializationContext:
    player: Player
    id_map: IDMap


class Serializable(ABC):

    @abstractmethod
    def serialize(self, context: SerializationContext) -> JSON: ...


class DecisionPoint(Serializable, Generic[O]):

    @abstractmethod
    def get_explanation(self) -> str: ...

    @abstractmethod
    def serialize_payload(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "explanation": self.get_explanation(),
            "type": self.__class__.__name__,
            "payload": self.serialize_payload(context),
        }

    @abstractmethod
    def parse_response(self, v: Any) -> O: ...


class TargetProfile(ABC, Generic[O]):
    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {"type": type(self).__name__, "values": self.serialize_values(context)}

    @abstractmethod
    def parse_response(self, v: Any) -> O: ...


class NoTarget(TargetProfile[None]):

    def serialize_values(self, context: SerializationContext) -> JSON:
        return {}

    def parse_response(self, v: Any) -> None:
        return None


@dataclasses.dataclass(kw_only=True)
class Option(ABC, Generic[O]):
    target_profile: TargetProfile[O]

    @abstractmethod
    def serialize_values(self, context: SerializationContext) -> JSON: ...

    def serialize(self, context: SerializationContext) -> JSON:
        return {
            "type": type(self).__name__,
            "values": self.serialize_values(context),
            "target_profile": self.target_profile.serialize(context),
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

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {"options": [option.serialize(context) for option in self.options]}

    def parse_response(self, v: Any) -> OptionDecision:
        option = self.options[v["index"]]
        return OptionDecision(
            option=option, target=option.target_profile.parse_response(v["target"])
        )
