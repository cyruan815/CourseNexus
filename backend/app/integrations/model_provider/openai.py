from __future__ import annotations

from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelAnswer, StructuredOutputT
from app.modules.material_context.schemas import ContextChunk


logger = get_logger("model.generate")


class OpenAIModelProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        client: Any | None = None,
        api_key_env_name: str = "MODEL_API_KEY",
    ) -> None:
        if not api_key:
            raise CourseNexusError(
                code="GENERATION_FAILED",
                message=f"{api_key_env_name} 未配置",
                status_code=500,
                details={"missing": api_key_env_name},
            )
        self.model = model
        self.client = client or OpenAI(api_key=api_key, base_url=base_url)

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        started_at = perf_counter()
        prompt = self._build_prompt(question, context_chunks)
        try:
            response = self.client.responses.create(model=self.model, input=prompt)
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc

        answer_text = getattr(response, "output_text", None) or ""
        answer = ModelAnswer(
            answer_text=answer_text,
            citation_chunk_ids=[chunk.chunk_id for chunk in context_chunks[:1]],
        )
        logger.info(
            "模型调用成功 | operation=answer_question model=%s chunks=%d cost_ms=%.2f",
            self.model,
            len(context_chunks),
            (perf_counter() - started_at) * 1000,
        )
        return answer

    def generate_structured(
        self,
        *,
        prompt: str,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        started_at = perf_counter()
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=prompt,
                text_format=output_schema,
            )
        except ValidationError as exc:
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="模型结构化输出不符合约定",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc

        parsed = getattr(response, "output_parsed", None)
        try:
            if isinstance(parsed, BaseModel):
                result = output_schema.model_validate(parsed.model_dump())
            else:
                result = output_schema.model_validate(parsed)
        except (TypeError, ValueError, ValidationError) as exc:
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="模型结构化输出不符合约定",
                status_code=502,
            ) from exc
        logger.info(
            "模型调用成功 | operation=generate_structured model=%s schema=%s cost_ms=%.2f",
            self.model,
            output_schema.__name__,
            (perf_counter() - started_at) * 1000,
        )
        return result

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
