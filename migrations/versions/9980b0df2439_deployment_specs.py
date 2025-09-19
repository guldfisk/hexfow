from typing import Sequence

from alembic import op


revision: str = "9980b0df2439"
down_revision: str | Sequence[str] | None = "8efbb2a541a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        r"""
        update map set
          scenario = jsonb_insert(
            jsonb_insert(scenario, '{to_points}', '24'::jsonb),
            '{deployment_spec}',
            '{"max_army_units"\:20,"max_army_points"\:120,"max_deployment_units"\:12,"max_deployment_points"\:70}'::jsonb
          );
        """
    )


def downgrade() -> None: ...
