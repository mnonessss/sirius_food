"""drop menu item photo key

Revision ID: f2c8d4e1a9b3
Revises: d9f5b3c4e7a1
Create Date: 2026-11-02 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c8d4e1a9b3"
down_revision: Union[str, None] = "d9f5b3c4e7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("menu_items", "photo_key")


def downgrade() -> None:
    op.add_column("menu_items", sa.Column("photo_key", sa.String(), nullable=True))
