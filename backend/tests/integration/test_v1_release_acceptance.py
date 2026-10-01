from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401
from app.commands.reconcile_storage import reconcile_storage
from app.core.errors import CourseNexusError
from app.db.base import Base
from app.db.session import get_db
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.base import ParsedDocument
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.course_qa import router as course_qa_router
from app.modules.generation.orchestrator import router as generation_router
from app.modules.materials import router as materials_router
from app.modules.study_plans import router as study_plan_router


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "release_samples" / "limits-and-continuity.txt"
MATERIAL_PATTERN = re.compile(r"mat_[0-9a-f]{32}")
CHUNK_PATTERN = re.compile(r"chk_[0-9a-f_]+")


class SwitchableReleaseParser:
    def __init__(self) -> None:
        self.fail = False
        self.delegate = PlainTextParser()

    def parse(self, file_path: Path) -> ParsedDocument:
        if self.fail:
            raise CourseNexusError(code="PARSE_FAILED", message="Injected release parse failure", status_code=500)
        return self.delegate.parse(file_path)


class ReleaseOutlineProvider:
    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        assert output_schema.__name__ == "OutlineGenerationResult"
        return output_schema.model_validate(
            {
                "topic_title": "极限与连续",
                "sections": [
                    {
                        "title": "极限的直观含义",
                        "summary": "极限描述函数在输入附近趋近的值。",
                        "review_suggestion": "先复述定义，再检查连续性的三个条件。",
                    }
                ],
            }
        )


class ReleasePlanProvider:
    def __init__(self) -> None:
        self.material_id: str | None = None
        self.chunk_id: str | None = None

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        material_match = MATERIAL_PATTERN.search(prompt)
        chunk_match = CHUNK_PATTERN.search(prompt)
        if material_match:
            self.material_id = material_match.group(0)
        if chunk_match:
            self.chunk_id = chunk_match.group(0)
        assert self.material_id is not None
        assert self.chunk_id is not None

        if output_schema.__name__ == "PlanBatchExtraction":
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "Limits and continuity",
                            "summary": "Understand the limit definition and the three continuity conditions.",
                            "difficulty": "medium",
                            "estimated_minutes": 30,
                            "related_material_ids": [self.material_id],
                            "citation_chunk_ids": [self.chunk_id],
                        }
                    ],
                    "citation_chunk_ids": [self.chunk_id],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            return output_schema.model_validate(
                {
                    "title": "Limits and Continuity Review",
                    "tasks": [
                        {
                            "title": "Limits and continuity",
                            "task_date": "2026-10-01",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "Study the core concept",
                                    "subtask_type": "learn",
                                    "description": "Review the definition and continuity conditions.",
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 30,
                                    "citation_chunk_ids": [self.chunk_id],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "Check understanding",
                                    "subtask_type": "test",
                                    "description": "Check the full scope for the day.",
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": [self.chunk_id],
                                    "sort_order": 2,
                                },
                            ],
                        }
                    ],
                    "citation_chunk_ids": [self.chunk_id],
                }
            )
        raise AssertionError(output_schema)


@dataclass
class ReleaseHarness:
    client: TestClient
    db: Session
    storage: LocalFileStorage
    rag_index: FakeRagIndex
    parser: SwitchableReleaseParser


@pytest.fixture()
def release_harness(tmp_path: Path) -> Generator[ReleaseHarness, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'release.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = testing_session()
    storage = LocalFileStorage(root_path=tmp_path / "uploads", max_file_size_bytes=256 * 1024)
    rag_index = FakeRagIndex()
    parser = SwitchableReleaseParser()
    plan_provider = ReleasePlanProvider()

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[materials_router.get_material_storage] = lambda: storage
    app.dependency_overrides[materials_router.get_material_parser] = lambda: parser
    app.dependency_overrides[materials_router.get_rag_index] = lambda: rag_index
    app.dependency_overrides[course_qa_router.get_retrieval_rag_index] = lambda: rag_index
    app.dependency_overrides[course_qa_router.get_model_provider] = lambda: MockModelProvider()
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda _content_type: ReleaseOutlineProvider()
    )
    app.dependency_overrides[study_plan_router.get_plan_generator_provider] = lambda: plan_provider
    app.dependency_overrides[study_plan_router.get_plan_map_provider] = lambda: plan_provider
    try:
        yield ReleaseHarness(
            client=TestClient(app),
            db=db,
            storage=storage,
            rag_index=rag_index,
            parser=parser,
        )
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def _register(client: TestClient, username: str) -> None:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200, response.text


def _login_headers(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _explicit_scope(material_id: str) -> dict[str, object]:
    return {"include_all_parsed_materials": False, "material_ids": [material_id]}


def test_v1_release_flow_preserves_evidence_across_reparse_failure_and_delete(
    release_harness: ReleaseHarness,
) -> None:
    client = release_harness.client
    _register(client, "release-owner")
    owner_headers = _login_headers(client, "release-owner")
    _register(client, "release-outsider")
    outsider_headers = _login_headers(client, "release-outsider")

    course_response = client.post(
        "/api/v1/courses",
        headers=owner_headers,
        json={"name": "Calculus V1"},
    )
    assert course_response.status_code == 200, course_response.text
    course_id = course_response.json()["data"]["id"]

    sample_bytes = SAMPLE_PATH.read_bytes()
    upload_response = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=owner_headers,
        files={"file": (SAMPLE_PATH.name, sample_bytes, "text/plain")},
    )
    assert upload_response.status_code == 200, upload_response.text
    material_id = upload_response.json()["data"]["id"]

    parse_response = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=owner_headers)
    assert parse_response.status_code == 200, parse_response.text
    parsed_material = parse_response.json()["data"]
    assert parsed_material["parse_status"] == "parsed"
    assert parsed_material["is_learning_ready"] is True
    active_version_id = parsed_material["active_parse_version_id"]
    assert active_version_id

    content_response = client.get(f"/api/v1/materials/{material_id}/content", headers=owner_headers)
    assert content_response.status_code == 200
    assert content_response.content == sample_bytes
    assert content_response.headers["cache-control"] == "private, no-store"

    denied_response = client.get(f"/api/v1/materials/{material_id}", headers=outsider_headers)
    assert denied_response.status_code == 404
    assert denied_response.json()["error"]["code"] == "NOT_FOUND"

    qa_response = client.post(
        f"/api/v1/courses/{course_id}/qa/questions",
        headers=owner_headers,
        json={
            "question": "What value does a limit describe?",
            "material_scope": _explicit_scope(material_id),
            "source_page": "course_detail",
        },
    )
    assert qa_response.status_code == 200, qa_response.text
    answer = qa_response.json()["data"]
    assert answer["answer_type"] == "grounded"
    assert answer["source_citations"][0]["material_version_id"] == active_version_id

    generation_response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=owner_headers,
        json={
            "content_type": "outline",
            "material_scope": _explicit_scope(material_id),
            "parameters": {"section_count": 1},
        },
    )
    assert generation_response.status_code == 200, generation_response.text
    generated = generation_response.json()["data"]
    assert generated["generation_status"] == "success"
    assert generated["material_scope_json"]["material_versions"] == [
        {"material_id": material_id, "version_id": active_version_id}
    ]

    preview_response = client.post(
        f"/api/v1/courses/{course_id}/study-plans/preview",
        headers=owner_headers,
        json={
            "goal_text": "Review limits and continuity",
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "daily_available_minutes": 60,
            "material_scope": _explicit_scope(material_id),
        },
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()["data"]
    assert preview["material_snapshot"]["material_versions"] == [
        {"material_id": material_id, "version_id": active_version_id}
    ]

    save_payload = dict(preview)
    save_payload.pop("course_id")
    save_payload["client_flow"] = "wizard_v1"
    save_payload["title"] = "Limits Review 2026-10-01"
    save_response = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers={**owner_headers, "Idempotency-Key": "release-plan-2026-10-01"},
        json=save_payload,
    )
    assert save_response.status_code == 200, save_response.text
    saved_plan = save_response.json()["data"]
    plan_id = saved_plan["plan"]["id"]
    assert saved_plan["plan"]["title"] == "Limits Review 2026-10-01"
    assert [subtask["subtask_type"] for subtask in saved_plan["subtasks"]] == ["learn", "test"]

    release_harness.parser.fail = True
    failed_reparse_response = client.post(
        f"/api/v1/materials/{material_id}/parse-retries",
        headers=owner_headers,
    )
    assert failed_reparse_response.status_code == 200, failed_reparse_response.text
    failed_reparse = failed_reparse_response.json()["data"]
    assert failed_reparse["active_parse_version_id"] == active_version_id
    assert failed_reparse["is_learning_ready"] is True
    assert failed_reparse["parse_error"] == "PARSE_FAILED"

    qa_after_failure = client.post(
        f"/api/v1/courses/{course_id}/qa/questions",
        headers=owner_headers,
        json={
            "question": "Which continuity conditions must hold?",
            "material_scope": _explicit_scope(material_id),
            "source_page": "course_detail",
        },
    )
    assert qa_after_failure.status_code == 200, qa_after_failure.text
    assert qa_after_failure.json()["data"]["answer_type"] == "grounded"

    delete_response = client.delete(f"/api/v1/materials/{material_id}", headers=owner_headers)
    assert delete_response.status_code == 200, delete_response.text
    assert client.get(f"/api/v1/materials/{material_id}", headers=owner_headers).status_code == 404

    generated_after_delete = client.get(
        f"/api/v1/generated-contents/{generated['id']}",
        headers=owner_headers,
    )
    assert generated_after_delete.status_code == 200
    assert generated_after_delete.json()["data"]["material_scope_json"]["material_versions"] == [
        {"material_id": material_id, "version_id": active_version_id}
    ]
    plan_after_delete = client.get(f"/api/v1/study-plans/{plan_id}", headers=owner_headers)
    assert plan_after_delete.status_code == 200
    messages_after_delete = client.get(
        f"/api/v1/conversations/{answer['conversation_id']}/messages",
        headers=owner_headers,
    )
    assert messages_after_delete.status_code == 200
    assistant_message = next(
        message for message in messages_after_delete.json()["data"] if message["role"] == "assistant"
    )
    assert assistant_message["source_citations"][0]["material_id"] is None
    assert assistant_message["source_citations"][0]["material_name"] == SAMPLE_PATH.name

    release_harness.db.expire_all()
    report = reconcile_storage(
        db=release_harness.db,
        storage_root=release_harness.storage.root_path,
        rag_records=release_harness.rag_index.list_records(),
    )
    assert report.status == "notices"
    assert report.inconsistency_count == 0
    assert {issue.code for issue in report.issues} == {"PARSE_VERSION_RETAINED"}
    assert {issue.details["status"] for issue in report.issues} == {"failed"}
