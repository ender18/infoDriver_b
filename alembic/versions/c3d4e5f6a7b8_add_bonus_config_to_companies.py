"""add_bonus_config_to_companies

Revision ID: c3d4e5f6a7b8
Revises: 0aaae2085397
Create Date: 2026-06-11 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = '0aaae2085397'
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('bonus_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'bonus_config')
