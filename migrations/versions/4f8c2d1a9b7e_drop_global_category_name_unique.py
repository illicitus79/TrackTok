"""Drop legacy tenant-wide category name uniqueness.

Categories are scoped to projects. The same category name may be reused across
different projects in the same tenant, while remaining unique within one
project.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4f8c2d1a9b7e"
down_revision = "1b3c5e0ac9a1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS uq_category_tenant_name")
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_category_project_name'
                ) THEN
                    ALTER TABLE categories
                    ADD CONSTRAINT uq_category_project_name
                    UNIQUE (tenant_id, project_id, name);
                END IF;
            END
            $$;
            """
        )
        return

    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints("categories")
    }
    with op.batch_alter_table("categories") as batch_op:
        if "uq_category_tenant_name" in constraints:
            batch_op.drop_constraint("uq_category_tenant_name", type_="unique")
        if "uq_category_project_name" not in constraints:
            batch_op.create_unique_constraint(
                "uq_category_project_name",
                ["tenant_id", "project_id", "name"],
            )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS uq_category_project_name")
        op.create_unique_constraint(
            "uq_category_tenant_name",
            "categories",
            ["tenant_id", "name"],
        )
        return

    constraints = {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints("categories")
    }
    with op.batch_alter_table("categories") as batch_op:
        if "uq_category_project_name" in constraints:
            batch_op.drop_constraint("uq_category_project_name", type_="unique")
        if "uq_category_tenant_name" not in constraints:
            batch_op.create_unique_constraint("uq_category_tenant_name", ["tenant_id", "name"])
