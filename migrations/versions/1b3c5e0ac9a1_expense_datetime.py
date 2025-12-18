"""Convert expense_date to datetime with timezone support.

- Alter expenses.expense_date from DATE to TIMESTAMP.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1b3c5e0ac9a1"
down_revision = "e442b08c1fe1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "expenses",
        "expense_date",
        existing_type=sa.DATE(),
        type_=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "expenses",
        "expense_date",
        existing_type=sa.DateTime(),
        type_=sa.DATE(),
        existing_nullable=False,
    )
