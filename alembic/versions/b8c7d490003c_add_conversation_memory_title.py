"""add conversation memory_title

Revision ID: b8c7d490003c
Revises: 1078372ccdda
Create Date: 2026-05-12 11:15:12.146307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c7d490003c'
down_revision: Union[str, Sequence[str], None] = '1078372ccdda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation",
        sa.Column(
            "memory_title",
            sa.String(length=20),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("conversation", "memory_title", server_default=None)


def downgrade() -> None:
    op.drop_column("conversation", "memory_title")