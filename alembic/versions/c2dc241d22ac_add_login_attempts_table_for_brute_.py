"""add login_attempts table for brute force protection

Revision ID: c2dc241d22ac
Revises: 3a37c413acf9
Create Date: 2026-10-21 12:43:21.623081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2dc241d22ac'
down_revision: Union[str, Sequence[str], None] = '3a37c413acf9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('login_attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=False),
    sa.Column('attempt_count', sa.Integer(), nullable=False),
    sa.Column('blocked_until', sa.DateTime(), nullable=True),
    sa.Column('last_attempt_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_attempts_ip_address'), 'login_attempts', ['ip_address'], unique=False)
    op.create_index(op.f('ix_login_attempts_id'), 'login_attempts', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_login_attempts_id'), table_name='login_attempts')
    op.drop_index(op.f('ix_login_attempts_ip_address'), table_name='login_attempts')
    op.drop_table('login_attempts')
