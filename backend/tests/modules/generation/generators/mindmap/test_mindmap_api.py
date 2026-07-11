from __future__ import annotations

import re

import app.modules.generation.orchestrator.router as generation_router
from app.main import app
from app.modules.generation.generators.mindmap.schemas import MindmapMapResult


class PromptGroundedMindmapProvider:
    def answer_question(self, **_: object) -> object:
        raise AssertionError("Mindmap must not call answer_question")

    def generate_structured(self, *, prompt: str, output_schema: type[MindmapMapResult]) -> MindmapMapResult:
        chunk_ids = re.findall(r"\[chunk_id=([^\]]+)\]", prompt)
        chunk_id = chunk_ids[0]
        return output_schema.model_validate({"concepts": [
            {"local_key": "root", "label": "Course", "summary": "Root", "parent_local_key": None, "source_chunk_ids": [chunk_id]},
            {"local_key": "a", "label": "Topic A", "summary": "A", "parent_local_key": "root", "source_chunk_ids": [chunk_id]},
            {"local_key": "b", "label": "Topic B", "summary": "B", "parent_local_key": "root", "source_chunk_ids": [chunk_id]},
        ], "relations": []})


def test_mindmap_post_history_and_detail_persist_markdown(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id, content=b"Topic A\n\nTopic B")
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: PromptGroundedMindmapProvider()
    )
    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers,
        json={"content_type": "mindmap", "parameters": {"center_topic": "Course"}},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert data["content_json"]["markmap_markdown"] == "- Course\n  - Topic A\n  - Topic B"
    assert len(data["source_citations"]) == 1
    detail = client.get(f"/api/v1/generated-contents/{data['id']}", headers=alice_api.headers)
    assert detail.json()["data"]["content_json"] == data["content_json"]
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    assert any(item["id"] == data["id"] for item in history.json()["data"])
