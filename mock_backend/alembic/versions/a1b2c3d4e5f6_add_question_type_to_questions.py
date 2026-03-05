"""add question_type to questions

Revision ID: a1b2c3d4e5f6
Revises: 66ed4b635ed8
Create Date: 2026-03-05 14:52:46.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '66ed4b635ed8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enum type
questiontype_enum = sa.Enum('technical', 'behavioral', 'coding', name='questiontype')


def upgrade() -> None:
    """Add question_type enum and column to questions table."""
    # Create the enum type in the database
    questiontype_enum.create(op.get_bind(), checkfirst=True)

    # Add question_type column to questions table
    op.add_column(
        'questions',
        sa.Column(
            'question_type',
            sa.Enum('technical', 'behavioral', 'coding', name='questiontype'),
            nullable=False,
            server_default='technical'
        )
    )


def downgrade() -> None:
    """Remove question_type column and enum from questions table."""
    # Drop the column first
    op.drop_column('questions', 'question_type')

    # Drop the enum type
    questiontype_enum.drop(op.get_bind(), checkfirst=True)
