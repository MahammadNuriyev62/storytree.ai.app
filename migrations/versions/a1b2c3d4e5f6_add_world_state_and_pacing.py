"""add world state and pacing

Revision ID: a1b2c3d4e5f6
Revises: 3580072425da
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3580072425da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add persistent world-state + pacing columns."""
    op.add_column("story", sa.Column("initial_state", sqlite.JSON(), nullable=True))
    op.add_column("scene", sa.Column("state", sqlite.JSON(), nullable=True))
    op.add_column("scene", sa.Column("state_changes", sqlite.JSON(), nullable=True))
    op.add_column("scene", sa.Column("pacing", sa.String(), nullable=True))


def downgrade() -> None:
    """Drop the world-state + pacing columns."""
    op.drop_column("scene", "pacing")
    op.drop_column("scene", "state_changes")
    op.drop_column("scene", "state")
    op.drop_column("story", "initial_state")
