"""add ssl monitoring fields

Revision ID: ssl_monitoring_001
Revises: add_sensitivity_column
Create Date: 2025-12-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ssl_monitoring_001'
down_revision = 'add_sensitivity_column'
branch_labels = None
depends_on = None


def upgrade():
    # Add SSL monitoring columns to domains table
    op.add_column('domains', sa.Column('ssl_enabled', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('domains', sa.Column('ssl_expiry_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('domains', sa.Column('ssl_issuer', sa.String(), nullable=True))
    op.add_column('domains', sa.Column('ssl_subject', sa.String(), nullable=True))
    op.add_column('domains', sa.Column('ssl_days_until_expiry', sa.Integer(), nullable=True))
    op.add_column('domains', sa.Column('ssl_last_checked', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove SSL monitoring columns
    op.drop_column('domains', 'ssl_last_checked')
    op.drop_column('domains', 'ssl_days_until_expiry')
    op.drop_column('domains', 'ssl_subject')
    op.drop_column('domains', 'ssl_issuer')
    op.drop_column('domains', 'ssl_expiry_date')
    op.drop_column('domains', 'ssl_enabled')
