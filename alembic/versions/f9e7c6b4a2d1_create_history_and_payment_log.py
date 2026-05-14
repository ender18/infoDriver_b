"""create driver_accounts_history and payment_log

Revision ID: f9e7c6b4a2d1
Revises: d5a8b3c2e1f0
Create Date: 2026-05-12 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f9e7c6b4a2d1'
down_revision: Union[str, Sequence[str], None] = 'd5a8b3c2e1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'driver_accounts_history',

        sa.Column('id',         sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(36),  nullable=False),
        sa.Column('company_id', sa.Integer(),   nullable=False),

        # Datos del conductor
        sa.Column('driver_id',             sa.Integer(),   nullable=False),
        sa.Column('callsign',              sa.String(50),  nullable=True),
        sa.Column('forename',              sa.String(100), nullable=True),
        sa.Column('surname',               sa.String(100), nullable=True),
        sa.Column('bank_name',             sa.String(150), nullable=True),
        sa.Column('bank_sort_code',        sa.String(100), nullable=True),
        sa.Column('current_balance',       sa.Float(),     nullable=True),
        sa.Column('outstanding_amount',    sa.Float(),     nullable=True),
        sa.Column('all_jobs_total',        sa.Float(),     nullable=True),
        sa.Column('all_jobs_commission',   sa.Float(),     nullable=True),
        sa.Column('notes',                 sa.Text(),      nullable=True),
        sa.Column('fetched_at',            sa.DateTime(timezone=True), nullable=True),

        # Procesamiento Autocab
        sa.Column('process_status',           sa.String(20), nullable=True),
        sa.Column('process_result',           sa.Text(),     nullable=True),
        sa.Column('process_balance_before',   sa.Float(),    nullable=True),
        sa.Column('processed_at',             sa.DateTime(timezone=True), nullable=True),

        # Pago Peibo
        sa.Column('payment_status',       sa.String(20),  nullable=True),
        sa.Column('peibo_transaction_id', sa.String(100), nullable=True),
        sa.Column('peibo_tracking_code',  sa.String(100), nullable=True),
        sa.Column('peibo_paid_at',        sa.DateTime(timezone=True), nullable=True),

        # Webhook Peibo
        sa.Column('webhook_status',              sa.String(50),     nullable=True),
        sa.Column('webhook_transaction_id',      sa.String(100),    nullable=True),
        sa.Column('webhook_date_time',           sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_concept',             sa.String(255),    nullable=True),
        sa.Column('webhook_reference',           sa.String(100),    nullable=True),
        sa.Column('webhook_amount',              sa.Numeric(12, 2), nullable=True),
        sa.Column('webhook_beneficiary_account', sa.String(30),     nullable=True),
        sa.Column('webhook_originator_account',  sa.String(30),     nullable=True),
        sa.Column('webhook_originator_bank',     sa.String(10),     nullable=True),
        sa.Column('webhook_originator_name',     sa.String(200),    nullable=True),
        sa.Column('webhook_originator_tax_id',   sa.String(20),     nullable=True),
        sa.Column('webhook_type',                sa.String(20),     nullable=True),
        sa.Column('webhook_refund_reason_code',  sa.Integer(),      nullable=True),
        sa.Column('webhook_received_at',         sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
    )
    op.create_index('ix_dah_id',            'driver_accounts_history', ['id'],                 unique=False)
    op.create_index('ix_dah_session_id',    'driver_accounts_history', ['session_id'],         unique=False)
    op.create_index('ix_dah_company_id',    'driver_accounts_history', ['company_id'],         unique=False)
    op.create_index('ix_dah_driver_id',     'driver_accounts_history', ['driver_id'],          unique=False)
    op.create_index('ix_dah_tracking_code', 'driver_accounts_history', ['peibo_tracking_code'], unique=False)

    op.create_table(
        'payment_log',
        sa.Column('id',         sa.Integer(),  nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('company_id', sa.Integer(),  nullable=True),
        sa.Column('driver_id',  sa.Integer(),  nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('history_id', sa.Integer(),  nullable=True),
        sa.Column('payload',    sa.JSON(),      nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['history_id'], ['driver_accounts_history.id']),
    )
    op.create_index('ix_payment_log_id',         'payment_log', ['id'],         unique=False)
    op.create_index('ix_payment_log_company_id', 'payment_log', ['company_id'], unique=False)
    op.create_index('ix_payment_log_driver_id',  'payment_log', ['driver_id'],  unique=False)
    op.create_index('ix_payment_log_session_id', 'payment_log', ['session_id'], unique=False)
    op.create_index('ix_payment_log_event_type', 'payment_log', ['event_type'], unique=False)
    op.create_index('ix_payment_log_created_at', 'payment_log', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('payment_log')
    op.drop_table('driver_accounts_history')
