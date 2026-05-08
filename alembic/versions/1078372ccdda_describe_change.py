"""rename ok_flag / ok to tool_succeeded (align ORM)

Revision ID: 1078372ccdda
Revises: 3124fd0ba1ac
Create Date: 2026-05-08 08:13:14.126881

说明：autogenerate 曾生成「先 ADD NOT NULL 再 DROP」，在已有行时会报
NotNullViolation。此处改为 RENAME，数据不变。

conversation_messages.role 仍为 VARCHAR 存枚举值，与 native_enum=False 一致；
若将来需改库类型可单独开迁移。
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1078372ccdda"
down_revision: Union[str, Sequence[str], None] = "3124fd0ba1ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('ALTER TABLE agent_steps RENAME COLUMN ok_flag TO tool_succeeded')
    op.execute("ALTER TABLE events RENAME COLUMN ok TO tool_succeeded")


def downgrade() -> None:
    op.execute("ALTER TABLE agent_steps RENAME COLUMN tool_succeeded TO ok_flag")
    op.execute("ALTER TABLE events RENAME COLUMN tool_succeeded TO ok")
