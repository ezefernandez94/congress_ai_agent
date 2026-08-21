"""add bot_users

Revision ID: b3f1c9d2e4a7
Revises: ca7a0ac27660
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f1c9d2e4a7'
down_revision: Union[str, None] = 'ca7a0ac27660'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bot_users',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('is_owner', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('receives_digest', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_users_telegram_user_id'), 'bot_users', ['telegram_user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_bot_users_telegram_user_id'), table_name='bot_users')
    op.drop_table('bot_users')
