from typing import Sequence


revision: str = "a22718c8515f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None: ...


def downgrade() -> None: ...
