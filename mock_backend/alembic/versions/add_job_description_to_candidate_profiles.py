"""Add job_description to candidate_profiles

Revision ID: add_job_description
Revises: 3b7aaaf47898
Create Date: 2026-03-01 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_job_description'
down_revision: Union[str, None] = '3b7aaaf47898'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add job_description column to candidate_profiles table."""
    op.add_column('candidate_profiles', 
                  sa.Column('job_description', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove job_description column from candidate_profiles table."""
    op.drop_column('candidate_profiles', 'job_description')
