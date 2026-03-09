"""Add DRAFT status to InterviewStatus

Revision ID: 6f15ea94e0a8
Revises: 67cf7f0cd608
Create Date: 2026-03-09 21:59:26.027204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f15ea94e0a8'
down_revision: Union[str, Sequence[str], None] = '67cf7f0cd608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'DRAFT' to interviewstatus enum
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE interviewstatus ADD VALUE 'DRAFT'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL doesn't support removing a value from an enum easily.
    pass
