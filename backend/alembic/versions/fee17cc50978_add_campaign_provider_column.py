"""add_campaign_provider_column

Revision ID: fee17cc50978
Revises: 9f888a319eac
Create Date: 2026-09-14 19:05:59.918539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'fee17cc50978'
down_revision: Union[str, Sequence[str], None] = '9f888a319eac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider', sa.Text(), nullable=True, server_default='mock'))


def downgrade() -> None:
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_column('provider')
