"""Add products.image_url - the source listing's own primary image URL
(schema.org `image`/og:image, hotlinked directly), so the investigation
result can show the real product photo instead of no image at all.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-17
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
