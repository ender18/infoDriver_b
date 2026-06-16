"""create_payment_queue

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-11 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payment_queue',
        sa.Column('id',                   sa.Integer(),     primary_key=True),
        sa.Column('company_id',           sa.Integer(),     sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('source',               sa.String(30),    nullable=False),
        sa.Column('driver_id',            sa.Integer(),     nullable=True),
        sa.Column('callsign',             sa.String(50),    nullable=True),
        sa.Column('forename',             sa.String(100),   nullable=True),
        sa.Column('surname',              sa.String(100),   nullable=True),
        sa.Column('bank_name',            sa.String(150),   nullable=True),
        sa.Column('bank_sort_code',       sa.String(100),   nullable=True),
        sa.Column('amount',               sa.Float(),       nullable=False),
        sa.Column('adjusted_amount',      sa.Float(),       nullable=True),
        sa.Column('notes',                sa.Text(),        nullable=True),
        sa.Column('source_ref',           sa.String(255),   nullable=True),
        sa.Column('status',               sa.String(20),    nullable=False, server_default='pending'),
        sa.Column('rejection_reason',     sa.Text(),        nullable=True),
        sa.Column('queued_by_id',         sa.Integer(),     sa.ForeignKey('users.id'), nullable=True),
        sa.Column('queued_at',            sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_by_id',       sa.Integer(),     sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at',          sa.DateTime(timezone=True), nullable=True),
        sa.Column('peibo_transaction_id', sa.Integer(),     sa.ForeignKey('peibo_transactions.id'), nullable=True),
    )
    op.create_index('ix_pq_company_status', 'payment_queue', ['company_id', 'status'])
    op.create_index('ix_pq_queued_at',      'payment_queue', ['queued_at'])


def downgrade() -> None:
    op.drop_index('ix_pq_queued_at',      table_name='payment_queue')
    op.drop_index('ix_pq_company_status', table_name='payment_queue')
    op.drop_table('payment_queue')
