"""create peibo_webhook_events

Revision ID: d2e3f4a5b6c1
Revises: c1d2e3f4a5b6
Create Date: 2026-05-30 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd2e3f4a5b6c1'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'peibo_webhook_events',

        sa.Column('id',                    sa.Integer(),      nullable=False),

        # FK a la transacción (nullable: puede llegar un evento huérfano)
        sa.Column('peibo_transaction_id',  sa.Integer(),      nullable=True),
        sa.Column('tracking_code',         sa.String(100),    nullable=True),

        # Datos del evento
        sa.Column('status',                sa.String(50),     nullable=True),
        sa.Column('type',                  sa.String(20),     nullable=True),
        sa.Column('concept',               sa.String(255),    nullable=True),
        sa.Column('reference',             sa.String(100),    nullable=True),
        sa.Column('amount',                sa.Numeric(12, 2), nullable=True),
        sa.Column('date_time',             sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_reason_code',    sa.Integer(),      nullable=True),

        # Cuentas involucradas
        sa.Column('beneficiary_account',   sa.String(30),     nullable=True),
        sa.Column('originator_account',    sa.String(30),     nullable=True),
        sa.Column('originator_bank',       sa.String(10),     nullable=True),
        sa.Column('originator_name',       sa.String(200),    nullable=True),
        sa.Column('originator_tax_id',     sa.String(20),     nullable=True),

        # Payload crudo + timestamp de recepción
        sa.Column('raw_payload',           sa.JSON(),         nullable=True),
        sa.Column('received_at',           sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['peibo_transaction_id'], ['peibo_transactions.id']),
    )

    op.create_index('ix_pwe_id',                   'peibo_webhook_events', ['id'],                  unique=False)
    op.create_index('ix_pwe_peibo_transaction_id', 'peibo_webhook_events', ['peibo_transaction_id'], unique=False)
    op.create_index('ix_pwe_tracking_code',        'peibo_webhook_events', ['tracking_code'],        unique=False)
    op.create_index('ix_pwe_received_at',          'peibo_webhook_events', ['received_at'],          unique=False)


def downgrade() -> None:
    op.drop_table('peibo_webhook_events')
