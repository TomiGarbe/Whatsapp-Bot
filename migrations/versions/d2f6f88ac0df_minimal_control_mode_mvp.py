"""minimal control mode mvp

Revision ID: d2f6f88ac0df
Revises: 06b0076550c6
Create Date: 2026-02-27 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d2f6f88ac0df"
down_revision: Union[str, Sequence[str], None] = "06b0076550c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS ck_conversations_human_consistency")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS ck_conversations_human_status")
    op.execute("DROP INDEX IF EXISTS ix_conversations_human_queue")
    op.drop_column("conversations", "assigned_agent_id")
    op.drop_column("conversations", "human_status")
    op.drop_table("conversation_transfers")
    op.drop_column("messages", "agent_id")
    op.drop_column("requests", "validated_by_agent_id")
    op.drop_table("agents")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role in ('agent', 'admin', 'supervisor')", name="ck_agents_role"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "email", name="uq_agents_business_email"),
    )
    op.create_index("ix_agents_business_id", "agents", ["business_id"], unique=False)
    op.create_index("ix_agents_is_active", "agents", ["is_active"], unique=False)

    op.add_column("messages", sa.Column("agent_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_messages_agent_id_agents",
        "messages",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("requests", sa.Column("validated_by_agent_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_requests_validated_by_agent_id_agents",
        "requests",
        "agents",
        ["validated_by_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "conversation_transfers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("from_agent_id", sa.UUID(), nullable=True),
        sa.Column("to_agent_id", sa.UUID(), nullable=True),
        sa.Column("from_mode", sa.String(length=20), nullable=False),
        sa.Column("to_mode", sa.String(length=20), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("transfer_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("from_mode in ('ai', 'human')", name="ck_conversation_transfers_from_mode"),
        sa.CheckConstraint("status in ('pending', 'accepted', 'rejected', 'cancelled')", name="ck_conversation_transfers_status"),
        sa.CheckConstraint("to_mode in ('ai', 'human')", name="ck_conversation_transfers_to_mode"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_transfers_conversation_id",
        "conversation_transfers",
        ["conversation_id"],
        unique=False,
    )
    op.create_index("ix_conversation_transfers_status", "conversation_transfers", ["status"], unique=False)

    op.add_column("conversations", sa.Column("human_status", sa.String(length=20), nullable=True))
    op.add_column("conversations", sa.Column("assigned_agent_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_assigned_agent_id_agents",
        "conversations",
        "agents",
        ["assigned_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_conversations_human_status",
        "conversations",
        "human_status in ('waiting', 'active') OR human_status IS NULL",
    )
    op.create_index(
        "ix_conversations_human_queue",
        "conversations",
        ["business_id", "human_status", "started_at"],
        unique=False,
    )
