"""Add description to expenses.

Revision ID: 9c7a2d4e6f81
Revises: 4f8c2d1a9b7e
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa


revision = "9c7a2d4e6f81"
down_revision = "4f8c2d1a9b7e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("expenses", sa.Column("description", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("expenses", "description")
