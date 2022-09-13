"""
create images table

Revision ID: 12ade287ead0
Down revision ID: None
Created date: 2022-09-07 01:18:25.189943+00:00
"""

import sqlalchemy as sa
import alembic.op as op


revision = '12ade287ead0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "images",
        sa.Column("flickr_id", sa.BigInteger, primary_key=True),
        sa.Column("image_path", sa.Text, nullable=False),
        sa.Column("label", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("collected_at", sa.TIMESTAMP(timezone=True), server_default=sa.sql.func.current_timestamp()),
    )


def downgrade():
    op.drop_table("images")
