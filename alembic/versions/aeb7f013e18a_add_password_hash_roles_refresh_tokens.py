"""add password_hash, roles, refresh_tokens

Revision ID: aeb7f013e18a
Revises: 3e4d017b561a
Create Date: 2026-09-30 17:13:32.197094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aeb7f013e18a'
down_revision: Union[str, Sequence[str], None] = '3e4d017b561a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Создаём таблицу ролей.
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
    )

    # Добавляем колонки в users. Пока nullable=True — заполним ниже.
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_role", "users", "roles", ["role_id"], ["id"])

    # Создаём таблицу refresh-токенов.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("token_hash", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default="false"),
    )

    # Заполняем роли.
    op.execute(
        "INSERT INTO roles (name) VALUES ('student'), ('cook'), ('courier'), ('admin')"
    )
    # Назначаем всем существующим пользователям роль student.
    op.execute(
        "UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'student')"
    )
    # У старых строк нет пароля. Кладём недействительный для входа bcrypt-хеш,
    # иначе NOT NULL упадёт на уже существующих пользователях.
    op.execute(
        "UPDATE users SET password_hash = "
        "'$2b$12$.hSZeDaDQ0XumF.PfATxzu9cMhmexv5dr2jcjx5kZNrwGmM7iJE.K' "
        "WHERE password_hash IS NULL"
    )

    # Теперь можно сделать колонки обязательными.
    op.alter_column("users", "role_id", nullable=False)
    op.alter_column("users", "password_hash", nullable=False)


def downgrade():
    op.drop_table("refresh_tokens")
    op.drop_constraint("fk_users_role", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_column("users", "password_hash")
    op.drop_table("roles")
