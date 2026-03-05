"""add coding interview tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 14:57:48.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create coding_problems, test_cases, and code_submissions tables."""

    # --- coding_problems -------------------------------------------------
    op.create_table(
        'coding_problems',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(), nullable=False),
        sa.Column('starter_code', sa.JSON(), nullable=True),
        sa.Column('time_limit_sec', sa.Integer(), server_default='900', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id'),
    )

    # --- test_cases ------------------------------------------------------
    op.create_table(
        'test_cases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('problem_id', sa.Uuid(), nullable=False),
        sa.Column('input', sa.Text(), nullable=False),
        sa.Column('expected_output', sa.Text(), nullable=False),
        sa.Column('is_hidden', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['coding_problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- code_submissions ------------------------------------------------
    op.create_table(
        'code_submissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('problem_id', sa.Uuid(), nullable=False),
        sa.Column('interview_id', sa.Uuid(), nullable=False),
        sa.Column('candidate_id', sa.Uuid(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending', nullable=False),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('passed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['coding_problems.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Drop coding interview tables in reverse dependency order."""
    op.drop_table('code_submissions')
    op.drop_table('test_cases')
    op.drop_table('coding_problems')
