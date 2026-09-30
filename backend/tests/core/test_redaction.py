from app.core.config import Settings
from app.core.redaction import SensitiveDataRedactor


def test_redactor_masks_all_configured_credentials() -> None:
    redactor = SensitiveDataRedactor(
        Settings(
            _env_file=None,
            secret_key="configured-secret",
            course_qa_api_key="course-qa-key",
            study_plan_map_api_key="study-map-key",
            openai_api_key="legacy-key",
        )
    )

    output = redactor.redact(
        "configured-secret course-qa-key study-map-key legacy-key"
    )

    assert output == "[REDACTED] [REDACTED] [REDACTED] [REDACTED]"


def test_redactor_masks_bearer_tokens_case_insensitively() -> None:
    redactor = SensitiveDataRedactor(Settings(_env_file=None))

    output = redactor.redact("Authorization: bearer abc.def-123 another=ok")

    assert output == "Authorization: Bearer [REDACTED] another=ok"


def test_redactor_masks_labeled_unconfigured_secrets() -> None:
    redactor = SensitiveDataRedactor(Settings(_env_file=None))

    output = redactor.redact(
        "api_key=unknown-key SECRET_KEY:unknown-secret authorization=opaque"
    )

    assert output == (
        "api_key=[REDACTED] SECRET_KEY:[REDACTED] authorization=[REDACTED]"
    )


def test_redactor_preserves_non_sensitive_runtime_context() -> None:
    redactor = SensitiveDataRedactor(Settings(_env_file=None))

    output = redactor.redact(
        "model=gpt-5.4-mini base_url=https://models.example/v1 request_id=req_1"
    )

    assert output == (
        "model=gpt-5.4-mini base_url=https://models.example/v1 request_id=req_1"
    )
