"""add advisors table

Revision ID: 8b0c3e8bd5b7
Revises: d2f6f88ac0df
Create Date: 2026-02-27 00:00:02.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b0c3e8bd5b7"
down_revision: Union[str, Sequence[str], None] = "d2f6f88ac0df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "advisors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_advisors_business_id", "advisors", ["business_id"], unique=False)
    op.create_index("ix_advisors_is_active", "advisors", ["is_active"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_advisors_is_active", table_name="advisors")
    op.drop_index("ix_advisors_business_id", table_name="advisors")
    op.drop_table("advisors")
