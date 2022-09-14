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
        "searches",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("query", sa.Text, nullable=False, unique=True),
        sa.Column("per_page", sa.BigInteger, nullable=False),
        sa.Column("max_taken_date", sa.BigInteger, nullable=False),
        sa.Column("last_page_idx", sa.BigInteger, nullable=False),
        sa.Column("last_image_idx", sa.BigInteger, nullable=False),
        sa.Column("first_search_time", sa.DateTime(timezone=True), server_default=sa.sql.func.now()),
        sa.Column("last_search_time", sa.TIMESTAMP(timezone=True), server_default=sa.sql.func.now()),
    )

    op.create_table(
        "images",
        sa.Column("flickr_id", sa.BigInteger, primary_key=True),
        sa.Column("image_path", sa.Text, nullable=False),
        sa.Column("label", sa.BigInteger, nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.sql.func.now()),
        sa.Column("search_id", sa.BigInteger, sa.ForeignKey("searches.id"), nullable=False, index=True),
        sa.Column("page_idx", sa.BigInteger, nullable=False),
        sa.Column("image_idx", sa.BigInteger, nullable=False),
    )
    op.create_index("ix_images_page_idx_image_idx", "images", ["page_idx", "image_idx"])



def downgrade():
    op.drop_table("searches")
    op.drop_table("images")
