import app.modules.generation.generators.mindmap.generator as mindmap_generator
import app.modules.generation.orchestrator.router as generation_router
from app.main import app


class MindmapProvider:
    def generate_structured(self, *, prompt, output_schema):
        return output_schema.model_validate({
            "topic_title": "第一章 基础概念",
            "root_node_id": "root",
            "nodes": [
                {"id": "root", "label": "Alpha", "summary": "Root", "level": 1},
                {"id": "child", "label": "Beta", "summary": "Child", "level": 2},
            ],
            "edges": [{"from": "root", "to": "child", "relation": "child"}],
        })


class FakePreprocessor:
    def transform(self, markdown):
        return {"root": {"content": "Alpha", "children": []}, "features": {}, "assets": {"styles": [], "scripts": []}}


def test_mindmap_api_persists_preprocessed_markmap_without_citations(client, alice_api, api_course_factory, api_material_factory, monkeypatch) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    monkeypatch.setattr(mindmap_generator, "MarkmapLibPreprocessor", lambda **_: FakePreprocessor())
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: MindmapProvider()
    response = client.post(f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json={"content_type": "mindmap", "parameters": {}})
    data = response.json()["data"]
    assert data["source_citations"] == []
    assert data["title"] == "第一章 基础概念"
    assert data["content_json"]["markmap_data"]["root"]["content"] == "Alpha"
    assert "source_citation_ids" not in data["content_json"]["nodes"][0]
