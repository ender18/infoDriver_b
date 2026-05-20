"""add peibo fields to companies

Revision ID: a1b2c3d4e5f6
Revises: f9e7c6b4a2d1
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f9e7c6b4a2d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('peibo_customer_key',       sa.String(255), nullable=True))
    op.add_column('companies', sa.Column('peibo_api_key',            sa.String(255), nullable=True))
    op.add_column('companies', sa.Column('peibo_originator_account', sa.String(30),  nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'peibo_originator_account')
    op.drop_column('companies', 'peibo_api_key')
    op.drop_column('companies', 'peibo_customer_key')
