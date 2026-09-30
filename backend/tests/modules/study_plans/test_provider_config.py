from app.core.config import Settings
from app.modules.study_plans import router


def test_study_plan_dependencies_route_purposes_to_shared_factory(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    expected_provider = object()

    def fake_factory(purpose, *, api_style="auto", settings):
        calls.append((purpose, api_style))
        return expected_provider

    monkeypatch.setattr(router, "create_model_provider", fake_factory)
    monkeypatch.setattr(
        router,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            study_plan_generator_api_style="responses",
        ),
    )

    assert router.get_plan_parser_provider() is expected_provider
    assert router.get_plan_generator_provider() is expected_provider
    assert router.get_plan_diagnostic_provider() is expected_provider
    assert calls == [
        ("study_plan_parser", "auto"),
        ("study_plan_generator", "responses"),
        ("study_plan_diagnostic", "auto"),
    ]


def test_generator_and_map_api_styles_are_constructed_independently(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        study_plan_generator_api_key="generator-key",
        study_plan_generator_base_url="https://api.openai.com/v1",
        study_plan_generator_model="generator-model",
        study_plan_generator_api_style="responses",
        study_plan_map_api_style="chat",
    )
    monkeypatch.setattr(router, "get_settings", lambda: settings)

    generator = router.get_plan_generator_provider()
    map_provider = router.get_plan_map_provider(model_provider=generator)

    assert generator.api_style == "responses"
    assert map_provider.api_style == "chat"
    assert map_provider.model == "generator-model"


def test_map_provider_reuses_generator_when_no_map_override(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        study_plan_generator_api_key="generator-key",
        study_plan_generator_api_style="responses",
    )
    monkeypatch.setattr(router, "get_settings", lambda: settings)
    generator = router.get_plan_generator_provider()

    assert router.get_plan_map_provider(model_provider=generator) is generator
