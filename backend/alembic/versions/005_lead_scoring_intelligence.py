"""lead_scoring_intelligence

Revision ID: 005_scoring
Revises: 004_telemetry
Create Date: 2026-09-14 20:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_scoring'
down_revision: Union[str, Sequence[str], None] = '004_telemetry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lifecycle_status to businesses table
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lifecycle_status', sa.Text(), nullable=True, server_default='NEW'))

    # Create lead_scores table
    op.create_table(
        'lead_scores',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('business_id', sa.UUID(), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('campaign_id', sa.UUID(), sa.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('total_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tier', sa.Text(), nullable=False, server_default='LOW'),
        sa.Column('lifecycle_status', sa.Text(), nullable=False, server_default='NEW'),
        sa.Column('business_fit_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('location_fit_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('contactability_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('digital_presence_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('data_quality_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('scoring_version', sa.Text(), nullable=True, server_default='v1'),
        sa.Column('scoring_ruleset', sa.Text(), nullable=True, server_default='default_v1'),
        sa.Column('positive_signals', sa.JSON(), nullable=True),
        sa.Column('negative_signals', sa.JSON(), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('is_qualified', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.Column('disqualified', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('disqualification_reason', sa.Text(), nullable=True),
        sa.Column('disqualified_rule', sa.Text(), nullable=True),
        sa.Column('scored_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now())
    )


def downgrade() -> None:
    op.drop_table('lead_scores')
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('lifecycle_status')
