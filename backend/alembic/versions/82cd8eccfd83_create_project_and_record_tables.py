"""create_project_and_record_tables

Revision ID: 82cd8eccfd83
Revises: 
Create Date: 2026-10-13 01:21:56.411359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82cd8eccfd83'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely checking if tables already exist."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "project" not in existing_tables:
        op.create_table(
            "project",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("event_name", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_project_name", "project", ["name"], unique=False)
        op.create_index("ix_project_status", "project", ["status"], unique=False)

    if "projectfield" not in existing_tables:
        op.create_table(
            "projectfield",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("field_key", sa.String(length=100), nullable=False),
            sa.Column("field_label", sa.String(length=255), nullable=False),
            sa.Column("field_type", sa.String(length=50), nullable=False),
            sa.Column("required", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("validation_config", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", "field_key", name="uq_project_field_key"),
        )
        op.create_index("ix_projectfield_project_id", "projectfield", ["project_id"], unique=False)
        op.create_index("ix_projectfield_field_key", "projectfield", ["field_key"], unique=False)
        op.create_index("ix_projectfield_display_order", "projectfield", ["display_order"], unique=False)

    if "registrationrecord" not in existing_tables:
        op.create_table(
            "registrationrecord",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("source_image_path", sa.String(length=1024), nullable=True),
            sa.Column("extracted_data", sa.JSON(), nullable=False),
            sa.Column("review_status", sa.String(length=50), server_default="pending", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_registrationrecord_project_id", "registrationrecord", ["project_id"], unique=False)
        op.create_index("ix_registrationrecord_review_status", "registrationrecord", ["review_status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("registrationrecord")
    op.drop_table("projectfield")
    op.drop_table("project")
