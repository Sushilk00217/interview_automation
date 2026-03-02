"""Add resume_text to candidate_profiles

Revision ID: add_resume_text
Revises: add_verification_fields
Create Date: 2026-03-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_resume_text'
down_revision: Union[str, None] = 'add_verification_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add resume_text column to candidate_profiles table."""
    op.add_column('candidate_profiles', 
                  sa.Column('resume_text', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove resume_text column from candidate_profiles table."""
    op.drop_column('candidate_profiles', 'resume_text')
