"""create superstore_sales table

Revision ID: 0001
Revises:
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "superstore_sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ship_mode", sa.String(length=50), nullable=False),
        sa.Column("segment", sa.String(length=50), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("region", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("sub_category", sa.String(length=100), nullable=False),
        sa.Column("sales", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("discount", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("profit", sa.Numeric(precision=12, scale=4), nullable=False),
    )
    op.create_index("ix_superstore_sales_segment", "superstore_sales", ["segment"])
    op.create_index("ix_superstore_sales_city", "superstore_sales", ["city"])
    op.create_index("ix_superstore_sales_state", "superstore_sales", ["state"])
    op.create_index("ix_superstore_sales_region", "superstore_sales", ["region"])
    op.create_index("ix_superstore_sales_category", "superstore_sales", ["category"])
    op.create_index("ix_superstore_sales_sub_category", "superstore_sales", ["sub_category"])


def downgrade() -> None:
    op.drop_table("superstore_sales")
