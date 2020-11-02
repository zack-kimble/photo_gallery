"""add fields for label names

Revision ID: 5395a9a87603
Revises: 6bc2ba763303
Create Date: 2020-11-01 13:36:07.628413

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5395a9a87603'
down_revision = '6bc2ba763303'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('photo_face', sa.Column('bb_auto', sa.BOOLEAN(), nullable=True))
    op.add_column('photo_face', sa.Column('name', sa.VARCHAR(), nullable=True))
    op.add_column('photo_face', sa.Column('name_type', sa.BOOLEAN(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('photo_face', 'name_type')
    op.drop_column('photo_face', 'name')
    op.drop_column('photo_face', 'bb_auto')
    # ### end Alembic commands ###
