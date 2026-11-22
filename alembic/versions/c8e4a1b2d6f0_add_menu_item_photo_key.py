"""add menu item photo key

Revision ID: c8e4a1b2d6f0
Revises: b7c1d2e3f4a5
Create Date: 2026-10-21 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8e4a1b2d6f0"
down_revision: Union[str, None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("photo_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "photo_key")
