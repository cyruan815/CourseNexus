import app.modules.generation.orchestrator.router as generation_router
from app.main import app


class FlashcardProvider:
    def generate_structured(self, *, prompt, output_schema):
        return output_schema.model_validate({"topic_title": "第一章 基础概念", "cards": [{"front": "Alpha", "back": "First topic", "tags": ["intro"]}]})


def test_flashcard_api_persists_cards_without_citations(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: FlashcardProvider()
    response = client.post(f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json={"content_type": "flashcard", "parameters": {"card_count": 1}})
    data = response.json()["data"]
    assert data["source_citations"] == []
    assert data["title"] == "第一章 基础概念"
    assert data["content_json"]["cards"][0]["id"] == "card_001"
    assert "source_citation_ids" not in data["content_json"]["cards"][0]
