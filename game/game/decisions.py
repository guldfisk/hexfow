import dataclasses
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, TypeAlias, Mapping
from uuid import uuid4

from bidict import bidict

from game.game.map.coordinates import CC
from game.game.player import Player


O = TypeVar("O")

JSON: TypeAlias = Mapping[str, Any]


# TODO where this shit?
class IDMap:

    def __init__(self):
        #         self.unit_positions: bidict[Unit, Hex] = bidict()
        self._ids: bidict[int, str] = bidict()
        self._objects: dict[int, object] = {}
        self._accessed: set[int] = set()

    def has_id(self, id_: str) -> bool:
        return id_ in self._ids.inverse

    def get_id_for(self, obj: Any) -> str:
        _id = id(obj)
        if _id not in self._ids:
            self._ids[_id] = str(uuid4())
            # TODO this is just for debugging
            self._objects[_id] = obj
        self._accessed.add(_id)
        return self._ids[_id]

    def get_object_for(self, id_: str) -> object:
        return self._objects[self._ids.inverse[id_]]

    def prune(self) -> None:
        self._ids = bidict({k: v for k, v in self._ids.items() if k in self._accessed})
        self._accessed = set()


@dataclasses.dataclass
class SerializationContext:
    player: Player
    id_map: IDMap
    last_hex_states: dict[CC : dict[str, Any]] | None


# TODO this should just be a protocol?
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
