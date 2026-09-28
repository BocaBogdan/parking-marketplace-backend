"""collapse user roles to USER and ADMIN

Revision ID: 9ba7b5bc597d
Revises: 3fa4d7793180
Create Date: 2026-09-26 13:08:02.025507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ba7b5bc597d'
down_revision: Union[str, Sequence[str], None] = '3fa4d7793180'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Postgres can't drop values from an existing enum type, so collapsing
    DRIVER/OWNER into USER requires swapping in a brand new enum type rather
    than ALTER TYPE ... ADD VALUE (which also can't be used to remove values).
    """
    op.execute("CREATE TYPE user_role_new AS ENUM ('USER', 'ADMIN')")

    op.execute("ALTER TABLE users ADD COLUMN role_new user_role_new")
    op.execute(
        """
        UPDATE users
        SET role_new = CASE
            WHEN role = 'ADMIN' THEN 'ADMIN'::user_role_new
            ELSE 'USER'::user_role_new
        END
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN role_new SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN role_new SET DEFAULT 'USER'")

    op.execute("ALTER TABLE users DROP COLUMN role")
    op.execute("ALTER TABLE users RENAME COLUMN role_new TO role")

    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")


def downgrade() -> None:
    """Downgrade schema.

    Lossy: DRIVER vs OWNER can no longer be distinguished once collapsed into
    USER, so every USER row is mapped back to DRIVER on downgrade.
    """
    op.execute("CREATE TYPE user_role_old AS ENUM ('DRIVER', 'OWNER', 'ADMIN')")

    op.execute("ALTER TABLE users ADD COLUMN role_old user_role_old")
    op.execute(
        """
        UPDATE users
        SET role_old = CASE
            WHEN role = 'ADMIN' THEN 'ADMIN'::user_role_old
            ELSE 'DRIVER'::user_role_old
        END
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN role_old SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN role_old SET DEFAULT 'DRIVER'")

    op.execute("ALTER TABLE users DROP COLUMN role")
    op.execute("ALTER TABLE users RENAME COLUMN role_old TO role")

    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_old RENAME TO user_role")
