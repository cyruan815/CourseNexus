import app.modules.generation.orchestrator.router as generation_router
from app.main import app


class QuizProvider:
    def generate_structured(self, *, prompt, output_schema):
        return output_schema.model_validate({"questions": [{
            "question_type": "single_choice", "question_text": "Which topic is present?",
            "options": [{"id": key, "text": text} for key, text in zip("ABCD", ["Alpha", "Beta", "Gamma", "Delta"])],
            "correct_answer": "A", "explanation": "Alpha is present.", "difficulty": "easy",
        }]})


def test_quiz_api_persists_final_questions_without_citations(client, alice_api, api_course_factory, api_material_factory) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = lambda: lambda _: QuizProvider()
    response = client.post(f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers, json={"content_type": "quiz", "parameters": {"question_count": 1}})
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert data["source_citations"] == []
    assert data["content_json"]["questions"][0]["id"] == "q_001"
    assert "source_citation_ids" not in data["content_json"]["questions"][0]
