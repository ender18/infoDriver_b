"""create peibo_transactions

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a1
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'peibo_transactions',

        sa.Column('id',              sa.Integer(),      nullable=False),
        sa.Column('tracking_code',   sa.String(100),    nullable=False),
        sa.Column('transaction_id',  sa.String(100),    nullable=False),

        sa.Column('status',          sa.String(20),     nullable=False, server_default='pending'),
        sa.Column('amount',          sa.Numeric(12, 2), nullable=False),

        sa.Column('company_id',      sa.Integer(),      nullable=False),

        # Polimorfismo: qué módulo originó el pago
        sa.Column('source_type',     sa.String(50),     nullable=False),  # driver_payment | invoice | ...
        sa.Column('source_id',       sa.Integer(),      nullable=False),  # ID en la tabla fuente

        # Auditoría
        sa.Column('created_by',      sa.Integer(),      nullable=True),   # FK users.id
        sa.Column('error_message',   sa.Text(),         nullable=True),   # motivo de fallo
        sa.Column('paid_at',         sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',      sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at',      sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['company_id'],  ['companies.id']),
        sa.ForeignKeyConstraint(['created_by'],  ['users.id']),
    )

    op.create_index('ix_pt_id',            'peibo_transactions', ['id'],           unique=False)
    op.create_index('ix_pt_tracking_code', 'peibo_transactions', ['tracking_code'], unique=True)
    op.create_index('ix_pt_company_id',    'peibo_transactions', ['company_id'],   unique=False)
    op.create_index('ix_pt_source',        'peibo_transactions', ['source_type', 'source_id'], unique=False)
    op.create_index('ix_pt_status',        'peibo_transactions', ['status'],       unique=False)
    op.create_index('ix_pt_created_at',    'peibo_transactions', ['created_at'],   unique=False)


def downgrade() -> None:
    op.drop_table('peibo_transactions')
