"""Add password reset request table

Revision ID: 4e5d5d4b9a1c
Revises: 3ed2689003dc
Create Date: 2025-10-01 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e5d5d4b9a1c'
down_revision = '3ed2689003dc'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'password_reset_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_by_admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('note', sa.String(length=255), nullable=True),
    )
    op.create_index(
        'ix_password_reset_requests_status',
        'password_reset_requests',
        ['status']
    )
    op.create_index(
        'ix_password_reset_requests_admin_id',
        'password_reset_requests',
        ['admin_id']
    )
    op.create_index(
        'ix_password_reset_requests_user_id',
        'password_reset_requests',
        ['user_id']
    )


def downgrade():
    op.drop_index('ix_password_reset_requests_user_id', table_name='password_reset_requests')
    op.drop_index('ix_password_reset_requests_admin_id', table_name='password_reset_requests')
    op.drop_index('ix_password_reset_requests_status', table_name='password_reset_requests')
    op.drop_table('password_reset_requests')
