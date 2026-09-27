"""merge heads

Revision ID: d993f2781534
Revises: b9d0e2f4a6c8, d3f8a1c6b9e2
Create Date: 2026-09-27 07:54:42.904121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd993f2781534'
down_revision: Union[str, Sequence[str], None] = ('b9d0e2f4a6c8', 'd3f8a1c6b9e2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
