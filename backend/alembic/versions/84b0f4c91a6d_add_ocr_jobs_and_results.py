"""Add OCR job/results tables without changing registration data."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "84b0f4c91a6d"
down_revision: Union[str, Sequence[str], None] = "ce04d2d1187a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "ocrjob" not in existing:
        op.create_table(
            "ocrjob",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("image_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("handwriting_regions", sa.JSON(), nullable=False),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["image_id"], ["imageasset.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("image_id", name="uq_ocrjob_image_id"),
        )
        op.create_index("ix_ocrjob_project_id", "ocrjob", ["project_id"])
        op.create_index("ix_ocrjob_image_id", "ocrjob", ["image_id"])
        op.create_index("ix_ocrjob_status", "ocrjob", ["status"])

    if "ocrresult" not in existing:
        op.create_table(
            "ocrresult",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("image_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("region_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.String(length=20000), nullable=False),
            sa.Column("polygon", sa.JSON(), nullable=False),
            sa.Column("coordinate_space", sa.String(length=32), nullable=False, server_default="processed"),
            sa.Column("image_width", sa.Integer(), nullable=False),
            sa.Column("image_height", sa.Integer(), nullable=False),
            sa.Column("recognition_type", sa.String(length=32), nullable=False, server_default="printed"),
            sa.Column("model_id", sa.String(length=255), nullable=False),
            sa.Column("model_version", sa.String(length=100), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("extra_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["image_id"], ["imageasset.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["job_id"], ["ocrjob.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_id", "region_index", name="uq_ocrresult_job_region"),
        )
        op.create_index("ix_ocrresult_project_id", "ocrresult", ["project_id"])
        op.create_index("ix_ocrresult_image_id", "ocrresult", ["image_id"])
        op.create_index("ix_ocrresult_job_id", "ocrresult", ["job_id"])


def downgrade() -> None:
    op.drop_table("ocrresult")
    op.drop_table("ocrjob")