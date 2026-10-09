"""เพิ่มตาราง payments ของ Payment service (ชำระเงินจองก่อนออกใบจอง)

ตารางนี้เก็บรายการชำระเงินจอง (payment intent) ที่เกิด "ก่อน" ใบจอง
จึงมี FK ไปที่ reservations.code แบบ nullable — เติมค่าตอน confirm สำเร็จเท่านั้น
สร้างหลัง reservations เสมอ (down_revision ชี้ที่ 0001_initial) ไม่งั้น FK หาตารางปลายทางไม่เจอ

index: user_id (ลิสต์รายการของผู้ใช้) และ status (กวาดรายการที่ยัง pending)

Revision ID: 0002_payments
Revises: 0001_initial
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0002_payments'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('payments',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('purpose', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('method', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('reference', sa.JSON(), nullable=False),
    sa.Column('qr_payload', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.Column('reservation_code', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['reservation_code'], ['reservations.code'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payments_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_payments_user_id'), ['user_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_user_id'))
        batch_op.drop_index(batch_op.f('ix_payments_status'))

    op.drop_table('payments')
