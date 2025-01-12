"""project

Revision ID: 7a83343605fa
Create Date: 2016-05-19 11:24:59.309190

"""

from alembic import op  # noqa
import sqlalchemy as sa  # noqa
import datetime  # noqa

# revision identifiers, used by Alembic.
revision = '7a83343605fa'
down_revision = 'f60452e2e987'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('op_project_id', sa.String(32), nullable=False),
        sa.Column('qt_load_balancers', sa.Integer, nullable=True),
        sa.Column('cu_load_balancers', sa.Integer, nullable=True),

        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),

        sa.Column('deleted', sa.DateTime(), nullable=True),
        sa.Column('ceased', sa.DateTime(), nullable=True),

        mysql_DEFAULT_CHARSET='utf8'
    )
    op.execute(
        sa.sql.table(
            'project',
            sa.sql.column('qt_load_balancers'),
            sa.sql.column('cu_load_balancers'),
        )
        .update()
        .values({
            'qt_load_balancers': op.inline_literal(1),
            'cu_load_balancers': op.inline_literal(0),
        })
    )


def downgrade():
    op.drop_table('project')
