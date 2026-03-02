"""create_questions_table

Revision ID: 5e59a010ec1e
Revises: b87cc7600014
Create Date: 2026-03-02 14:54:24.088791

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '5e59a010ec1e'
down_revision: Union[str, Sequence[str], None] = 'b87cc7600014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create questions table
    op.create_table('questions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('PYTHON', 'SQL', 'MACHINE_LEARNING', 'DATA_STRUCTURES', 'SYSTEM_DESIGN', 'STATISTICS', name='categoryenum'), nullable=False),
        sa.Column('difficulty', sa.Enum('EASY', 'MEDIUM', 'HARD', name='difficultyenum'), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Add question_id as nullable first
    op.add_column('template_questions', sa.Column('question_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_template_questions_question_id', 'template_questions', 'questions', ['question_id'], ['id'], ondelete='CASCADE')

    # 3. Data Migration
    connection = op.get_bind()
    
    # Query existing template questions using raw SQL
    try:
        # Use text() for SQL execution in SQLAlchemy 2.0 style
        rows = connection.execute(sa.text("SELECT id, question_text FROM template_questions")).fetchall()
        
        for row in rows:
            new_q_id = uuid.uuid4()
            # Insert into questions using raw SQL to handle Enum types simply
            # We use Postgres cast syntax to be explicit if necessary, but label strings usually work
            connection.execute(
                sa.text(
                    "INSERT INTO questions (id, text, category, difficulty, is_active, created_at, updated_at) "
                    "VALUES (:id, :text, :category, :difficulty, 'true', now(), now())"
                ),
                {
                    "id": new_q_id,
                    "text": row[1],
                    "category": 'PYTHON',
                    "difficulty": 'MEDIUM'
                }
            )
            # Update template_questions to link to the new question
            connection.execute(
                sa.text("UPDATE template_questions SET question_id = :q_id WHERE id = :tq_id"),
                {"q_id": new_q_id, "tq_id": row[0]}
            )
    except Exception as e:
        print(f"Data migration warning: {e}")
        # We might want to handle cases where the table is empty or column doesn't exist
        pass

    # 4. Finalize schema
    op.alter_column('template_questions', 'question_id', nullable=False)
    op.drop_column('template_questions', 'question_text')


def downgrade() -> None:
    # 1. Add question_text column back
    op.add_column('template_questions', sa.Column('question_text', sa.String(), nullable=True))

    # 2. Restore data
    connection = op.get_bind()
    try:
        rows = connection.execute(sa.text(
            "SELECT tq.id, q.text FROM template_questions tq JOIN questions q ON tq.question_id = q.id"
        )).fetchall()
        
        for row in rows:
            connection.execute(
                sa.text("UPDATE template_questions SET question_text = :text WHERE id = :id"),
                {"text": row[1], "id": row[0]}
            )
    except Exception as e:
        print(f"Downgrade data migration warning: {e}")
        pass

    # 3. Cleanup
    op.alter_column('template_questions', 'question_text', nullable=False)
    op.drop_constraint('fk_template_questions_question_id', 'template_questions', type_='foreignkey')
    op.drop_column('template_questions', 'question_id')
    op.drop_table('questions')
    
    # Explicitly drop enums to clean up in Postgres
    op.execute('DROP TYPE categoryenum')
    op.execute('DROP TYPE difficultyenum')
