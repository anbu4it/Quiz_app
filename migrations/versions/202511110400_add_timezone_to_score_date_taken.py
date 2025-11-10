"""add timezone to score.date_taken

Revision ID: 202511110400
Revises: 3640e51cc979
Create Date: 2025-11-11 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '202511110400'
down_revision = '3640e51cc979'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Reinterpret existing naive timestamps as UTC, then convert to timestamptz
        op.execute("ALTER TABLE score ALTER COLUMN date_taken TYPE TIMESTAMP WITH TIME ZONE USING date_taken AT TIME ZONE 'UTC';")
    else:
        # SQLite: type alteration for timezone flag not impactful; ensure column exists
        with op.batch_alter_table('score') as batch_op:
            batch_op.alter_column('date_taken', type_=sa.DateTime(timezone=True), existing_nullable=False)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE score ALTER COLUMN date_taken TYPE TIMESTAMP WITHOUT TIME ZONE;")
    else:
        with op.batch_alter_table('score') as batch_op:
            batch_op.alter_column('date_taken', type_=sa.DateTime(timezone=False), existing_nullable=False)
