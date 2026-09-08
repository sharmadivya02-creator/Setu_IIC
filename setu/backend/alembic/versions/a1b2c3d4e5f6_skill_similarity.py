from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f743af429963'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'skill_similarity',
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('related_skill_id', sa.Integer(), nullable=False),
        sa.Column('similarity', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('skill_id', 'related_skill_id'),
    )
   
    op.create_index('ix_skill_similarity_skill_id', 'skill_similarity', ['skill_id'])


def downgrade() -> None:
    op.drop_index('ix_skill_similarity_skill_id', table_name='skill_similarity')
    op.drop_table('skill_similarity')
