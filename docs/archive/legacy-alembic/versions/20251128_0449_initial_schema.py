"""initial schema

Revision ID: e442b08c1fe1
Revises: 
Create Date: 2025-11-28 04:49:02.994101+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e442b08c1fe1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema.

    Adds project scoping to categories. We first add the column as nullable,
    backfill it with a reasonable default (first project per tenant), then
    enforce NOT NULL and new constraints. This avoids integrity errors on
    existing rows.
    """
    # Add column nullable initially
    op.add_column("categories", sa.Column("project_id", sa.String(length=36), nullable=True))

    # Create FK early (nullable allowed)
    op.create_foreign_key(
        "fk_categories_project", "categories", "projects", ["project_id"], ["id"], ondelete="CASCADE"
    )

    # Backfill project_id: choose earliest created project for each tenant
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            WITH first_projects AS (
                SELECT DISTINCT ON (tenant_id) id, tenant_id
                FROM projects
                ORDER BY tenant_id, created_at
            )
            UPDATE categories c
            SET project_id = fp.id
            FROM first_projects fp
            WHERE c.project_id IS NULL AND fp.tenant_id = c.tenant_id;
            """
        )
    )

    # Enforce NOT NULL after backfill
    op.alter_column(
        "categories", "project_id", existing_type=sa.String(length=36), nullable=False
    )

    # Drop legacy tenant/name index & constraint if they existed
    try:
        op.drop_index("ix_categories_tenant_name", table_name="categories")
    except Exception:
        pass
    try:
        op.drop_constraint("uq_category_tenant_name", "categories", type_="unique")
    except Exception:
        pass

    # New indexes & unique constraints
    op.create_index(op.f("ix_categories_project_id"), "categories", ["project_id"], unique=False)
    op.create_index(
        "ix_categories_tenant_project", "categories", ["tenant_id", "project_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_category_project_name", "categories", ["tenant_id", "project_id", "name"]
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Reverse of upgrade
    try:
        op.drop_constraint("uq_category_project_name", "categories", type_="unique")
    except Exception:
        pass
    try:
        op.drop_index("ix_categories_tenant_project", table_name="categories")
    except Exception:
        pass
    try:
        op.drop_index(op.f("ix_categories_project_id"), table_name="categories")
    except Exception:
        pass
    try:
        op.drop_constraint("fk_categories_project", "categories", type_="foreignkey")
    except Exception:
        pass
    # Restore legacy constraints (best effort)
    op.create_unique_constraint("uq_category_tenant_name", "categories", ["tenant_id", "name"])
    op.create_index("ix_categories_tenant_name", "categories", ["tenant_id", "name"], unique=False)
    op.drop_column("categories", "project_id")
