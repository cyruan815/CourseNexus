import app.modules.generation.orchestrator.router as generation_router
from app.main import app


class QuizProvider:
    def generate_structured(self, *, prompt, output_schema):
        return output_schema.model_validate({"topic_title": "第一章 基础概念", "questions": [{
            "question_type": "single_choice", "question_text": "材料中出现了哪个主题？",
            "options": [{"id": key, "text": text, "explanation": f"{text}的判断理由。"} for key, text in zip("ABCD", ["甲", "乙", "丙", "丁"])],
            "correct_answer": "A", "explanation": "材料中包含甲主题。", "difficulty": "easy",
        }]})


def test_quiz_api_persists_final_questions_without_citations(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: QuizProvider()
    response = client.post(f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json={"content_type": "quiz", "parameters": {"question_count": 1}})
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert data["title"] == "第一章 基础概念"
    assert data["source_citations"] == []
    assert data["content_json"]["questions"][0]["id"] == "q_001"
    assert data["content_json"]["questions"][0]["options"][1]["explanation"] == "乙的判断理由。"
    assert "source_citation_ids" not in data["content_json"]["questions"][0]
