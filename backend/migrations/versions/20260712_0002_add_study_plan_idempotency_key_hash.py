"""add study plan idempotency key hash

Revision ID: 20260712_0002
Revises: 20260709_0001
Create Date: 2026-07-12
"""
from __future__ import annotations

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa

revision: str = "20260712_0002"
down_revision: str | None = "20260709_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("study_plans", sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True))
    _backfill_idempotency_key_hash()
    op.create_index(
        "uq_study_plans_user_course_idempotency_key_hash",
        "study_plans",
        ["user_id", "course_id", "idempotency_key_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_study_plans_user_course_idempotency_key_hash", table_name="study_plans")
    op.drop_column("study_plans", "idempotency_key_hash")


def _backfill_idempotency_key_hash() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("select id, parsed_config_json from study_plans where parsed_config_json is not null")
    ).mappings()
    for row in rows:
        key_hash = _idempotency_key_hash_from_config(row["parsed_config_json"])
        if key_hash:
            bind.execute(
                sa.text("update study_plans set idempotency_key_hash = :key_hash where id = :plan_id"),
                {"key_hash": key_hash, "plan_id": row["id"]},
            )


def _idempotency_key_hash_from_config(raw_config: object) -> str | None:
    config = raw_config
    if isinstance(raw_config, str):
        try:
            config = json.loads(raw_config)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw_config, (bytes, bytearray)):
        try:
            config = json.loads(raw_config.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    if not isinstance(config, dict):
        return None
    idempotency = config.get("idempotency")
    if not isinstance(idempotency, dict):
        return None
    key_hash = idempotency.get("key_hash")
    return key_hash if isinstance(key_hash, str) and key_hash else None