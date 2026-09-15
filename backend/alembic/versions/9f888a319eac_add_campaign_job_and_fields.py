"""add_campaign_job_and_fields

Revision ID: 9f888a319eac
Revises: 57961cab038a
Create Date: 2026-09-14 18:51:04.951394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f888a319eac'
down_revision: Union[str, Sequence[str], None] = '57961cab038a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('discovery_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('campaign_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('target_count', sa.Integer(), nullable=True),
        sa.Column('discovered_count', sa.Integer(), nullable=True),
        sa.Column('unique_count', sa.Integer(), nullable=True),
        sa.Column('duplicate_count', sa.Integer(), nullable=True),
        sa.Column('failed_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('category', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('keywords', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))
        batch_op.add_column(sa.Column('locations', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))
        batch_op.add_column(sa.Column('require_phone', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('require_website', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('require_email', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('discovered_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('unique_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('duplicate_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('failed_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_column('completed_at')
        batch_op.drop_column('started_at')
        batch_op.drop_column('failed_count')
        batch_op.drop_column('duplicate_count')
        batch_op.drop_column('unique_count')
        batch_op.drop_column('discovered_count')
        batch_op.drop_column('require_email')
        batch_op.drop_column('require_website')
        batch_op.drop_column('require_phone')
        batch_op.drop_column('locations')
        batch_op.drop_column('keywords')
        batch_op.drop_column('category')
        batch_op.drop_column('description')
    op.drop_table('discovery_jobs')
