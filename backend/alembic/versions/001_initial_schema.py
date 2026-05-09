"""Initial baseline schema (squashed).

Revision ID: 001
Revises:
Create Date: 2026-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sector_type", sa.String(32), nullable=False, server_default="industry"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_sector_name"),
    )
    op.create_index("idx_sectors_type", "sectors", ["sector_type"])

    op.create_table(
        "sector_fund_flow_minute",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("ts", sa.DateTime, nullable=False),
        sa.Column("sector_id", sa.Integer, sa.ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("net_inflow_yi", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_date_slot_sector", "sector_fund_flow_minute", ["trade_date", "ts", "sector_id"])
    op.create_index("idx_date_sector_time", "sector_fund_flow_minute", ["trade_date", "sector_id", "ts"])
    op.create_index("idx_ts_sector", "sector_fund_flow_minute", ["ts", "sector_id"])

    if dialect_name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        # Timescale hypertable unique-index rule: PK must include partition key. Drop id-only PK.
        op.execute("ALTER TABLE sector_fund_flow_minute DROP CONSTRAINT IF EXISTS sector_fund_flow_minute_pkey")
        op.execute("CREATE INDEX IF NOT EXISTS idx_sector_fund_flow_minute_id ON sector_fund_flow_minute (id)")
        op.execute(
            """
            SELECT create_hypertable(
                'sector_fund_flow_minute',
                by_range('trade_date'),
                if_not_exists => TRUE,
                migrate_data => TRUE
            )
            """
        )
        op.execute(
            """
            ALTER TABLE sector_fund_flow_minute
            SET (
                timescaledb.compress,
                timescaledb.compress_segmentby = 'sector_id',
                timescaledb.compress_orderby = 'trade_date DESC,ts DESC'
            )
            """
        )
        op.execute(
            """
            SELECT add_compression_policy(
                'sector_fund_flow_minute',
                compress_after => INTERVAL '7 days',
                if_not_exists => TRUE
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("SELECT remove_compression_policy('sector_fund_flow_minute', if_exists => TRUE)")
        op.execute("ALTER TABLE sector_fund_flow_minute SET (timescaledb.compress = false)")
        op.execute("DROP INDEX IF EXISTS idx_sector_fund_flow_minute_id")

    op.drop_index("idx_ts_sector", "sector_fund_flow_minute")
    op.drop_index("idx_date_sector_time", "sector_fund_flow_minute")
    op.drop_constraint("uq_date_slot_sector", "sector_fund_flow_minute")
    op.drop_table("sector_fund_flow_minute")
    op.drop_index("idx_sectors_type", "sectors")
    op.drop_table("sectors")
