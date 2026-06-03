"""refactor driver_accounts_history and payment_log — drop peibo/webhook fields, add FKs

Revision ID: f4a5b6c1d2e3
Revises: e3f4a5b6c1d2
Create Date: 2026-05-30 00:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f4a5b6c1d2e3'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c1d2'
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
    # ── driver_accounts_history ────────────────────────────────────────────────
    op.drop_index('ix_dah_tracking_code', table_name='driver_accounts_history')

    for col in PEIBO_COLS + WEBHOOK_COLS:
        op.drop_column('driver_accounts_history', col)

    op.add_column('driver_accounts_history',
        sa.Column('peibo_transaction_id', sa.Integer(),
                  sa.ForeignKey('peibo_transactions.id'), nullable=True))
    op.create_index('ix_dah_peibo_tx', 'driver_accounts_history', ['peibo_transaction_id'], unique=False)

    # ── payment_log ────────────────────────────────────────────────────────────
    op.add_column('payment_log',
        sa.Column('peibo_transaction_id', sa.Integer(),
                  sa.ForeignKey('peibo_transactions.id'), nullable=True))
    op.create_index('ix_pl_peibo_tx', 'payment_log', ['peibo_transaction_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_pl_peibo_tx',  table_name='payment_log')
    op.drop_column('payment_log', 'peibo_transaction_id')

    op.drop_index('ix_dah_peibo_tx', table_name='driver_accounts_history')
    op.drop_column('driver_accounts_history', 'peibo_transaction_id')

    op.add_column('driver_accounts_history', sa.Column('payment_status',       sa.String(20),  nullable=True))
    op.add_column('driver_accounts_history', sa.Column('peibo_transaction_id', sa.String(100), nullable=True))
    op.add_column('driver_accounts_history', sa.Column('peibo_tracking_code',  sa.String(100), nullable=True))
    op.add_column('driver_accounts_history', sa.Column('peibo_paid_at',        sa.DateTime(timezone=True), nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_status',              sa.String(50),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_transaction_id',      sa.String(100),    nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_date_time',           sa.DateTime(timezone=True), nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_concept',             sa.String(255),    nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_reference',           sa.String(100),    nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_amount',              sa.Numeric(12, 2), nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_beneficiary_account', sa.String(30),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_originator_account',  sa.String(30),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_originator_bank',     sa.String(10),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_originator_name',     sa.String(200),    nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_originator_tax_id',   sa.String(20),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_type',                sa.String(20),     nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_refund_reason_code',  sa.Integer(),      nullable=True))
    op.add_column('driver_accounts_history', sa.Column('webhook_received_at',         sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_dah_tracking_code', 'driver_accounts_history', ['peibo_tracking_code'], unique=False)
