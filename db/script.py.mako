"""
${message}

Revision ID: ${up_revision}
Down revision ID: ${down_revision}
Created date: ${create_date}
"""



revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    pass


def downgrade():
    pass
