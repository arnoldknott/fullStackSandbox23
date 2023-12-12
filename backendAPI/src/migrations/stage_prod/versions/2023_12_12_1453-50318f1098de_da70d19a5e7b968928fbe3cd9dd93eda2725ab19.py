# fmt: off
# ruff: noqa
""""da70d19a5e7b968928fbe3cd9dd93eda2725ab19"

Revision ID: 50318f1098de
Revises: 32c8b266512a
Create Date: 2023-12-12 14:53:46.328539+01:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '50318f1098de'
down_revision: Union[str, None] = '32c8b266512a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('demoresource', 'language')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('demoresource', sa.Column('language', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###

# fmt: on
