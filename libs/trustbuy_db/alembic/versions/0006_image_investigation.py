"""Image-based investigation support: investigations.data_source
("fetched" | "image_ocr" | "url_and_image") and investigations.image_storage_key,
mirroring how a manually-vs-independently-sourced investigation is
distinguished (see PROJECT_REPORT.md / ARCHITECTURE.md image-analysis feature).

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-24
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigations",
        sa.Column("data_source", sa.String(length=20), nullable=False, server_default="fetched"),
    )
    op.add_column("investigations", sa.Column("image_storage_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("investigations", "image_storage_key")
    op.drop_column("investigations", "data_source")
