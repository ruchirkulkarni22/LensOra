"""create external docs & search audit tables

Revision ID: h10000000001
Revises: g01234567890
Create Date: 2025-10-01
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

# revision identifiers, used by Alembic.
revision = 'h10000000001'
down_revision = 'g01234567890'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'external_docs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('url', sa.Text, nullable=False, unique=True, index=True),
        sa.Column('domain', sa.String(length=255), nullable=True, index=True),
        sa.Column('title', sa.Text, nullable=True),
        sa.Column('content_text', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('embedding', VECTOR(384), nullable=True),
        sa.Column('fetched_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )
    op.create_table(
        'external_search_audit',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('query_text', sa.Text, nullable=False),
        sa.Column('normalized_query_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('provider_used', sa.String(length=50), nullable=True),
        sa.Column('result_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('external_search_audit')
    op.drop_table('external_docs')
