"""add menu categories

Revision ID: b7c1d2e3f4a5
Revises: aeb7f013e18a
Create Date: 2026-10-19 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, None] = "aeb7f013e18a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
    )
    op.create_index("ix_categories_id", "categories", ["id"])

    op.add_column("menu_items", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_menu_items_category_id",
        "menu_items",
        "categories",
        ["category_id"],
        ["id"],
    )

    op.bulk_insert(
        categories,
        [{"name": "Супы"}, {"name": "Горячее"}, {"name": "Напитки"}],
    )


def downgrade() -> None:
    op.drop_constraint("fk_menu_items_category_id", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "category_id")
    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")
