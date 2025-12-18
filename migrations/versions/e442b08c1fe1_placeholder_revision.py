"""Placeholder to align alembic history.

This revision exists to satisfy environments that reference e442b08c1fe1.
No schema changes are applied.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e442b08c1fe1"
down_revision = "7a1d3f2b9acb"
branch_labels = None
depends_on = None


def upgrade():
    """No-op upgrade to align migration history."""
    pass


def downgrade():
    """No-op downgrade to align migration history."""
    pass
