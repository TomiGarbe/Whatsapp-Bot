"""add human_status to conversations

Revision ID: b44a4f95a9e7
Revises: 0930cb0695fa
Create Date: 2026-02-26 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b44a4f95a9e7"
down_revision: Union[str, Sequence[str], None] = "0930cb0695fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("conversations", sa.Column("human_status", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_conversations_human_status",
        "conversations",
        "human_status in ('waiting', 'active') OR human_status IS NULL",
    )
    op.create_index("ix_conversations_human_status", "conversations", ["human_status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_conversations_human_status", table_name="conversations")
    op.drop_constraint("ck_conversations_human_status", "conversations", type_="check")
    op.drop_column("conversations", "human_status")
