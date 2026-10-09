"""เพิ่มตาราง watchlist_items (รายการรถที่สนใจ) ของ Catalog service

ตารางนี้เป็นความสัมพันธ์ many-to-many ระหว่าง users กับ cars จึงต้องสร้างหลังทั้งสองตาราง
(down_revision ชี้ที่ 0002_payments ซึ่งเป็น head เดิม — ไม่งั้นจะกลายเป็น 2 head แล้ว upgrade พัง)

unique (user_id, car_id): บังคับที่ระดับฐานข้อมูล ไม่พึ่งแค่โค้ด เพราะปุ่มหัวใจกดสลับไปมา
ถ้าสองรีเควสต์วิ่งพร้อมกันโค้ดฝั่งแอปอาจเช็คไม่ทัน แต่ฐานข้อมูลยังกันซ้ำได้

ไม่มีคอลัมน์สำหรับ "เคยแจ้งเตือนโปรฯ ไปแล้วหรือยัง" โดยเจตนา — ตัวกันแจ้งซ้ำดูจาก
notifications เดิมของผู้ใช้ (kind=promo.ending + link ที่มีรหัสรถและวันหมดอายุ) จึงไม่ต้องเพิ่มคอลัมน์

Revision ID: 0003_watchlist
Revises: 0002_payments
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0003_watchlist'
down_revision: Union[str, None] = '0002_payments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('watchlist_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('car_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'car_id', name='uq_watchlist_user_car')
    )
    # batch_alter_table: SQLite แก้โครงตารางตรง ๆ ไม่ได้ (บน PostgreSQL ออกมาเป็น CREATE INDEX ปกติ)
    with op.batch_alter_table('watchlist_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_watchlist_items_car_id'), ['car_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_watchlist_items_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('watchlist_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_watchlist_items_user_id'))
        batch_op.drop_index(batch_op.f('ix_watchlist_items_car_id'))

    op.drop_table('watchlist_items')
