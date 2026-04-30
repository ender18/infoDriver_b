"""add driver_accounts table

Revision ID: b3f9a2e1c7d0
Revises: 4829c17cb36a
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f9a2e1c7d0'
down_revision: Union[str, Sequence[str], None] = '4829c17cb36a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'driver_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('forename', sa.String(length=100), nullable=True),
        sa.Column('surname', sa.String(length=100), nullable=True),
        sa.Column('current_balance', sa.Float(), nullable=True),
        sa.Column('outstanding_amount', sa.Float(), nullable=True),
        sa.Column('all_jobs_total', sa.Float(), nullable=True),
        sa.Column('all_jobs_commission', sa.Float(), nullable=True),
        sa.Column('last_processed_api', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('process_status', sa.String(length=20), nullable=True),
        sa.Column('process_result', sa.Text(), nullable=True),
        sa.Column('process_balance_before', sa.Float(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_driver_accounts_id', 'driver_accounts', ['id'], unique=False)
    op.create_index('ix_driver_accounts_company_id', 'driver_accounts', ['company_id'], unique=False)
    op.create_index('ix_driver_accounts_driver_id', 'driver_accounts', ['driver_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_driver_accounts_driver_id', table_name='driver_accounts')
    op.drop_index('ix_driver_accounts_company_id', table_name='driver_accounts')
    op.drop_index('ix_driver_accounts_id', table_name='driver_accounts')
    op.drop_table('driver_accounts')
