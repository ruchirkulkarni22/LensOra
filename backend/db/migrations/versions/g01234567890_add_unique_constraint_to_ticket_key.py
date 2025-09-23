"""add unique constraint to ticket_key in validations_log table

Revision ID: g01234567890
Revises: f01234567890
Create Date: 2024-09-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g01234567890'
down_revision = 'f01234567890'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add a unique constraint to ticket_key in validations_log table to ensure
    we only have one status per ticket at a time. This supports the stateful
    tracking of tickets.
    """
    # First, we need to clean up any duplicate entries that might exist
    op.execute("""
        DELETE FROM validations_log
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                ROW_NUMBER() OVER (PARTITION BY ticket_key ORDER BY validated_at DESC) as rnum
                FROM validations_log
            ) t
            WHERE t.rnum > 1
        )
    """)

    # Now add the unique constraint
    op.create_unique_constraint('uq_validations_log_ticket_key', 'validations_log', ['ticket_key'])


def downgrade():
    """
    Remove the unique constraint from ticket_key in validations_log table.
    """
    op.drop_constraint('uq_validations_log_ticket_key', 'validations_log', type_='unique')