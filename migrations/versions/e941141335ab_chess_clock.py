from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e941141335ab"
down_revision: str | Sequence[str] | None = "9980b0df2439"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("game", sa.Column("time_bank", sa.Float(), nullable=True))
    op.add_column("game", sa.Column("time_grace", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("game", "time_grace")
    op.drop_column("game", "time_bank")
