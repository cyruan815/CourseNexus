from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.materials.router import get_material_storage, get_rag_index


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    rag_index = FakeRagIndex()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_material_storage] = lambda: LocalFileStorage(
        root_path=tmp_path,
        max_file_size_bytes=1024,
    )
    app.dependency_overrides[get_rag_index] = lambda: rag_index
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def create_course(client: TestClient, token: str, name: str = "Linear Algebra") -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_upload_list_detail_and_delete_file_material(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    upload_response = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro", "application/octet-stream")},
    )

    assert upload_response.status_code == 200
    material = upload_response.json()["data"]
    material_id = material["id"]
    assert material["name"] == "notes.md"
    assert material["source_type"] == "file"
    assert material["material_type"] == "markdown"
    assert material["parse_status"] == "uploaded"
    assert material["parse_quality"] == "unknown"
    assert material["parse_diagnostics_json"] is None

    list_response = client.get(f"/api/v1/courses/{course_id}/materials", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["data"]] == [material_id]

    detail_response = client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == material_id

    rename_response = client.patch(
        f"/api/v1/materials/{material_id}",
        headers=headers,
        json={"name": "  第一章笔记.md  "},
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["data"]["name"] == "第一章笔记.md"
    assert rename_response.json()["data"]["file_url"] == material["file_url"]
    assert rename_response.json()["data"]["parse_status"] == "uploaded"

    delete_response = client.delete(f"/api/v1/materials/{material_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["parse_status"] == "deleted"

    assert client.get(f"/api/v1/courses/{course_id}/materials", headers=headers).json()["data"] == []


def test_create_link_material(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/material-links",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Course Site", "source_url": "https://example.com/course"},
    )

    assert response.status_code == 200
    material = response.json()["data"]
    assert material["source_type"] == "url"
    assert material["material_type"] == "link"
    assert material["source_url"] == "https://example.com/course"


def test_parse_retry_parses_uploaded_text_material(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro\nAlpha\n", "text/markdown")},
    )
    material_id = upload_response.json()["data"]["id"]

    parse_response = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)

    assert parse_response.status_code == 200
    parsed = parse_response.json()["data"]
    assert parsed["parse_status"] == "parsed"
    assert parsed["parse_error"] is None
    assert parsed["parse_quality"] == "complete"
    assert parsed["parse_diagnostics_json"]["parser"] == "plain_text"
    assert parsed["parse_diagnostics_json"]["warnings"] == []


def test_material_detail_does_not_cross_user_boundary(client: TestClient) -> None:
    alice_token = register_and_token(client, "alice")
    bob_token = register_and_token(client, "bob")
    bob_course_id = create_course(client, bob_token, "Databases")
    bob_upload = client.post(
        f"/api/v1/courses/{bob_course_id}/materials",
        headers={"Authorization": f"Bearer {bob_token}"},
        files={"file": ("bob.txt", b"bob notes", "text/plain")},
    )
    bob_material_id = bob_upload.json()["data"]["id"]

    response = client.get(
        f"/api/v1/materials/{bob_material_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

    rename_response = client.patch(
        f"/api/v1/materials/{bob_material_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"name": "stolen.txt"},
    )
    assert rename_response.status_code == 404
    assert rename_response.json()["error"]["code"] == "NOT_FOUND"


def test_upload_rejects_unsafe_filename(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("../evil.md", b"# Intro", "text/markdown")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_material_folder_crud_and_material_move_flow(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    week_one_response = client.post(
        f"/api/v1/courses/{course_id}/material-folders",
        headers=headers,
        json={"name": "第一周"},
    )
    week_two_response = client.post(
        f"/api/v1/courses/{course_id}/material-folders",
        headers=headers,
        json={"name": "第二周"},
    )

    assert week_one_response.status_code == 200
    assert week_two_response.status_code == 200
    week_one = week_one_response.json()["data"]
    week_two = week_two_response.json()["data"]
    assert week_one["sort_order"] == 1
    assert week_two["sort_order"] == 2

    update_response = client.patch(
        f"/api/v1/material-folders/{week_two['id']}",
        headers=headers,
        json={"name": "考试重点", "sort_order": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "考试重点"

    list_response = client.get(f"/api/v1/courses/{course_id}/material-folders", headers=headers)
    assert list_response.status_code == 200
    assert {folder["id"] for folder in list_response.json()["data"]} == {week_one["id"], week_two["id"]}

    upload_response = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro", "text/markdown")},
    )
    material_id = upload_response.json()["data"]["id"]

    move_response = client.patch(
        f"/api/v1/materials/{material_id}/folder",
        headers=headers,
        json={"folder_id": week_one["id"]},
    )
    assert move_response.status_code == 200
    assert move_response.json()["data"]["folder_id"] == week_one["id"]

    delete_response = client.delete(f"/api/v1/material-folders/{week_one['id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted_at"] is not None

    material_response = client.get(f"/api/v1/materials/{material_id}", headers=headers)
    assert material_response.status_code == 404

    list_materials_response = client.get(f"/api/v1/courses/{course_id}/materials", headers=headers)
    assert list_materials_response.status_code == 200
    assert list_materials_response.json()["data"] == []


def test_material_folder_endpoints_do_not_cross_user_boundary(client: TestClient) -> None:
    alice_token = register_and_token(client, "alice")
    bob_token = register_and_token(client, "bob")
    alice_course_id = create_course(client, alice_token, "Linear Algebra")
    bob_course_id = create_course(client, bob_token, "Databases")
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    bob_folder = client.post(
        f"/api/v1/courses/{bob_course_id}/material-folders",
        headers=bob_headers,
        json={"name": "Bob Folder"},
    ).json()["data"]
    alice_material = client.post(
        f"/api/v1/courses/{alice_course_id}/materials",
        headers=alice_headers,
        files={"file": ("notes.md", b"# Intro", "text/markdown")},
    ).json()["data"]

    update_response = client.patch(
        f"/api/v1/material-folders/{bob_folder['id']}",
        headers=alice_headers,
        json={"name": "Stolen"},
    )
    move_response = client.patch(
        f"/api/v1/materials/{alice_material['id']}/folder",
        headers=alice_headers,
        json={"folder_id": bob_folder["id"]},
    )

    assert update_response.status_code == 404
    assert move_response.status_code == 404
