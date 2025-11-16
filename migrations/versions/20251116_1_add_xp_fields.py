"""add xp fields to user and score

Revision ID: 20251116_1
Revises: 
Create Date: 2025-11-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251116_1'
down_revision = 'c0979da4221d'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to user
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('total_xp', sa.Integer(), nullable=False, server_default='0'))
    # Add columns to score
    with op.batch_alter_table('score') as batch_op:
        batch_op.add_column(sa.Column('difficulty', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('xp_earned', sa.Integer(), nullable=False, server_default='0'))

    # Backfill XP for existing rows assuming medium difficulty (10 xp per correct)
    conn = op.get_bind()
    try:
        conn.execute(sa.text("UPDATE score SET xp_earned = CASE WHEN xp_earned IS NULL OR xp_earned = 0 THEN (score * 10) ELSE xp_earned END"))
    except Exception:
        pass

    # Aggregate total_xp onto users (quote table name correctly per dialect)
    try:
        if conn.dialect.name == 'postgresql':
            conn.execute(sa.text('UPDATE "user" SET total_xp = COALESCE((SELECT SUM(s.xp_earned) FROM score s WHERE s.user_id = "user".id), 0)'))
        else:
            # SQLite accepts double-quoted identifiers as well
            conn.execute(sa.text('UPDATE "user" SET total_xp = COALESCE((SELECT SUM(s.xp_earned) FROM score s WHERE s.user_id = "user".id), 0)'))
    except Exception:
        pass

    # Drop server_default now that data is backfilled
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('total_xp', server_default=None)
    with op.batch_alter_table('score') as batch_op:
        batch_op.alter_column('xp_earned', server_default=None)


def downgrade():
    with op.batch_alter_table('score') as batch_op:
        batch_op.drop_column('xp_earned')
        batch_op.drop_column('difficulty')
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('total_xp')
