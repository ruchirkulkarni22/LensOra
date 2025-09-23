# File: backend/db/migrations/versions/f01234567890_add_validated_at_column_to_validations_log.py
"""add_validated_at_column_to_validations_log

Revision ID: f01234567890
Revises: 9940803aa6aa
Create Date: 2025-09-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f01234567890'
down_revision = 'e153e2875902'  # This should be the current head revision
branch_labels = None
depends_on = None


def upgrade():
    # Add the validated_at column to validations_log table with a default value
    op.add_column('validations_log', 
                  sa.Column('validated_at', sa.DateTime, server_default=sa.func.now()))


def downgrade():
    # Drop the validated_at column
    op.drop_column('validations_log', 'validated_at')