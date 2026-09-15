"""pipeline_jobs_and_exports

Revision ID: 006_pipeline_exports
Revises: 005_scoring
Create Date: 2026-09-14 21:17:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_pipeline_exports'
down_revision: Union[str, Sequence[str], None] = '005_scoring'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create pipeline_jobs table
    op.create_table(
        'pipeline_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.Text(), nullable=True, server_default='QUEUED'),
        sa.Column('current_stage', sa.Text(), nullable=True, server_default='DISCOVERY'),
        sa.Column('total_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('processed_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('partial_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_records', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('progress_percent', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('batch_size', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('stage_progress', sa.JSON(), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_pipeline_jobs_campaign_id'), 'pipeline_jobs', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_pipeline_jobs_status'), 'pipeline_jobs', ['status'], unique=False)

    # 2. Create export_history table
    op.create_table(
        'export_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('format', sa.Text(), nullable=False, server_default='xlsx'),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_export_history_campaign_id'), 'export_history', ['campaign_id'], unique=False)

    # 3. Add performance indexes on existing tables for high-volume queries
    op.create_index('ix_businesses_lifecycle_status', 'businesses', ['lifecycle_status'], unique=False)
    op.create_index('ix_lead_scores_business_id', 'lead_scores', ['business_id'], unique=False)
    op.create_index('ix_lead_scores_campaign_id', 'lead_scores', ['campaign_id'], unique=False)
    op.create_index('ix_lead_scores_tier', 'lead_scores', ['tier'], unique=False)
    op.create_index('ix_business_contacts_business_id', 'business_contacts', ['business_id'], unique=False)
    op.create_index('ix_business_locations_business_id', 'business_locations', ['business_id'], unique=False)
    op.create_index('ix_business_socials_business_id', 'business_socials', ['business_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_business_socials_business_id', table_name='business_socials')
    op.drop_index('ix_business_locations_business_id', table_name='business_locations')
    op.drop_index('ix_business_contacts_business_id', table_name='business_contacts')
    op.drop_index('ix_lead_scores_tier', table_name='lead_scores')
    op.drop_index('ix_lead_scores_campaign_id', table_name='lead_scores')
    op.drop_index('ix_lead_scores_business_id', table_name='lead_scores')
    op.drop_index('ix_businesses_lifecycle_status', table_name='businesses')

    op.drop_index(op.f('ix_export_history_campaign_id'), table_name='export_history')
    op.drop_table('export_history')

    op.drop_index(op.f('ix_pipeline_jobs_status'), table_name='pipeline_jobs')
    op.drop_index(op.f('ix_pipeline_jobs_campaign_id'), table_name='pipeline_jobs')
    op.drop_table('pipeline_jobs')
