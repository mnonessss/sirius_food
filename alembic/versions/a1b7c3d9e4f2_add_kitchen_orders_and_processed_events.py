"""add kitchen orders and processed events

Revision ID: a1b7c3d9e4f2
Revises: f2c8d4e1a9b3
Create Date: 2026-11-05 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b7c3d9e4f2"
down_revision: Union[str, None] = "f2c8d4e1a9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_table(
        "processed_events",
        sa.Column("id", sa.String(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
    op.drop_table("kitchen_orders")
