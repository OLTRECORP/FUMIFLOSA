"""0003_add_user_username

Revision ID: 0003_add_user_username
Revises: 0002_company_and_portal
Create Date: 2026-09-29 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_add_user_username'
down_revision: Union[str, None] = '0002_company_and_portal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar columna username a users
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(100);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);")
    
    # 2. Agregar columnas faltantes a clients si no existen
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_slug VARCHAR(100);")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_password VARCHAR(255);")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS portal_is_enabled BOOLEAN DEFAULT TRUE;")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_clients_portal_slug ON clients (portal_slug);")


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
