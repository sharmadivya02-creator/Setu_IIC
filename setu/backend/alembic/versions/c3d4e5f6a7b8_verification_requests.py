"""

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'verification_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('course_name', sa.String(length=120), nullable=True),
        sa.Column('evidence_url', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('review_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_verification_requests_student_id', 'verification_requests', ['student_id'])
    op.create_index('ix_verification_requests_skill_id', 'verification_requests', ['skill_id'])
    op.create_index('ix_verification_requests_status', 'verification_requests', ['status'])


def downgrade() -> None:
    op.drop_index('ix_verification_requests_status', table_name='verification_requests')
    op.drop_index('ix_verification_requests_skill_id', table_name='verification_requests')
    op.drop_index('ix_verification_requests_student_id', table_name='verification_requests')
    op.drop_table('verification_requests')