from __future__ import annotations

import re

import app.modules.generation.orchestrator.router as generation_router
from app.main import app
from app.modules.generation.generators.quiz.schemas import QuizMapResult


class PromptGroundedQuizProvider:
    def answer_question(self, **_: object) -> object:
        raise AssertionError("Quiz must not call answer_question")

    def generate_structured(self, *, prompt: str, output_schema: type[QuizMapResult]) -> QuizMapResult:
        chunk_id = re.findall(r"\[chunk_id=([^\]]+)\]", prompt)[0]
        return output_schema.model_validate({"candidates": [
            {
                "question_type": "single_choice", "question_text": "Which topic is present?",
                "options": [{"id": "A", "text": "Alpha"}, {"id": "B", "text": "Beta"}, {"id": "C", "text": "Gamma"}, {"id": "D", "text": "Delta"}],
                "correct_answer": "A", "explanation": "The material contains Alpha.",
                "difficulty": "easy", "source_chunk_ids": [chunk_id],
            },
            {
                "question_type": "single_choice", "question_text": "Which topic appears first?",
                "options": [{"id": "A", "text": "Alpha"}, {"id": "B", "text": "Beta"}, {"id": "C", "text": "Gamma"}, {"id": "D", "text": "Delta"}],
                "correct_answer": "A", "explanation": "Alpha appears first.",
                "difficulty": "medium", "source_chunk_ids": [chunk_id],
            },
        ]})


def test_quiz_post_history_and_detail_persist_questions_and_citations(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id, content=b"Alpha\n\nBeta")
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: PromptGroundedQuizProvider()
    )
    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers,
        json={
            "content_type": "quiz",
            "parameters": {
                "question_count": 2,
                "question_types": ["single_choice"],
            },
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["generation_status"] == "success"
    assert [item["id"] for item in data["content_json"]["questions"]] == ["q_001", "q_002"]
    assert all(item["source_citation_ids"] for item in data["content_json"]["questions"])
    assert data["source_citations"]
    detail = client.get(f"/api/v1/generated-contents/{data['id']}", headers=alice_api.headers)
    assert detail.json()["data"]["content_json"] == data["content_json"]
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    assert any(item["id"] == data["id"] for item in history.json()["data"])


def test_invalid_quiz_parameters_return_422_without_history(
    client, alice_api, api_course_factory, api_material_factory
) -> None:
    course_id = api_course_factory(alice_api)
    api_material_factory(alice_api, course_id)
    response = client.post(
        f"/api/v1/courses/{course_id}/generations", headers=alice_api.headers,
        json={"content_type": "quiz", "parameters": {"question_count": 51}},
    )
    assert response.status_code == 422
    history = client.get(f"/api/v1/courses/{course_id}/generated-contents", headers=alice_api.headers)
    assert history.json()["data"] == []
