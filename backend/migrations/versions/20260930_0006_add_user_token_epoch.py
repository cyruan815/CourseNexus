"""add user token_epoch for login revocation

Revision ID: 20260930_0006
Revises: 20260715_0005
Create Date: 2026-09-30
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260930_0006"
down_revision: str | None = "20260715_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 默认 0 与签发时 payload 中 epoch 缺失（历史 token）的兜底语义一致：
    # 存量登录态在迁移后继续有效，直到该用户修改密码递增 epoch。
    op.add_column(
        "users",
        sa.Column("token_epoch", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_epoch")
