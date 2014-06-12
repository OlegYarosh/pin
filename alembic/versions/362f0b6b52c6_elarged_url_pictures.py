"""elarged url pictures

Revision ID: 362f0b6b52c6
Revises: 4c683c8911ce
Create Date: 2014-06-12 11:31:32.447323

"""

# revision identifiers, used by Alembic.
revision = '362f0b6b52c6'
down_revision = '4c683c8911ce'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('pictures', sa.Column('enlarged_url', sa.Text))


def downgrade():
    op.drop_column('pictures', 'enlarged_url')
