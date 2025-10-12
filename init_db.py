from alembic import command
from alembic.config import Config

from model.engine import engine
from model.models import Base


def initialize_database() -> None:
    Base.metadata.create_all(engine)

    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")


if __name__ == "__main__":
    initialize_database()
