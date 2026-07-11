from __future__ import annotations

from importlib import import_module

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.orchestrator.contracts import Generator, GeneratorFactory


BUILTIN_GENERATOR_MODULES = {
    "flashcard": "app.modules.generation.generators.flashcard.generator",
    "knowledge_list": "app.modules.generation.generators.knowledge_list.generator",
    "mindmap": "app.modules.generation.generators.mindmap.generator",
    "outline": "app.modules.generation.generators.outline.generator",
    "quiz": "app.modules.generation.generators.quiz.generator",
}


class GeneratorRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, GeneratorFactory] = {}

    def register(self, content_type: str, factory: GeneratorFactory, *, replace: bool = False) -> None:
        if content_type in self._factories and not replace:
            raise CourseNexusError(
                code="CONFLICT",
                message="Generator is already registered",
                status_code=409,
                details={"content_type": content_type},
            )
        self._factories[content_type] = factory

    def create(self, content_type: str, model_provider: ModelProvider) -> Generator:
        factory = self._factories.get(content_type)
        if factory is None:
            raise CourseNexusError(
                code="VALIDATION_ERROR",
                message="Generation content type is not supported",
                status_code=422,
                details={"content_type": content_type},
            )
        return factory(model_provider)

    def supported_content_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def default_generator_registry() -> GeneratorRegistry:
    from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator

    registry = GeneratorRegistry()
    for content_type, module_name in BUILTIN_GENERATOR_MODULES.items():
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise

            def build_placeholder(
                model_provider: ModelProvider,
                *,
                _content_type: str = content_type,
            ) -> Generator:
                return PlaceholderGenerator(content_type=_content_type, model_provider=model_provider)

            factory = build_placeholder
        else:
            factory = module.build_generator
        registry.register(content_type, factory)
    return registry
