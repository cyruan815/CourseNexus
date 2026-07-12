from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.modules.generation.orchestrator.router as generation_router
from app.core.config import ModelEndpointConfig
from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.main import app
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator
from app.modules.generation.generators.outline.schemas import OutlineMapResult
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.generation.orchestrator.registry import GeneratorRegistry


SUPPORTED_CONTENT_TYPES = ("flashcard", "knowledge_list", "mindmap", "outline", "quiz")


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def create_course(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": "Linear Algebra"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def upload_and_parse_material(client: TestClient, token: str, course_id: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro\nAlpha\n", "text/markdown")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]
    parse = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parse.status_code == 200
    return material_id


@pytest.mark.parametrize("content_type", SUPPORTED_CONTENT_TYPES)
def test_generation_model_provider_uses_content_type_endpoint_and_openai_configuration(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
) -> None:
    requested_purposes: list[str] = []
    captured: dict[str, object] = {}

    class FakeSettings:
        def model_endpoint(self, purpose: str) -> ModelEndpointConfig:
            requested_purposes.append(purpose)
            return ModelEndpointConfig(
                api_key=f"{content_type}-key",
                base_url=f"https://{content_type}.example/v1",
                model=f"{content_type}-model",
            )

    class FakeProvider:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(generation_router, "get_settings", FakeSettings)
    monkeypatch.setattr(generation_router, "OpenAIModelProvider", FakeProvider)

    provider = generation_router.get_generation_model_provider(content_type)

    assert isinstance(provider, FakeProvider)
    assert requested_purposes == [content_type]
    assert captured == {
        "api_key": f"{content_type}-key",
        "model": f"{content_type}-model",
        "base_url": f"https://{content_type}.example/v1",
        "api_key_env_name": f"{content_type.upper()}_API_KEY",
    }


@pytest.mark.parametrize("content_type", SUPPORTED_CONTENT_TYPES)
def test_generation_model_provider_uses_mock_without_purpose_specific_key(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
) -> None:
    requested_purposes: list[str] = []

    class FakeSettings:
        def model_endpoint(self, purpose: str) -> ModelEndpointConfig:
            requested_purposes.append(purpose)
            return ModelEndpointConfig(api_key=None, base_url=None, model=f"{content_type}-model")

    monkeypatch.setattr(generation_router, "get_settings", FakeSettings)

    provider = generation_router.get_generation_model_provider(content_type)

    assert isinstance(provider, MockModelProvider)
    assert requested_purposes == [content_type]


def test_generation_model_provider_factory_returns_provider_callable() -> None:
    factory = generation_router.get_generation_model_provider_factory()

    assert callable(factory)
    assert factory is generation_router.get_generation_model_provider


def test_generation_model_provider_factory_is_overridable_endpoint_dependency(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_and_token(client, "provider-override")
    course_id = create_course(client, token)
    provider = MockModelProvider()
    requested_content_types: list[str] = []

    def provider_factory(content_type: str) -> MockModelProvider:
        requested_content_types.append(content_type)
        return provider

    def fake_generate_content(
        db: Session,
        *,
        user_id: str,
        course_id: str,
        payload: object,
        registry: object,
        model_provider: object,
        max_batch_tokens: int,
    ) -> SimpleNamespace:
        assert model_provider is provider
        assert max_batch_tokens > 0
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id="gen-provider-override",
            user_id=user_id,
            course_id=course_id,
            study_subtask_id=None,
            source_message_id=None,
            content_type="outline",
            title="Outline",
            content="Body",
            content_json={"items": []},
            generation_status="success",
            material_scope_json={},
            error_code=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: provider_factory
    monkeypatch.setattr(generation_router, "generate_content", fake_generate_content)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "outline"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "gen-provider-override"
    assert requested_content_types == ["outline"]


def test_default_generation_provider_rejects_unconfigured_custom_purpose(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_and_token(client, "custom-default-provider")
    course_id = create_course(client, token)
    registry = GeneratorRegistry()
    registry.register("note", lambda provider: PlaceholderGenerator(content_type="note", model_provider=provider))

    class UnexpectedSettings:
        def model_endpoint(self, purpose: str) -> ModelEndpointConfig:
            raise AssertionError(f"unexpected model endpoint lookup: {purpose}")

    app.dependency_overrides[generation_router.get_generator_registry] = lambda: registry
    app.dependency_overrides.pop(generation_router.get_generation_model_provider_factory)
    monkeypatch.setattr(generation_router, "get_settings", UnexpectedSettings)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "note"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "VALIDATION_ERROR",
        "message": "Generation model purpose is not configured",
        "details": {"content_type": "note"},
    }


def test_custom_registry_type_works_with_overridden_provider_factory(
    client: TestClient,
) -> None:
    token = register_and_token(client, "custom-provider-override")
    course_id = create_course(client, token)
    upload_and_parse_material(client, token, course_id)
    registry = GeneratorRegistry()
    provider = MockModelProvider()
    received_providers: list[ModelProvider] = []

    def build_note_generator(received_provider: ModelProvider) -> PlaceholderGenerator:
        received_providers.append(received_provider)
        return PlaceholderGenerator(content_type="note", model_provider=received_provider)

    registry.register("note", build_note_generator)
    app.dependency_overrides[generation_router.get_generator_registry] = lambda: registry
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: (
        lambda content_type: provider
    )

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "note"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["content_type"] == "note"
    assert response.json()["data"]["generation_status"] == "success"
    assert received_providers == [provider]


def test_generation_api_rejects_unsupported_type_before_provider_construction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_and_token(client, "unsupported-provider")
    course_id = create_course(client, token)
    requested_purposes: list[str] = []

    class FakeSettings:
        def model_endpoint(self, purpose: str) -> ModelEndpointConfig:
            requested_purposes.append(purpose)
            raise AssertionError("unsupported content type reached model configuration")

    monkeypatch.setattr(generation_router, "get_settings", FakeSettings)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert requested_purposes == []


def test_generation_api_creates_and_reads_generated_content(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnexpectedOpenAIProvider:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("API fixture must not construct a live-capable provider")

    monkeypatch.setattr(generation_router, "OpenAIModelProvider", UnexpectedOpenAIProvider)
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(client, token, course_id)
    headers = {"Authorization": f"Bearer {token}"}
    chunk_id = f"chk_{material_id.removeprefix('mat_')}_000000"
    provider = MockModelProvider(
        structured_outputs={
            OutlineMapResult: {
                "candidates": [
                    {
                        "title": "Introduction",
                        "summary": "Alpha",
                        "review_suggestion": "Review Alpha",
                        "source_order_key": "000001",
                        "source_chunk_ids": [chunk_id],
                    }
                ]
            }
        }
    )
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: provider
    )

    generation = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=headers,
        json={"content_type": "outline"},
    )

    assert generation.status_code == 200
    generated_content = generation.json()["data"]
    assert generated_content["generation_status"] == "success"
    assert generated_content["content_type"] == "outline"
    assert len(generated_content["source_citations"]) == 1
    citation = generated_content["source_citations"][0]
    assert set(citation) == {
        "id",
        "material_id",
        "chunk_id",
        "material_name",
        "page",
        "page_index",
        "hit_text",
        "sort_order",
    }
    assert citation["id"].startswith("cit_")
    assert citation["material_id"] == material_id
    assert citation["chunk_id"] == chunk_id
    assert citation["material_name"] == "notes.md"
    assert citation["page"] is None
    assert citation["page_index"] == 0
    assert "Alpha" in citation["hit_text"]
    assert citation["sort_order"] == 1

    listed = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [generated_content["id"]]
    assert listed.json()["data"][0]["source_citations"] == [citation]

    detail = client.get(f"/api/v1/generated-contents/{generated_content['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == generated_content["id"]
    assert detail.json()["data"]["source_citations"] == [citation]


def test_generation_api_returns_empty_citation_array_when_none_are_persisted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = register_and_token(client, "no-citations")
    course_id = create_course(client, token)

    def fake_generate_content(
        db: Session,
        *,
        user_id: str,
        course_id: str,
        payload: object,
        registry: object,
        model_provider: object,
        max_batch_tokens: int,
    ) -> SimpleNamespace:
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id="gen-no-citations",
            user_id=user_id,
            course_id=course_id,
            study_subtask_id=None,
            source_message_id=None,
            content_type="outline",
            title="Outline",
            content="Body",
            content_json={"items": []},
            generation_status="success",
            material_scope_json={},
            error_code=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

    monkeypatch.setattr(generation_router, "generate_content", fake_generate_content)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "outline"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["source_citations"] == []


def test_generation_api_rejects_unknown_content_type(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers={"Authorization": f"Bearer {token}"},
        json={"content_type": "unknown"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_generation_api_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/courses/course-id/generations", json={"content_type": "outline"})

    assert response.status_code == 401


def test_generation_api_hides_other_users_course(
    client: TestClient,
    alice_api,
    bob_api,
    api_course_factory,
    api_material_factory,
) -> None:
    course_id = api_course_factory(alice_api)
    material_id = api_material_factory(alice_api, course_id)

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=bob_api.headers,
        json={
            "content_type": "outline",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )

    assert response.status_code == 404


def test_generation_api_hides_other_users_explicit_material_scope(
    client: TestClient,
    alice_api,
    bob_api,
    api_course_factory,
    api_material_factory,
) -> None:
    alice_course_id = api_course_factory(alice_api)
    alice_material_id = api_material_factory(alice_api, alice_course_id)
    bob_course_id = api_course_factory(bob_api, name="Databases")

    response = client.post(
        f"/api/v1/courses/{bob_course_id}/generations",
        headers=bob_api.headers,
        json={
            "content_type": "outline",
            "material_scope": {
                "include_all_parsed_materials": False,
                "material_ids": [alice_material_id],
            },
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "material_scope",
    [None, {"include_all_parsed_materials": False, "material_ids": []}],
)
def test_generation_api_rejects_no_parsed_material_and_explicit_empty_scope(
    client: TestClient,
    alice_api,
    api_course_factory,
    material_scope: dict[str, object] | None,
) -> None:
    course_id = api_course_factory(alice_api)
    payload: dict[str, object] = {"content_type": "outline"}
    if material_scope is not None:
        payload["material_scope"] = material_scope

    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json=payload
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_PARSED_MATERIAL"


def test_generator_validation_error_does_not_persist_record(
    client: TestClient,
    sqlite_engine: Engine,
    alice_api,
    api_course_factory,
    api_material_factory,
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)

    class ValidationGenerator:
        content_type = "outline"

        def generate(self, *, batches, expected_material_ids, parameters) -> GeneratorOutput:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Bad parameters", status_code=422)

    registry = GeneratorRegistry()
    registry.register("outline", lambda provider: ValidationGenerator())
    app.dependency_overrides[generation_router.get_generator_registry] = lambda: registry

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=alice_api.headers,
        json={"content_type": "outline"},
    )

    assert response.status_code == 422
    with Session(sqlite_engine) as session:
        assert list(session.execute(select(AIGeneratedContent)).scalars()) == []


def test_failed_generation_can_be_listed_and_read_without_content_or_citations(
    client: TestClient,
    alice_api,
    api_course_factory,
    api_material_factory,
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)

    class FailingGenerator:
        content_type = "outline"

        def generate(self, *, batches, expected_material_ids, parameters) -> GeneratorOutput:
            raise CourseNexusError(
                code="GENERATION_FAILED", message="Stable generator failure", status_code=500
            )

    registry = GeneratorRegistry()
    registry.register("outline", lambda provider: FailingGenerator())
    app.dependency_overrides[generation_router.get_generator_registry] = lambda: registry

    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=alice_api.headers,
        json={"content_type": "outline"},
    )

    assert response.status_code == 200
    failed = response.json()["data"]
    assert failed["generation_status"] == "failed"
    assert failed["error_code"] == "GENERATION_FAILED"
    assert failed["content_json"] is None
    assert failed["source_citations"] == []

    listed = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    detail = client.get(f"/api/v1/generated-contents/{failed['id']}", headers=alice_api.headers)
    assert listed.status_code == detail.status_code == 200
    assert listed.json()["data"][0]["id"] == failed["id"]
    assert detail.json()["data"]["content_json"] is None
    assert detail.json()["data"]["source_citations"] == []


def test_repeated_equivalent_generation_requests_create_distinct_records(
    client: TestClient,
    alice_api,
    api_course_factory,
    api_material_factory,
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    url = f"/api/v1/courses/{course_id}/generations"
    payload = {"content_type": "outline"}

    first = client.post(url, headers=alice_api.headers, json=payload)
    second = client.post(url, headers=alice_api.headers, json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] != second.json()["data"]["id"]
