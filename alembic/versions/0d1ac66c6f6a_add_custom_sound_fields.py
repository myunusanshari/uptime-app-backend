"""add_custom_sound_fields

Revision ID: 0d1ac66c6f6a
Revises: ssl_monitoring_001
Create Date: 2025-12-05 05:32:52.499422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d1ac66c6f6a'
down_revision: Union[str, Sequence[str], None] = 'ssl_monitoring_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new custom sound columns
    op.add_column('domains', sa.Column('custom_sound_down', sa.String(), nullable=True))
    op.add_column('domains', sa.Column('custom_sound_up', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove custom sound columns
    op.drop_column('domains', 'custom_sound_up')
    op.drop_column('domains', 'custom_sound_down')
