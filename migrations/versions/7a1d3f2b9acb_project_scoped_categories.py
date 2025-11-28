"""Project-scoped categories.

Add project_id to categories, enforce per-project uniqueness, and backfill existing rows.
"""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = "7a1d3f2b9acb"
down_revision = "a0d0062df1c0"
branch_labels = None
depends_on = None


def upgrade():
    # Add project_id column
    op.add_column(
        "categories",
        sa.Column("project_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_categories_project_id_projects",
        "categories",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Drop tenant-level name index to allow per-project reuse
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_index("ix_categories_tenant_name")

    # Backfill project_id using the oldest project per tenant; create a default project if none exist
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, tenant_id FROM categories WHERE project_id IS NULL")).fetchall()
    tenants_missing_project = set()

    for row in rows:
        project_id = conn.execute(
            sa.text(
                "SELECT id FROM projects WHERE tenant_id = :tenant_id AND is_deleted = 0 "
                "ORDER BY created_at ASC LIMIT 1"
            ),
            {"tenant_id": row.tenant_id},
        ).scalar()
        if not project_id:
            tenants_missing_project.add(row.tenant_id)
            continue
        conn.execute(
            sa.text("UPDATE categories SET project_id = :project_id WHERE id = :id"),
            {"project_id": project_id, "id": row.id},
        )

    # Create a default project per tenant that had categories but no projects
    for tenant_id in tenants_missing_project:
        project_id = str(uuid4())
        conn.execute(
            sa.text(
                """
                INSERT INTO projects (id, tenant_id, name, description, starting_budget, projected_estimate, currency, status, is_deleted, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :description, :starting_budget, :projected_estimate, :currency, :status, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": project_id,
                "tenant_id": tenant_id,
                "name": "General",
                "description": "Auto-created during category migration",
                "starting_budget": 0,
                "projected_estimate": 0,
                "currency": "USD",
                "status": "active",
            },
        )
        conn.execute(
            sa.text("UPDATE categories SET project_id = :project_id WHERE tenant_id = :tenant_id AND project_id IS NULL"),
            {"project_id": project_id, "tenant_id": tenant_id},
        )

    # Enforce non-null and new indexes
    with op.batch_alter_table("categories") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index("ix_categories_tenant_project", ["tenant_id", "project_id"], unique=False)
        batch_op.create_unique_constraint("uq_category_project_name", ["tenant_id", "project_id", "name"])


def downgrade():
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_constraint("uq_category_project_name", type_="unique")
        batch_op.drop_index("ix_categories_tenant_project")
        batch_op.alter_column("project_id", existing_type=sa.String(length=36), nullable=True)

    op.drop_constraint("fk_categories_project_id_projects", "categories", type_="foreignkey")
    op.drop_column("categories", "project_id")

    with op.batch_alter_table("categories") as batch_op:
        batch_op.create_index("ix_categories_tenant_name", ["tenant_id", "name"], unique=False)
