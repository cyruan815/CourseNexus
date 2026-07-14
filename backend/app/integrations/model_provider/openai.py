from __future__ import annotations

import json
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
        self.base_url = base_url
        self.client = client or OpenAI(api_key=api_key, base_url=base_url)

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        started_at = perf_counter()
        prompt = self._build_prompt(question, context_chunks)
        try:
            response = self.client.responses.create(model=self.model, input=prompt)
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc
            answer_text = self._answer_question_with_chat(prompt=prompt)
        else:
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


    def generate_text(self, *, prompt: str) -> str:
        started_at = perf_counter()
        if self._uses_deepseek_chat_completions():
            text = self._generate_text_with_chat(prompt=prompt)
        else:
            try:
                response = self.client.responses.create(model=self.model, input=prompt)
            except Exception as exc:
                if not _is_not_found_error(exc):
                    raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc
                text = self._generate_text_with_chat(prompt=prompt)
            else:
                text = getattr(response, "output_text", None) or ""
        logger.info(
            "模型调用成功 | operation=generate_text model=%s cost_ms=%.2f",
            self.model,
            (perf_counter() - started_at) * 1000,
        )
        return text

    def _generate_text_with_chat(self, *, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You generate polished Markdown only."},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc
        return _first_chat_content(response)

    def generate_structured(
        self,
        *,
        prompt: str,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        started_at = perf_counter()
        if self._uses_deepseek_chat_completions():
            result = self._generate_structured_with_chat(prompt=prompt, output_schema=output_schema)
            self._log_structured_generation(output_schema=output_schema, started_at=started_at)
            return result

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
                status_code=500,
            ) from exc
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc
            result = self._generate_structured_with_chat(prompt=prompt, output_schema=output_schema)
        else:
            parsed = getattr(response, "output_parsed", None)
            result = self._validate_structured_output(parsed=parsed, output_schema=output_schema)

        self._log_structured_generation(output_schema=output_schema, started_at=started_at)
        return result

    def _uses_deepseek_chat_completions(self) -> bool:
        return bool(self.base_url and "api.deepseek.com" in self.base_url.casefold())

    def _log_structured_generation(
        self,
        *,
        output_schema: type[StructuredOutputT],
        started_at: float,
    ) -> None:
        logger.info(
            "模型调用成功 | operation=generate_structured model=%s schema=%s cost_ms=%.2f",
            self.model,
            output_schema.__name__,
            (perf_counter() - started_at) * 1000,
        )

    def _answer_question_with_chat(self, *, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You answer using only the provided course context."},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc
        return _first_chat_content(response)


    def _generate_structured_with_chat(
        self,
        *,
        prompt: str,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        schema_json = json.dumps(output_schema.model_json_schema(), ensure_ascii=False)
        fallback_prompt = "\n\n".join(
            [
                prompt,
                "请只输出一个合法 JSON 对象，不要输出 Markdown、解释文字或代码块。",
                f"JSON Schema:\n{schema_json}",
            ]
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You generate valid JSON only."},
                    {"role": "user", "content": fallback_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="模型调用失败", status_code=502) from exc

        try:
            parsed = json.loads(_first_chat_content(response))
        except (TypeError, ValueError) as exc:
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="模型结构化输出不符合约定",
                status_code=500,
            ) from exc
        return self._validate_structured_output(parsed=parsed, output_schema=output_schema)

    def _validate_structured_output(
        self,
        *,
        parsed: object,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        try:
            if isinstance(parsed, BaseModel):
                return output_schema.model_validate(parsed.model_dump())
            return output_schema.model_validate(parsed)
        except (TypeError, ValueError, ValidationError) as exc:
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="模型结构化输出不符合约定",
                status_code=500,
            ) from exc

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


def _is_not_found_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    response_status_code = getattr(response, "status_code", None)
    return status_code == 404 or response_status_code == 404


def _first_chat_content(response: object) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""
