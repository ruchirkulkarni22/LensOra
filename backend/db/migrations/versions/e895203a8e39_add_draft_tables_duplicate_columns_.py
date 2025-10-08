# File: backend/db/migrations/script.py.mako
"""add draft tables, duplicate columns, ticket events

Revision ID: e895203a8e39
Revises: i10000000002
Create Date: 2025-10-07 09:52:22.181756

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e895203a8e39"
down_revision = "i10000000002"
branch_labels = None
depends_on = None

def _column_missing(inspector, table, column):
    return column not in [c["name"] for c in inspector.get_columns(table)]

def _table_missing(inspector, table):
    return table not in inspector.get_table_names()

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # validations_log: priority
    if _column_missing(inspector, "validations_log", "priority"):
        op.add_column("validations_log", sa.Column("priority", sa.String(length=4), nullable=True))

    # validations_log: duplicate_of
    if _column_missing(inspector, "validations_log", "duplicate_of"):
        op.add_column("validations_log", sa.Column("duplicate_of", sa.String(), nullable=True))

    # resolution_log: draft_id
    if _column_missing(inspector, "resolution_log", "draft_id"):
        op.add_column("resolution_log", sa.Column("draft_id", sa.Integer(), nullable=True))

    # resolution_drafts table
    if _table_missing(inspector, "resolution_drafts"):
        op.create_table(
            "resolution_drafts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_key", sa.String(), nullable=False, index=True),
            sa.Column("draft_text", sa.Text(), nullable=False),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"))
        )

    # ticket_events table
    if _table_missing(inspector, "ticket_events"):
        op.create_table(
            "ticket_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ticket_key", sa.String(), nullable=False, index=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"))
        )

def downgrade():
    # Downgrade is optional; implement only if you need reversibility
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_missing(inspector, "ticket_events"):
        op.drop_table("ticket_events")
    if not _table_missing(inspector, "resolution_drafts"):
        op.drop_table("resolution_drafts")
    # Columns (only drop if still exist)
    if not _column_missing(inspector, "resolution_log", "draft_id"):
        op.drop_column("resolution_log", "draft_id")
    if not _column_missing(inspector, "validations_log", "duplicate_of"):
        op.drop_column("validations_log", "duplicate_of")
    if not _column_missing(inspector, "validations_log", "priority"):
        op.drop_column("validations_log", "priority")
