"""สร้างตารางตั้งต้นทั้ง 13 ตาราง (initial schema)

เทียบเท่ากับสิ่งที่ SQLModel.metadata.create_all() เคยสร้างให้ คือสโกีมาตั้งต้นของระบบ
ตาม app/models.py — เรียงสร้างตามลำดับ foreign key (users/cars/showrooms ก่อน แล้วค่อยตารางลูก)

ใช้ batch_alter_table กับ index เพราะ SQLite แก้โครงตารางตรง ๆ ไม่ได้
(บน PostgreSQL สิ่งที่ออกมาเหมือน CREATE INDEX ปกติ)

Revision ID: 0001_initial
Revises: -
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('cars',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('brand', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('tagline', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('price', sa.Integer(), nullable=False),
    sa.Column('engine', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('power_hp', sa.Integer(), nullable=False),
    sa.Column('torque_nm', sa.Integer(), nullable=False),
    sa.Column('drive', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('drive_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('seats', sa.Integer(), nullable=False),
    sa.Column('fuel', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('accel', sa.Float(), nullable=False),
    sa.Column('safety', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('warranty', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('colors', sa.JSON(), nullable=False),
    sa.Column('options', sa.JSON(), nullable=False),
    sa.Column('promotion', sa.JSON(), nullable=True),
    sa.Column('road', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('cars', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cars_brand'), ['brand'], unique=False)
        batch_op.create_index(batch_op.f('ix_cars_drive_code'), ['drive_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_cars_price'), ['price'], unique=False)

    op.create_table('finance_plans',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('flat_rate', sa.Float(), nullable=False),
    sa.Column('min_down_pct', sa.Integer(), nullable=False),
    sa.Column('terms', sa.JSON(), nullable=False),
    sa.Column('promo', sa.Boolean(), nullable=False),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('showrooms',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('address', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('hours', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('service_center', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('full_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(length=254), nullable=False),
    sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(length=15), nullable=False),
    sa.Column('role', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    op.create_table('auth_sessions',
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('token_hash')
    )
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('documents',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('content_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documents_user_id'), ['user_id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('message', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('link', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)

    op.create_table('point_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('ref', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('point_transactions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_point_transactions_user_id'), ['user_id'], unique=False)

    op.create_table('reservations',
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('car_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('car_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('base_price', sa.Integer(), nullable=False),
    sa.Column('color', sa.JSON(), nullable=False),
    sa.Column('options', sa.JSON(), nullable=False),
    sa.Column('total_price', sa.Integer(), nullable=False),
    sa.Column('booking_fee', sa.Integer(), nullable=False),
    sa.Column('payment_method', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('promotion', sa.JSON(), nullable=True),
    sa.Column('promotion_expired', sa.Boolean(), nullable=False),
    sa.Column('price_locked_until', sa.Date(), nullable=False),
    sa.Column('customer_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('customer_phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('customer_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('contact_message_only', sa.Boolean(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('loan_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('delivery_date', sa.Date(), nullable=True),
    sa.Column('refund', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('code')
    )
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reservations_user_id'), ['user_id'], unique=False)

    op.create_table('reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('car_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('comment', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'car_id', name='uq_review_user_car')
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reviews_car_id'), ['car_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reviews_user_id'), ['user_id'], unique=False)

    op.create_table('service_appointments',
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('car_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('showroom_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('time', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=False),
    sa.Column('service_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('mileage_km', sa.Integer(), nullable=False),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
    sa.ForeignKeyConstraint(['showroom_id'], ['showrooms.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('code')
    )
    with op.batch_alter_table('service_appointments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_service_appointments_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_service_appointments_showroom_id'), ['showroom_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_service_appointments_user_id'), ['user_id'], unique=False)

    op.create_table('test_drives',
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('car_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('showroom_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('time', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('contact_message_only', sa.Boolean(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['car_id'], ['cars.id'], ),
    sa.ForeignKeyConstraint(['showroom_id'], ['showrooms.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('code')
    )
    with op.batch_alter_table('test_drives', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_test_drives_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_test_drives_showroom_id'), ['showroom_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_test_drives_user_id'), ['user_id'], unique=False)

    op.create_table('loans',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('reservation_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('plan_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('plan', sa.JSON(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('down_payment', sa.Integer(), nullable=False),
    sa.Column('down_pct', sa.Float(), nullable=False),
    sa.Column('principal', sa.Integer(), nullable=False),
    sa.Column('term_months', sa.Integer(), nullable=False),
    sa.Column('monthly_payment', sa.Integer(), nullable=False),
    sa.Column('monthly_income', sa.Integer(), nullable=False),
    sa.Column('applicant_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('applicant_phone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('occupation', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('documents', sa.JSON(), nullable=False),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('decided_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['plan_id'], ['finance_plans.id'], ),
    sa.ForeignKeyConstraint(['reservation_code'], ['reservations.code'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('loans', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_loans_reservation_code'), ['reservation_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_loans_user_id'), ['user_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('loans', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_loans_user_id'))
        batch_op.drop_index(batch_op.f('ix_loans_reservation_code'))

    op.drop_table('loans')
    with op.batch_alter_table('test_drives', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_test_drives_user_id'))
        batch_op.drop_index(batch_op.f('ix_test_drives_showroom_id'))
        batch_op.drop_index(batch_op.f('ix_test_drives_date'))

    op.drop_table('test_drives')
    with op.batch_alter_table('service_appointments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_service_appointments_user_id'))
        batch_op.drop_index(batch_op.f('ix_service_appointments_showroom_id'))
        batch_op.drop_index(batch_op.f('ix_service_appointments_date'))

    op.drop_table('service_appointments')
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reviews_user_id'))
        batch_op.drop_index(batch_op.f('ix_reviews_car_id'))

    op.drop_table('reviews')
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reservations_user_id'))

    op.drop_table('reservations')
    with op.batch_alter_table('point_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_point_transactions_user_id'))

    op.drop_table('point_transactions')
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))

    op.drop_table('notifications')
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_user_id'))

    op.drop_table('documents')
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_sessions_user_id'))

    op.drop_table('auth_sessions')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    op.drop_table('showrooms')
    op.drop_table('finance_plans')
    with op.batch_alter_table('cars', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cars_price'))
        batch_op.drop_index(batch_op.f('ix_cars_drive_code'))
        batch_op.drop_index(batch_op.f('ix_cars_brand'))

    op.drop_table('cars')
