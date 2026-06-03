"""refactor driver_accounts — drop peibo/webhook fields, add FK

Revision ID: e3f4a5b6c1d2
Revises: d2e3f4a5b6c1
Create Date: 2026-05-30 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e3f4a5b6c1d2'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PEIBO_COLS = [
    'payment_status', 'peibo_transaction_id', 'peibo_tracking_code', 'peibo_paid_at',
]
WEBHOOK_COLS = [
    'webhook_status', 'webhook_transaction_id', 'webhook_date_time', 'webhook_concept',
    'webhook_reference', 'webhook_amount', 'webhook_beneficiary_account',
    'webhook_originator_account', 'webhook_originator_bank', 'webhook_originator_name',
    'webhook_originator_tax_id', 'webhook_type', 'webhook_refund_reason_code',
    'webhook_received_at',
]


def upgrade() -> None:
    op.drop_index('ix_driver_accounts_peibo_tracking', table_name='driver_accounts')
    op.drop_index('ix_driver_accounts_session_id',     table_name='driver_accounts')

    for col in PEIBO_COLS + WEBHOOK_COLS:
        op.drop_column('driver_accounts', col)

    op.add_column('driver_accounts',
        sa.Column('peibo_transaction_id', sa.Integer(), sa.ForeignKey('peibo_transactions.id'), nullable=True))

    op.create_index('ix_driver_accounts_peibo_tx', 'driver_accounts', ['peibo_transaction_id'], unique=False)
    op.create_index('ix_driver_accounts_session_id', 'driver_accounts', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_driver_accounts_peibo_tx',      table_name='driver_accounts')
    op.drop_index('ix_driver_accounts_session_id',    table_name='driver_accounts')
    op.drop_column('driver_accounts', 'peibo_transaction_id')

    op.add_column('driver_accounts', sa.Column('payment_status',       sa.String(20),  nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_transaction_id', sa.String(100), nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_tracking_code',  sa.String(100), nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_paid_at',        sa.DateTime(timezone=True), nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_status',              sa.String(50),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_transaction_id',      sa.String(100),    nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_date_time',           sa.DateTime(timezone=True), nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_concept',             sa.String(255),    nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_reference',           sa.String(100),    nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_amount',              sa.Numeric(12, 2), nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_beneficiary_account', sa.String(30),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_originator_account',  sa.String(30),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_originator_bank',     sa.String(10),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_originator_name',     sa.String(200),    nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_originator_tax_id',   sa.String(20),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_type',                sa.String(20),     nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_refund_reason_code',  sa.Integer(),      nullable=True))
    op.add_column('driver_accounts', sa.Column('webhook_received_at',         sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_driver_accounts_peibo_tracking', 'driver_accounts', ['peibo_tracking_code'], unique=False)
    op.create_index('ix_driver_accounts_session_id',     'driver_accounts', ['session_id'],           unique=False)
