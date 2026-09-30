from __future__ import annotations

from app.core.config import ModelEndpointConfig, ModelPurpose, Settings, get_settings
from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.model_provider.openai import ApiStyle, OpenAIModelProvider


def create_model_provider(
    purpose: ModelPurpose,
    *,
    api_style: ApiStyle = "auto",
    settings: Settings | None = None,
) -> ModelProvider:
    runtime_settings = settings or get_settings()
    endpoint = runtime_settings.model_endpoint(purpose)
    return create_model_provider_from_endpoint(
        purpose,
        endpoint=endpoint,
        api_style=api_style,
        settings=runtime_settings,
    )


def create_model_provider_from_endpoint(
    purpose: str,
    *,
    endpoint: ModelEndpointConfig,
    api_style: ApiStyle = "auto",
    settings: Settings | None = None,
) -> ModelProvider:
    runtime_settings = settings or get_settings()
    if endpoint.api_key:
        return OpenAIModelProvider(
            api_key=endpoint.api_key,
            model=endpoint.model,
            base_url=endpoint.base_url,
            api_key_env_name=f"{purpose.upper()}_API_KEY",
            api_style=api_style,
        )
    if runtime_settings.enable_mock_model_provider:
        return MockModelProvider()
    raise CourseNexusError(
        code="MODEL_PROVIDER_NOT_CONFIGURED",
        message="模型服务未配置",
        status_code=503,
        details={"purpose": purpose},
    )
