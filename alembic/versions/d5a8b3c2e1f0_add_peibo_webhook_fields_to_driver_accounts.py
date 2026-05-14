"""add peibo and webhook fields to driver_accounts

Revision ID: d5a8b3c2e1f0
Revises: c4e8f2d3a1b5
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5a8b3c2e1f0'
down_revision: Union[str, Sequence[str], None] = 'c4e8f2d3a1b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sesión — para trazar qué refresh originó cada registro
    op.add_column('driver_accounts', sa.Column('session_id', sa.String(36), nullable=True))

    # Pago Peibo
    op.add_column('driver_accounts', sa.Column('payment_status',        sa.String(20),  nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_transaction_id',  sa.String(100), nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_tracking_code',   sa.String(100), nullable=True))
    op.add_column('driver_accounts', sa.Column('peibo_paid_at',         sa.DateTime(timezone=True), nullable=True))

    # Webhook Peibo
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

    op.create_index('ix_driver_accounts_peibo_tracking', 'driver_accounts', ['peibo_tracking_code'])
    op.create_index('ix_driver_accounts_session_id',     'driver_accounts', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_driver_accounts_session_id',     table_name='driver_accounts')
    op.drop_index('ix_driver_accounts_peibo_tracking', table_name='driver_accounts')

    for col in [
        'webhook_received_at', 'webhook_refund_reason_code', 'webhook_type',
        'webhook_originator_tax_id', 'webhook_originator_name', 'webhook_originator_bank',
        'webhook_originator_account', 'webhook_beneficiary_account', 'webhook_amount',
        'webhook_reference', 'webhook_concept', 'webhook_date_time',
        'webhook_transaction_id', 'webhook_status',
        'peibo_paid_at', 'peibo_tracking_code', 'peibo_transaction_id', 'payment_status',
        'session_id',
    ]:
        op.drop_column('driver_accounts', col)
