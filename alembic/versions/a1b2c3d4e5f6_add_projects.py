"""add_projects

Revision ID: a1b2c3d4e5f6
Revises: f3a1b2c3d4e5
Create Date: 2026-06-19 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e8496a85b63b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the projects table
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('projects'):
        op.create_table(
            'projects',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('company_id', sa.Integer(),
                      sa.ForeignKey('companies.id', ondelete='CASCADE'),
                      nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True, server_default=''),
            sa.Column('color', sa.String(length=10), nullable=True, server_default='#2970ff'),
            sa.Column('budget', sa.Integer(), nullable=True),   # CentsInteger storage
            sa.Column('start_date', sa.DateTime(), nullable=True),
            sa.Column('end_date', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_projects_company', 'projects', ['company_id'])

    # 2. Add project_id to transactions
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('project_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_transactions_project', 'projects', ['project_id'], ['id']
        )

    # 3. Add project_id to planned_payments
    with op.batch_alter_table('planned_payments', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('project_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_planned_project', 'projects', ['project_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('planned_payments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_planned_project', type_='foreignkey')
        batch_op.drop_column('project_id')

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transactions_project', type_='foreignkey')
        batch_op.drop_column('project_id')

    op.drop_index('ix_projects_company', table_name='projects')
    op.drop_table('projects')
