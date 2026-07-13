from __future__ import annotations

import app.modules.generation.orchestrator.router as generation_router
from app.core.errors import CourseNexusError
from app.main import app


class OutlineProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        return output_schema.model_validate({"sections": [{
            "title": "Complete materials", "summary": "Summary", "review_suggestion": "Review",
        }]})


class FailingProvider:
    def generate_structured(self, *, prompt, output_schema):
        raise CourseNexusError(code="GENERATION_FAILED", message="provider failed", status_code=502)


def test_generation_requires_authentication(client) -> None:
    response = client.post("/api/v1/courses/crs_missing/generations", json={"content_type": "outline"})
    assert response.status_code == 401


def test_generation_history_and_detail_return_same_json_and_empty_citations(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id, filename="one.md", content=b"Alpha")
    api_material_factory(alice_api, course_id, filename="two.md", content=b"Beta")
    provider = OutlineProvider()
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: provider

    created = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=alice_api.headers,
        json={"content_type": "outline", "parameters": {"section_count": 1}},
    ).json()["data"]

    assert len(provider.prompts) == 1
    assert "Alpha" in provider.prompts[0] and "Beta" in provider.prompts[0]
    assert created["source_citations"] == []
    listed = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers).json()["data"][0]
    detail = client.get(f"/api/v1/generated-contents/{created['id']}", headers=alice_api.headers).json()["data"]
    assert listed["content_json"] == created["content_json"] == detail["content_json"]
    assert listed["source_citations"] == detail["source_citations"] == []


def test_invalid_parameters_return_422_without_history(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: OutlineProvider()
    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=alice_api.headers,
        json={"content_type": "outline", "parameters": {"section_count": 0}},
    )
    assert response.status_code == 422
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers).json()["data"]
    assert history == []


def test_model_failure_persists_failed_history(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: FailingProvider()
    response = client.post(
        f"/api/v1/courses/{course_id}/generations",
        headers=alice_api.headers,
        json={"content_type": "outline", "parameters": {}},
    )
    data = response.json()["data"]
    assert data["generation_status"] == "failed"
    assert data["error_code"] == "GENERATION_FAILED"
    assert data["source_citations"] == []
