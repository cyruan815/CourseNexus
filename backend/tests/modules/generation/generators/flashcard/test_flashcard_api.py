from __future__ import annotations

import re

import app.modules.generation.orchestrator.router as generation_router
from app.main import app
from app.modules.generation.generators.flashcard.schemas import FlashcardMapResult


class PromptGroundedFlashcardProvider:
    def answer_question(self, **_: object) -> object:
        raise AssertionError("Flashcard must not call answer_question")

    def generate_structured(self, *, prompt: str, output_schema: type[FlashcardMapResult]) -> FlashcardMapResult:
        chunk_id = re.findall(r"\[chunk_id=([^\]]+)\]", prompt)[0]
        return output_schema.model_validate({"candidates": [
            {"front": "What is Alpha?", "back": "Alpha is the first topic.", "tags": ["core"], "source_chunk_ids": [chunk_id]},
            {"front": "What is Beta?", "back": "Beta is the second topic.", "tags": ["core"], "source_chunk_ids": [chunk_id]},
        ]})


def test_flashcard_post_history_and_detail_persist_cards_and_citations(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id, content=b"Alpha\n\nBeta")
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: PromptGroundedFlashcardProvider()
    )
    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers,
        json={"content_type": "flashcard", "parameters": {"card_count": 2}},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert [item["id"] for item in data["content_json"]["cards"]] == ["card_001", "card_002"]
    assert all(item["mastery_status"] == "unknown" for item in data["content_json"]["cards"])
    assert all(item["source_citation_ids"] for item in data["content_json"]["cards"])
    detail = client.get(f"/api/v1/generated-contents/{data['id']}", headers=alice_api.headers)
    assert detail.json()["data"]["content_json"] == data["content_json"]
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    assert any(item["id"] == data["id"] for item in history.json()["data"])


def test_invalid_flashcard_parameters_return_422_without_history(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers,
        json={"content_type": "flashcard", "parameters": {"card_count": 0}},
    )
    assert response.status_code == 422
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    assert history.json()["data"] == []
