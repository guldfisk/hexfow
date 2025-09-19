from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeAlias
from uuid import UUID

from sqlalchemy import ForeignKey, MetaData, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from model.values import GameStatus


JsonDict: TypeAlias = dict[str, Any]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_N_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {str: Text(), JsonDict: JSONB}


class CreatedMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class UUIDPKMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class IntPKMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class Map(Base, CreatedMixin, IntPKMixin):
    __tablename__ = "map"

    name: Mapped[str] = mapped_column(unique=True)
    scenario: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Game(Base, CreatedMixin, IntPKMixin):
    __tablename__ = "game"

    status: Mapped[str] = mapped_column(default=GameStatus.PENDING)
    game_type: Mapped[str]
    with_fow: Mapped[bool]
    custom_armies: Mapped[bool]
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB)

    seats: Mapped[list[Seat]] = relationship(back_populates="game")


class Seat(Base, UUIDPKMixin):
    __tablename__ = "seat"
    __table_args__ = (
        UniqueConstraint("game_id", "position"),
        UniqueConstraint("game_id", "player_name"),
    )

    game_id: Mapped[int] = mapped_column(ForeignKey(Game.id))
    game: Mapped[Game] = relationship(back_populates="seats")
    position: Mapped[int]
    player_name: Mapped[str]


def create_models():
    from model.engine import engine

    Base.metadata.create_all(engine)
