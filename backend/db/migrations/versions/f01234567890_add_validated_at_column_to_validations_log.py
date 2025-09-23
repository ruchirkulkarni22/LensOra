# File: backend/db/migrations/versions/f01234567890_add_validated_at_column_to_validations_log.py
"""add_validated_at_column_to_validations_log

Revision ID: f01234567890
Revises: e153e2875902
Create Date: 2025-09-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f01234567890'
down_revision = 'e153e2875902'
branch_labels = None
depends_on = None


def upgrade():
    # --- FLAWLESS FIX ---
    # This migration was adding a 'validated_at' column that a previous migration
    # (9940803aa6aa) already creates. After correcting other migration issues,
    # this file became redundant and caused a "DuplicateColumn" error.
    # We are neutralizing its actions by replacing the content with 'pass'.
    pass


def downgrade():
    # --- FLAWLESS FIX ---
    # The downgrade path is also neutralized to maintain consistency.
    pass
