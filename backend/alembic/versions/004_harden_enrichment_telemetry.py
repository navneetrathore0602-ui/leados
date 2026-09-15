"""harden_enrichment_telemetry

Revision ID: 004_telemetry
Revises: 7a89b01234cd
Create Date: 2026-09-14 19:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_telemetry'
down_revision: Union[str, Sequence[str], None] = '7a89b01234cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('enrichment_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reachability_state', sa.Text(), nullable=True, server_default='SUCCESS'))
        batch_op.add_column(sa.Column('pages_attempted', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('pages_successful', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('pages_failed', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('total_http_requests', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('telemetry_logs', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('avg_duration_ms', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('median_duration_ms', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('p95_duration_ms', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('phone_found_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('email_found_count', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('social_found_count', sa.Integer(), nullable=True, server_default='0'))

def downgrade() -> None:
    with op.batch_alter_table('enrichment_jobs', schema=None) as batch_op:
        batch_op.drop_column('social_found_count')
        batch_op.drop_column('email_found_count')
        batch_op.drop_column('phone_found_count')
        batch_op.drop_column('p95_duration_ms')
        batch_op.drop_column('median_duration_ms')
        batch_op.drop_column('avg_duration_ms')
        batch_op.drop_column('telemetry_logs')
        batch_op.drop_column('total_http_requests')
        batch_op.drop_column('pages_failed')
        batch_op.drop_column('pages_successful')
        batch_op.drop_column('pages_attempted')
        batch_op.drop_column('reachability_state')
