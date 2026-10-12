"""Comprehensive tests for Project, Field, and Record endpoints and data integrity."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_projects(client: AsyncClient):
    """Test creating and listing projects."""
    res = await client.post(
        "/api/projects",
        json={"name": "Test Intake", "event_name": "Kandy Fair", "description": "October intake"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test Intake"
    assert data["event_name"] == "Kandy Fair"
    assert data["status"] == "active"
    proj_id = data["id"]

    # List projects
    list_res = await client.get("/api/projects")
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) >= 1
    assert any(p["id"] == proj_id for p in projects)


@pytest.mark.asyncio
async def test_update_and_archive_project(client: AsyncClient):
    """Test updating and archiving/restoring a project."""
    res = await client.post("/api/projects", json={"name": "To Archive"})
    proj_id = res.json()["id"]

    # Update project
    patch_res = await client.patch(
        f"/api/projects/{proj_id}",
        json={"name": "Archivable Project", "event_name": "Updated Event"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Archivable Project"

    # Archive project
    archive_res = await client.post(f"/api/projects/{proj_id}/archive")
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "archived"

    # Filter active projects
    active_res = await client.get("/api/projects?status=active")
    assert not any(p["id"] == proj_id for p in active_res.json())

    # Restore project
    restore_res = await client.post(f"/api/projects/{proj_id}/restore")
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "active"


@pytest.mark.asyncio
async def test_project_fields_crud_and_reorder(client: AsyncClient):
    """Test creating, updating, reordering, and deleting fields."""
    res = await client.post("/api/projects", json={"name": "Fields Project"})
    proj_id = res.json()["id"]

    # Add field 1
    f1_res = await client.post(
        f"/api/projects/{proj_id}/fields",
        json={
            "field_key": "full_name",
            "field_label": "Full Name",
            "field_type": "text",
            "required": True,
        },
    )
    assert f1_res.status_code == 201
    f1_id = f1_res.json()["id"]

    # Add field 2
    f2_res = await client.post(
        f"/api/projects/{proj_id}/fields",
        json={
            "field_key": "mobile_phone",
            "field_label": "Mobile Phone",
            "field_type": "phone",
            "required": True,
        },
    )
    assert f2_res.status_code == 201
    f2_id = f2_res.json()["id"]

    # Prevent duplicate field_key in same project
    dup_res = await client.post(
        f"/api/projects/{proj_id}/fields",
        json={
            "field_key": "full_name",
            "field_label": "Duplicate Full Name",
            "field_type": "text",
        },
    )
    assert dup_res.status_code == 422

    # Update field 1
    patch_res = await client.patch(
        f"/api/projects/{proj_id}/fields/{f1_id}",
        json={"field_label": "Student Full Name"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["field_label"] == "Student Full Name"

    # Reorder fields
    reorder_res = await client.post(
        f"/api/projects/{proj_id}/fields/reorder",
        json={"field_ids": [f2_id, f1_id]},
    )
    assert reorder_res.status_code == 200
    ordered = reorder_res.json()
    assert ordered[0]["id"] == f2_id
    assert ordered[1]["id"] == f1_id

    # Delete field
    del_res = await client.delete(f"/api/projects/{proj_id}/fields/{f1_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_preserve_phone_leading_zeros_and_record_crud(client: AsyncClient):
    """Test that phone numbers preserve leading zeros strictly as strings and record CRUD works."""
    p_res = await client.post(
        "/api/projects",
        json={
            "name": "Intake Records",
            "fields": [
                {
                    "field_key": "phone_num",
                    "field_label": "Phone Number",
                    "field_type": "phone",
                    "required": True,
                },
                {
                    "field_key": "notes",
                    "field_label": "Notes",
                    "field_type": "text",
                    "required": False,
                },
            ],
        },
    )
    proj_id = p_res.json()["id"]

    # Create record with leading zero phone number
    rec_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "phone_num": "0771234567",
                "notes": "Handwritten card #12",
            },
            "review_status": "pending",
        },
    )
    assert rec_res.status_code == 201
    rec = rec_res.json()
    rec_id = rec["id"]

    # Assert string preservation with leading zero
    assert rec["extracted_data"]["phone_num"] == "0771234567"
    assert isinstance(rec["extracted_data"]["phone_num"], str)

    # Fetch record
    get_res = await client.get(f"/api/projects/{proj_id}/records/{rec_id}")
    assert get_res.status_code == 200
    assert get_res.json()["extracted_data"]["phone_num"] == "0771234567"

    # Update record status to reviewed
    patch_res = await client.patch(
        f"/api/projects/{proj_id}/records/{rec_id}",
        json={"review_status": "reviewed"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["review_status"] == "reviewed"

    # List records with pagination
    list_res = await client.get(f"/api/projects/{proj_id}/records?page=1&limit=10")
    assert list_res.status_code == 200
    res_data = list_res.json()
    assert res_data["total"] == 1
    assert res_data["page"] == 1
    assert len(res_data["items"]) == 1


@pytest.mark.asyncio
async def test_required_and_invalid_fields(client: AsyncClient):
    """Test validation rejection for missing required fields and invalid types."""
    p_res = await client.post(
        "/api/projects",
        json={
            "name": "Strict Validation Project",
            "fields": [
                {
                    "field_key": "student_name",
                    "field_label": "Student Name",
                    "field_type": "text",
                    "required": True,
                },
                {
                    "field_key": "contact_no",
                    "field_label": "Contact Number",
                    "field_type": "phone",
                    "required": True,
                },
                {
                    "field_key": "age",
                    "field_label": "Age",
                    "field_type": "number",
                    "required": False,
                    "validation_config": {"min_value": 16, "max_value": 70},
                },
                {
                    "field_key": "email",
                    "field_label": "Email Address",
                    "field_type": "email",
                    "required": False,
                },
                {
                    "field_key": "intake_choice",
                    "field_label": "Intake Choice",
                    "field_type": "single_select",
                    "required": False,
                    "validation_config": {"options": ["January", "May", "September"]},
                },
            ],
        },
    )
    proj_id = p_res.json()["id"]

    # 1. Missing required field (student_name missing)
    missing_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={"extracted_data": {"contact_no": "0719876543"}},
    )
    assert missing_res.status_code == 422
    assert "Student Name" in missing_res.json()["detail"]

    # 2. Invalid phone format (contains letters)
    bad_phone_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "student_name": "Kamal",
                "contact_no": "071abc456",
            }
        },
    )
    assert bad_phone_res.status_code == 422
    assert "phone" in bad_phone_res.json()["detail"].lower()

    # 3. Invalid number
    bad_num_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "student_name": "Kamal",
                "contact_no": "0719876543",
                "age": "not-a-number",
            }
        },
    )
    assert bad_num_res.status_code == 422

    # 4. Out of bounds number
    oob_num_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "student_name": "Kamal",
                "contact_no": "0719876543",
                "age": 12,
            }
        },
    )
    assert oob_num_res.status_code == 422

    # 5. Invalid single select option
    bad_opt_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "student_name": "Kamal",
                "contact_no": "0719876543",
                "intake_choice": "December",
            }
        },
    )
    assert bad_opt_res.status_code == 422

    # 6. Invalid email
    bad_email_res = await client.post(
        f"/api/projects/{proj_id}/records",
        json={
            "extracted_data": {
                "student_name": "Kamal",
                "contact_no": "0719876543",
                "email": "invalid-email-string",
            }
        },
    )
    assert bad_email_res.status_code == 422


@pytest.mark.asyncio
async def test_missing_ids_and_cross_project_protection(client: AsyncClient):
    """Test 404 for missing resources and strict prevention of cross-project access."""
    # Create Project A
    pa = (await client.post("/api/projects", json={"name": "Project A"})).json()
    pa_id = pa["id"]

    # Create Project B
    pb = (await client.post("/api/projects", json={"name": "Project B"})).json()
    pb_id = pb["id"]

    # Add field to Project A
    fa = (
        await client.post(
            f"/api/projects/{pa_id}/fields",
            json={"field_key": "name_a", "field_label": "Name A", "field_type": "text"},
        )
    ).json()
    fa_id = fa["id"]

    # Add record to Project A
    ra = (
        await client.post(
            f"/api/projects/{pa_id}/records",
            json={"extracted_data": {"name_a": "Person A"}},
        )
    ).json()
    ra_id = ra["id"]

    # Non-existent project
    assert (await client.get("/api/projects/999999")).status_code == 404
    assert (await client.get("/api/projects/999999/records")).status_code == 404
    assert (await client.get("/api/projects/999999/fields")).status_code == 404

    # Non-existent record / field
    assert (await client.get(f"/api/projects/{pa_id}/records/999999")).status_code == 404
    assert (await client.get(f"/api/projects/{pa_id}/fields/999999")).status_code == 404

    # CROSS-PROJECT ACCESS PREVENTION:
    # Attempt to access Project A's record via Project B
    cross_rec = await client.get(f"/api/projects/{pb_id}/records/{ra_id}")
    assert cross_rec.status_code == 404
    assert "not found in project" in cross_rec.json()["detail"].lower()

    # Attempt to patch Project A's record via Project B
    cross_patch = await client.patch(
        f"/api/projects/{pb_id}/records/{ra_id}",
        json={"review_status": "reviewed"},
    )
    assert cross_patch.status_code == 404

    # Attempt to access Project A's field via Project B
    cross_field = await client.get(f"/api/projects/{pb_id}/fields/{fa_id}")
    assert cross_field.status_code == 404

    # Attempt to delete Project A's field via Project B
    cross_del = await client.delete(f"/api/projects/{pb_id}/fields/{fa_id}")
    assert cross_del.status_code == 404


@pytest.mark.asyncio
async def test_database_initialization_and_backup(tmp_path):
    """Test that database initialization is idempotent and backup utility works."""
    from app.core.database import create_db_and_tables
    from app.core.backup import create_backup

    # Initializing again should be completely idempotent and not raise errors
    await create_db_and_tables()

    # Test online backup creation
    backup_file = create_backup(destination_dir=tmp_path)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

