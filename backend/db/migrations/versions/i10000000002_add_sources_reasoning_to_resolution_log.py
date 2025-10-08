"""add sources and reasoning columns to resolution_log

Revision ID: i10000000002
Revises: h10000000001_create_external_search_tables
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'i10000000002'
# Corrected: previous migration's revision id is 'h10000000001' (file name included descriptive suffix)
down_revision = 'h10000000001'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('resolution_log') as batch:
        batch.add_column(sa.Column('sources_json', sa.JSON()))
        batch.add_column(sa.Column('reasoning_text', sa.Text()))

def downgrade():
    with op.batch_alter_table('resolution_log') as batch:
        batch.drop_column('sources_json')
        batch.drop_column('reasoning_text')