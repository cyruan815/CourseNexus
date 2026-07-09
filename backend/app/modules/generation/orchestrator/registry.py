from __future__ import annotations

from app.core.errors import CourseNexusError
from app.modules.generation.orchestrator.contracts import Generator


class GeneratorRegistry:
    def __init__(self) -> None:
        self._generators: dict[str, Generator] = {}

    def register(self, content_type: str, generator: Generator) -> None:
        self._generators[content_type] = generator

    def get(self, content_type: str) -> Generator:
        generator = self._generators.get(content_type)
        if generator is None:
            raise CourseNexusError(
                code="VALIDATION_ERROR",
                message="生成类型不支持",
                status_code=422,
                details={"content_type": content_type},
            )
        return generator


def default_generator_registry() -> GeneratorRegistry:
    from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator

    registry = GeneratorRegistry()
    for content_type in ("flashcard", "mindmap", "quiz", "outline", "knowledge_list"):
        registry.register(content_type, PlaceholderGenerator(content_type=content_type))
    return registry
