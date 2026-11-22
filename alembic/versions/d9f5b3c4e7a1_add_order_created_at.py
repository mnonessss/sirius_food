"""add order created_at

Revision ID: d9f5b3c4e7a1
Revises: c8e4a1b2d6f0
Create Date: 2026-10-22 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f5b3c4e7a1"
down_revision: Union[str, None] = "c8e4a1b2d6f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("orders", "created_at")
