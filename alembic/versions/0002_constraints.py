"""constraints and indexes

Revision ID: 0002
Revises: 0001
"""
import os

from alembic import op

revision = "0002"
down_revision = '0001'
branch_labels = None
depends_on = None

DIR = os.path.join(os.path.dirname(__file__), "..", "..", "db")


def run(name):
    # SQL лежит в каталоге db/. Выполняем через курсор драйвера: так знаки % в
    # RAISE EXCEPTION не принимаются за параметры.
    sql = open(os.path.join(DIR, name), encoding="utf-8").read()
    cur = op.get_bind().connection.cursor()
    cur.execute(sql)
    cur.close()


def upgrade():
    run("02_constraints.sql")


def downgrade():
    run("down_02.sql")
