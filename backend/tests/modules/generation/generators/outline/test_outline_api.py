import app.modules.generation.orchestrator.router as generation_router
from app.main import app


class OutlineProvider:
    def generate_structured(self, *, prompt, output_schema):
        return output_schema.model_validate({"sections": [{"title": "Alpha", "summary": "Summary", "review_suggestion": "Review"}]})


def test_outline_api_persists_sections_without_citations(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: OutlineProvider()
    response = client.post(f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json={"content_type": "outline", "parameters": {"section_count": 1}})
    data = response.json()["data"]
    assert data["source_citations"] == []
    assert data["content_json"]["sections"][0]["id"] == "sec_001"
    assert "source_citation_ids" not in data["content_json"]["sections"][0]
