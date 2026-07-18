"""Add canonical snapshot-series identity and provider request provenance.

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import date
from typing import Any

from alembic import op
from alembic.util.exc import CommandError
import sqlalchemy as sa

revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SERIES_SCHEMA = "aquantai.snapshot-series.v1"


def upgrade() -> None:
    op.add_column("ingestion_runs", sa.Column("series_key", sa.String(length=64), nullable=True))
    op.add_column("ingestion_runs", sa.Column("series_identity", sa.JSON(), nullable=True))
    op.add_column("ingestion_runs", sa.Column("provider_request_metadata", sa.JSON(), nullable=True))
    op.add_column("ingestion_runs", sa.Column("adapter_version", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    ingestion_runs = sa.table(
        "ingestion_runs",
        sa.column("id", sa.BigInteger()),
        sa.column("provider", sa.String()),
        sa.column("dataset", sa.String()),
        sa.column("requested_start_date", sa.Date()),
        sa.column("requested_end_date", sa.Date()),
        sa.column("requested_scope", sa.JSON()),
        sa.column("snapshot_mode", sa.String()),
        sa.column("contract_version", sa.String()),
        sa.column("series_key", sa.String()),
        sa.column("series_identity", sa.JSON()),
        sa.column("provider_request_metadata", sa.JSON()),
        sa.column("adapter_version", sa.String()),
    )
    daily_price = sa.table(
        "daily_price",
        sa.column("ingestion_run_id", sa.BigInteger()),
        sa.column("adjust_type", sa.String()),
    )

    rows = connection.execute(sa.select(ingestion_runs)).mappings().all()
    for row in rows:
        adjust_types = sorted(
            value or ""
            for value in connection.execute(
                sa.select(sa.distinct(daily_price.c.adjust_type)).where(
                    daily_price.c.ingestion_run_id == row["id"]
                )
            ).scalars()
        )
        scope = dict(row["requested_scope"] or {})
        adjust_type = _legacy_adjust_type(adjust_types, scope)
        identity = _canonical_identity(row, scope, adjust_type)
        connection.execute(
            ingestion_runs.update()
            .where(ingestion_runs.c.id == row["id"])
            .values(
                series_key=_series_key(identity),
                series_identity=identity,
                provider_request_metadata={
                    "migration_backfill": revision,
                    "network_access": False,
                },
                adapter_version="v0.3a-backfill",
            )
        )

    op.alter_column("ingestion_runs", "series_key", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("ingestion_runs", "series_identity", existing_type=sa.JSON(), nullable=False)
    op.alter_column("ingestion_runs", "provider_request_metadata", existing_type=sa.JSON(), nullable=False)
    op.alter_column("ingestion_runs", "adapter_version", existing_type=sa.String(length=64), nullable=False)
    op.create_check_constraint(
        "ck_ingestion_runs_series_key_length",
        "ingestion_runs",
        "length(series_key) = 64",
    )
    op.drop_index("uq_ingestion_runs_successful_batch", table_name="ingestion_runs")
    op.create_index(
        "uq_ingestion_runs_successful_batch",
        "ingestion_runs",
        ["batch_identifier", "series_key"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
        sqlite_where=sa.text("status = 'succeeded'"),
    )
    op.create_index(
        "ix_ingestion_runs_series_cutoff",
        "ingestion_runs",
        ["series_key", "information_cutoff_date", "completed_at", "id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT batch_identifier, COUNT(*) AS successful_series_count
            FROM ingestion_runs
            WHERE status = 'succeeded'
            GROUP BY batch_identifier
            HAVING COUNT(*) > 1
            ORDER BY batch_identifier
            LIMIT 1
            """
        )
    ).mappings().first()
    if duplicate is not None:
        raise CommandError(
            "Cannot downgrade revision 20260718_0002 without losing valid multi-series audit history: "
            f"batch {duplicate['batch_identifier']} has "
            f"{duplicate['successful_series_count']} successful series. No schema changes were applied. "
            "Keep this revision installed; this migration will not delete, merge, or overwrite ingestion runs."
        )
    op.drop_index("ix_ingestion_runs_series_cutoff", table_name="ingestion_runs")
    op.drop_index("uq_ingestion_runs_successful_batch", table_name="ingestion_runs")
    op.create_index(
        "uq_ingestion_runs_successful_batch",
        "ingestion_runs",
        ["batch_identifier"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
        sqlite_where=sa.text("status = 'succeeded'"),
    )
    op.drop_constraint("ck_ingestion_runs_series_key_length", "ingestion_runs", type_="check")
    op.drop_column("ingestion_runs", "adapter_version")
    op.drop_column("ingestion_runs", "provider_request_metadata")
    op.drop_column("ingestion_runs", "series_identity")
    op.drop_column("ingestion_runs", "series_key")


def _legacy_adjust_type(adjust_types: list[str], scope: dict[str, Any]) -> str:
    if len(adjust_types) == 1:
        return adjust_types[0]
    if not adjust_types:
        return str(scope.get("adjust_type", "")).strip()
    return "mixed:" + ",".join(adjust_types)


def _canonical_identity(row: Any, scope: dict[str, Any], adjust_type: str) -> dict[str, Any]:
    return {
        "series_schema": SERIES_SCHEMA,
        "provider": str(row["provider"]).strip(),
        "dataset": str(row["dataset"]).strip(),
        "contract_version": str(row["contract_version"]).strip(),
        "datasets": sorted(str(value).strip() for value in scope.get("datasets", [])),
        "stock_codes": sorted(str(value).strip() for value in scope.get("stock_codes", [])),
        "requested_start_date": _compact_date(row["requested_start_date"]),
        "requested_end_date": _compact_date(row["requested_end_date"]),
        "adjust_type": adjust_type,
        "snapshot_mode": str(row["snapshot_mode"]).strip(),
        "stock_code_semantics": str(scope.get("stock_code_semantics", "exact")).strip(),
        "compatibility_parameters": {},
    }


def _compact_date(value: Any) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    return str(value).replace("-", "")


def _series_key(identity: dict[str, Any]) -> str:
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
