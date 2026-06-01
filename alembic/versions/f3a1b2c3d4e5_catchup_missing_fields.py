"""catchup_missing_fields

Revision ID: f3a1b2c3d4e5
Revises: e21a7137eae1
Create Date: 2026-05-08 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e21a7137eae1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # --- Companies ---
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_api_key', sa.String(length=500), nullable=True, server_default=''))
        batch_op.add_column(sa.Column('ai_model', sa.String(length=50), nullable=True, server_default='gemini-2.5-flash'))
        batch_op.add_column(sa.Column('ai_enabled', sa.Boolean(), nullable=True, server_default='1'))

    # --- Transactions ---
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True, server_default='confirmed'))
        batch_op.add_column(sa.Column('edv_amount', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('edv_account_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('base_amount', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('base_edv_amount', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_transactions_edv_account', 'accounts', ['edv_account_id'], ['id'])

    # --- Planned Payments ---
    with op.batch_alter_table('planned_payments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('currency', sa.String(length=10), nullable=True, server_default='AZN'))
        batch_op.add_column(sa.Column('edv_amount', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('edv_account_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_planned_edv_account', 'accounts', ['edv_account_id'], ['id'])

def downgrade() -> None:
    with op.batch_alter_table('planned_payments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_planned_edv_account', type_='foreignkey')
        batch_op.drop_column('edv_account_id')
        batch_op.drop_column('edv_amount')
        batch_op.drop_column('currency')

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transactions_edv_account', type_='foreignkey')
        batch_op.drop_column('base_edv_amount')
        batch_op.drop_column('base_amount')
        batch_op.drop_column('edv_account_id')
        batch_op.drop_column('edv_amount')
        batch_op.drop_column('status')

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_column('ai_enabled')
        batch_op.drop_column('ai_model')
        batch_op.drop_column('ai_api_key')
