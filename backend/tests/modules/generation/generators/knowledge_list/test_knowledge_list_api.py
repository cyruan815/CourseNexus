from __future__ import annotations

import re

import app.modules.generation.orchestrator.router as generation_router
from app.main import app
from app.modules.generation.generators.knowledge_list.schemas import KnowledgeMapResult


class Provider:
    def answer_question(self, **_: object) -> object:
        raise AssertionError

    def generate_structured(self, *, prompt: str, output_schema: type[KnowledgeMapResult]) -> KnowledgeMapResult:
        chunk = re.findall(r"\[chunk_id=([^\]]+)\]", prompt)[0]
        return output_schema.model_validate(
            {
                "candidates": [
                    {
                        "name": "Alpha",
                        "definition": "The first topic.",
                        "importance": "high",
                        "related_section": "Core",
                        "source_chunk_ids": [chunk],
                    }
                ]
            }
        )


def test_knowledge_list_post_history_detail(client, alice_api, api_course_factory, api_material_factory) -> None:
    course = api_course_factory(alice_api)
    api_material_factory(alice_api, course)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: Provider()
    )
    response = client.post(
        f"/api/v1/courses/{course}/generations",
        headers=alice_api.headers,
        json={"content_type": "knowledge_list", "parameters": {"item_count": 1}},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert data["content_json"]["items"][0]["source_citation_ids"]
    detail = client.get(f"/api/v1/generated-contents/{data['id']}", headers=alice_api.headers)
    assert detail.json()["data"]["content_json"] == data["content_json"]


def test_invalid_knowledge_parameters_do_not_persist(client, alice_api, api_course_factory, api_material_factory) -> None:
    course = api_course_factory(alice_api)
    api_material_factory(alice_api, course)
    response = client.post(
        f"/api/v1/courses/{course}/generations",
        headers=alice_api.headers,
        json={"content_type": "knowledge_list", "parameters": {"item_count": 201}},
    )
    assert response.status_code == 422
    history = client.get(f"/api/v1/courses/{course}/generated-contents", headers=alice_api.headers)
    assert history.json()["data"] == []
