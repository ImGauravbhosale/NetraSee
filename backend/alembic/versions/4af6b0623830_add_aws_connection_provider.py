"""Add AWS connection provider

Revision ID: 4af6b0623830
Revises: 30e1acda9687
Create Date: 2026-10-03 12:02:09.520789

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4af6b0623830'
down_revision: Union[str, Sequence[str], None] = '30e1acda9687'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alembic's autogenerate doesn't detect new values on a native
    # Postgres ENUM type, and ALTER TYPE ... ADD VALUE can't run inside
    # the same transaction a later statement might use the new value in
    # — so this runs outside the migration's wrapping transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE connection_provider ADD VALUE IF NOT EXISTS 'AWS'")


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing it cleanly
    # requires recreating the enum type and every column that uses it,
    # which isn't worth the risk for a demo/dev-stage downgrade path —
    # not implemented on purpose rather than faked.
    raise NotImplementedError(
        "Cannot drop an enum value in Postgres without recreating the type. "
        "Restore from a backup taken before this migration if you need to downgrade."
    )
