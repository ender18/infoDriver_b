"""add bank_name, bank_sort_code, callsign to driver_accounts

Revision ID: c4e8f2d3a1b5
Revises: b3f9a2e1c7d0
Create Date: 2026-04-29 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4e8f2d3a1b5'
down_revision: Union[str, Sequence[str], None] = 'b3f9a2e1c7d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('driver_accounts', sa.Column('callsign',       sa.String(length=50),  nullable=True))
    op.add_column('driver_accounts', sa.Column('bank_name',      sa.String(length=150), nullable=True))
    op.add_column('driver_accounts', sa.Column('bank_sort_code', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('driver_accounts', 'bank_sort_code')
    op.drop_column('driver_accounts', 'bank_name')
    op.drop_column('driver_accounts', 'callsign')
