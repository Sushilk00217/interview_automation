"""Add verification fields to candidate_profiles

Revision ID: add_verification_fields
Revises: add_job_description
Create Date: 2026-03-01 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_verification_fields'
down_revision: Union[str, None] = 'add_job_description'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add verification fields to candidate_profiles table."""
    op.add_column('candidate_profiles', 
                  sa.Column('face_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('candidate_profiles', 
                  sa.Column('voice_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('candidate_profiles', 
                  sa.Column('face_sample_url', sa.String(), nullable=True))
    op.add_column('candidate_profiles', 
                  sa.Column('video_sample_url', sa.String(), nullable=True))
    op.add_column('candidate_profiles', 
                  sa.Column('voice_sample_url', sa.String(), nullable=True))
    op.add_column('candidate_profiles', 
                  sa.Column('face_verification_id', sa.String(), nullable=True))
    op.add_column('candidate_profiles', 
                  sa.Column('voice_profile_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove verification fields from candidate_profiles table."""
    op.drop_column('candidate_profiles', 'voice_profile_id')
    op.drop_column('candidate_profiles', 'face_verification_id')
    op.drop_column('candidate_profiles', 'voice_sample_url')
    op.drop_column('candidate_profiles', 'video_sample_url')
    op.drop_column('candidate_profiles', 'face_sample_url')
    op.drop_column('candidate_profiles', 'voice_verified')
    op.drop_column('candidate_profiles', 'face_verified')
