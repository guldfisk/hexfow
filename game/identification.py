from typing import Any
from uuid import uuid4

from bidict import bidict


class IDMap:
    def __init__(self):
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
