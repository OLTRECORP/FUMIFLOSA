"""0004_cancel_and_schedule

Revision ID: 0004_cancel_and_schedule
Revises: 0003_add_user_username
Create Date: 2026-09-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_cancel_and_schedule'
down_revision: Union[str, None] = '0003_add_user_username'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Campos de cancelación para certificados
    op.execute("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE NOT NULL;")
    op.execute("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);")
    op.execute("ALTER TABLE certificates ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;")
    
    # 2. Campos de estado y agendamiento para service_orders
    op.execute("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'completed' NOT NULL;")
    op.execute("ALTER TABLE service_orders ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;")


def downgrade() -> None:
    op.drop_column('certificates', 'cancelled_at')
    op.drop_column('certificates', 'cancellation_reason')
    op.drop_column('certificates', 'is_cancelled')
    op.drop_column('service_orders', 'scheduled_for')
    op.drop_column('service_orders', 'status')
