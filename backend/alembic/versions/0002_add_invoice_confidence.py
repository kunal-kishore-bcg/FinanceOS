"""add confidence column to invoices

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("confidence", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "confidence")
