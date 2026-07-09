from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelAnswer
from app.modules.material_context.schemas import ContextChunk


class OpenAIModelProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise CourseNexusError(
                code="GENERATION_FAILED",
                message="OpenAI API key 未配置",
                status_code=500,
                details={"missing": "OPENAI_API_KEY"},
            )
        self.model = model
        self.client = client or OpenAI(api_key=api_key, base_url=base_url)

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        prompt = self._build_prompt(question, context_chunks)
        try:
            response = self.client.responses.create(model=self.model, input=prompt)
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc

        answer_text = getattr(response, "output_text", None) or ""
        return ModelAnswer(
            answer_text=answer_text,
            citation_chunk_ids=[chunk.chunk_id for chunk in context_chunks[:1]],
        )

    def _build_prompt(self, question: str, context_chunks: list[ContextChunk]) -> str:
        context_text = "\n\n".join(
            f"[{index + 1}] {chunk.material_name}: {chunk.content_text}"
            for index, chunk in enumerate(context_chunks)
        )
        return (
            "You are CourseNexus, a course-material grounded study assistant. "
            "Answer using only the provided context.\n\n"
            f"Context:\n{context_text}\n\nQuestion:\n{question}"
        )
