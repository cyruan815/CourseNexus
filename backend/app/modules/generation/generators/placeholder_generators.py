from __future__ import annotations

from typing import Any

from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


class PlaceholderGenerator:
    def __init__(self, *, content_type: str, model_provider: ModelProvider) -> None:
        self.content_type = content_type
        self.model_provider = model_provider

    def generate(
        self,
        *,
        context: MaterialGenerationContext,
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        return GeneratorOutput(
            title=self.content_type.replace("_", " ").title(),
            content=context.text,
            content_json={"items": []},
        )
