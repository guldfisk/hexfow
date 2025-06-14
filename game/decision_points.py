import dataclasses
from typing import Any, Mapping

from game.core import Unit
from game.decisions import DecisionPoint, JSON, SerializationContext


@dataclasses.dataclass
class SelectUnitDecisionPoint(DecisionPoint[Unit]):
    options: list[Unit]
    explanation: str

    def get_explanation(self) -> str:
        return self.explanation

    def serialize_payload(self, context: SerializationContext) -> JSON:
        return {
            "units": [{"id": context.id_map.get_id_for(unit)} for unit in self.options]
        }

    def parse_response(self, v: Mapping[str, Any]) -> Unit:
        return self.options[v["index"]]
