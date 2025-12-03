"""add sensitivity column to domains table

Revision ID: add_sensitivity_column
Revises: 864a664e0645
Create Date: 2025-12-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_sensitivity_column'
down_revision = '864a664e0645'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('domains', sa.Column('sensitivity', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('domains', 'sensitivity')
