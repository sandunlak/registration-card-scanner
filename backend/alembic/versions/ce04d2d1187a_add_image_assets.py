"""Add project-scoped image metadata without altering registration records."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ce04d2d1187a"
down_revision: Union[str, Sequence[str], None] = "82cd8eccfd83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "imageasset" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "imageasset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("original_key", sa.String(length=1024), nullable=False),
        sa.Column("processed_key", sa.String(length=1024), nullable=True),
        sa.Column("variant_keys", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="uploaded"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("rotation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crop", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["record_id"], ["registrationrecord.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", name="uq_imageasset_record_id"),
    )
    op.create_index("ix_imageasset_project_id", "imageasset", ["project_id"])
    op.create_index("ix_imageasset_status", "imageasset", ["status"])


def downgrade() -> None:
    op.drop_table("imageasset")