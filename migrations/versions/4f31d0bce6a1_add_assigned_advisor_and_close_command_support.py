"""add assigned advisor and close command support

Revision ID: 4f31d0bce6a1
Revises: 8b0c3e8bd5b7
Create Date: 2026-02-27 00:00:03.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f31d0bce6a1"
down_revision: Union[str, Sequence[str], None] = "8b0c3e8bd5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("conversations", sa.Column("assigned_advisor_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_assigned_advisor_id_advisors",
        "conversations",
        "advisors",
        ["assigned_advisor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_assigned_advisor_id", "conversations", ["assigned_advisor_id"], unique=False)

    op.drop_constraint("ck_conversations_status", "conversations", type_="check")
    op.create_check_constraint(
        "ck_conversations_status",
        "conversations",
        "status in ('active', 'closed')",
    )

    op.drop_constraint("ck_messages_sender_type", "messages", type_="check")
    op.create_check_constraint(
        "ck_messages_sender_type",
        "messages",
        "sender_type in ('user', 'advisor', 'assistant', 'system')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_messages_sender_type", "messages", type_="check")
    op.create_check_constraint(
        "ck_messages_sender_type",
        "messages",
        "sender_type in ('user', 'agent', 'assistant', 'system')",
    )

    op.drop_constraint("ck_conversations_status", "conversations", type_="check")
    op.create_check_constraint(
        "ck_conversations_status",
        "conversations",
        "status in ('active', 'closed', 'archived')",
    )

    op.drop_index("ix_conversations_assigned_advisor_id", table_name="conversations")
    op.drop_constraint("fk_conversations_assigned_advisor_id_advisors", "conversations", type_="foreignkey")
    op.drop_column("conversations", "assigned_advisor_id")
