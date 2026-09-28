"""add INACTIVE spot status

Revision ID: 52c15dd57291
Revises: 9ba7b5bc597d
Create Date: 2026-09-28 12:26:55.801505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52c15dd57291'
down_revision: Union[str, Sequence[str], None] = '9ba7b5bc597d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Adds an INACTIVE spot status (used by DELETE /spots/{id} to deactivate a
    spot instead of removing the row) and makes spot_number unique only among
    non-INACTIVE spots, so a number frees up once its spot is deactivated.

    Swaps in a brand new 'status' enum type (with INACTIVE already included)
    rather than ALTER TYPE ... ADD VALUE: Postgres refuses to use a value added
    that way until the transaction that added it has committed, which would
    break creating the partial index below in the same migration.
    """
    op.execute("CREATE TYPE status_new AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'INACTIVE')")

    op.execute("ALTER TABLE spot ADD COLUMN status_new status_new")
    op.execute("UPDATE spot SET status_new = status::text::status_new")
    op.execute("ALTER TABLE spot ALTER COLUMN status_new SET NOT NULL")
    op.execute("ALTER TABLE spot ALTER COLUMN status_new SET DEFAULT 'PENDING'")

    op.drop_constraint('spot_spot_number_key', 'spot', type_='unique')

    op.execute("ALTER TABLE spot DROP COLUMN status")
    op.execute("ALTER TABLE spot RENAME COLUMN status_new TO status")

    op.execute("DROP TYPE status")
    op.execute("ALTER TYPE status_new RENAME TO status")

    op.create_index(
        'uq_spot_number_active',
        'spot',
        ['spot_number'],
        unique=True,
        postgresql_where=sa.text("status <> 'INACTIVE'"),
    )


def downgrade() -> None:
    """Downgrade schema.

    Lossy: any spot already marked INACTIVE has no equivalent in the prior
    model and is remapped to PENDING.
    """
    op.drop_index('uq_spot_number_active', table_name='spot', postgresql_where=sa.text("status <> 'INACTIVE'"))

    op.execute("CREATE TYPE status_old AS ENUM ('PENDING', 'APPROVED', 'REJECTED')")

    op.execute("ALTER TABLE spot ADD COLUMN status_old status_old")
    op.execute(
        """
        UPDATE spot
        SET status_old = CASE
            WHEN status = 'INACTIVE' THEN 'PENDING'::status_old
            ELSE status::text::status_old
        END
        """
    )
    op.execute("ALTER TABLE spot ALTER COLUMN status_old SET NOT NULL")
    op.execute("ALTER TABLE spot ALTER COLUMN status_old SET DEFAULT 'PENDING'")

    op.execute("ALTER TABLE spot DROP COLUMN status")
    op.execute("ALTER TABLE spot RENAME COLUMN status_old TO status")

    op.execute("DROP TYPE status")
    op.execute("ALTER TYPE status_old RENAME TO status")

    op.create_unique_constraint('spot_spot_number_key', 'spot', ['spot_number'])
