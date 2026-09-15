"""add_enrichment_tables

Revision ID: 7a89b01234cd
Revises: fee17cc50978
Create Date: 2026-09-14 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7a89b01234cd'
down_revision: Union[str, Sequence[str], None] = 'fee17cc50978'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'business_socials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('platform', sa.Text(), nullable=False),
        sa.Column('profile_url', sa.Text(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'business_candidate_fields',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('field_name', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'enrichment_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=True),
        sa.Column('campaign_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('fields_attempted', sa.JSON(), nullable=True),
        sa.Column('fields_found', sa.JSON(), nullable=True),
        sa.Column('fields_verified', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('error_code', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('enrichment_jobs')
    op.drop_table('business_candidate_fields')
    op.drop_table('business_socials')
