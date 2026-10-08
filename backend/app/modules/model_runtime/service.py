from __future__ import annotations

import json
import os
from pathlib import Path
import re
from threading import Lock
from uuid import uuid4

from app.core.config import MODEL_PURPOSES, Settings, get_settings
from app.core.errors import CourseNexusError
from app.core.logging import refresh_logging_redactor
from app.core.paths import PROJECT_ROOT
from app.integrations.rag.manager import get_rag_index_manager
from app.modules.model_runtime.schemas import (
    ModelEndpointConfigRead,
    ModelRuntimeConfigRead,
    ModelRuntimeConfigUpdate,
)


ENV_FILE_PATH = PROJECT_ROOT / ".env"
GENERAL_MODEL_PURPOSES = tuple(
    purpose for purpose in MODEL_PURPOSES if purpose != "embedding"
) + ("study_plan_map",)
_ENV_ASSIGNMENT_PATTERN = re.compile(
    r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*="
)
_ENV_WRITE_LOCK = Lock()
_API_KEY_HINT_LENGTH = 4


def get_model_runtime_config() -> ModelRuntimeConfigRead:
    settings = get_settings()
    return build_model_runtime_config(settings)


def save_model_runtime_config(
    payload: ModelRuntimeConfigUpdate,
) -> ModelRuntimeConfigRead:
    current_settings = get_settings()

    embedding_key = _updated_secret(
        payload.embedding.api_key,
        current_settings.embedding_api_key,
    )
    general_key = _updated_secret(
        payload.general.api_key,
        current_settings.course_qa_api_key,
    )
    missing_groups = [
        group
        for group, value in (
            ("embedding", embedding_key),
            ("general", general_key),
        )
        if not value
    ]
    if missing_groups:
        raise CourseNexusError(
            code="MODEL_API_KEY_REQUIRED",
            message="首次配置时必须填写 API Key",
            status_code=422,
            details={"groups": missing_groups},
        )

    updates = _build_environment_updates(
        payload,
        embedding_key=embedding_key,
        general_key=general_key,
    )
    try:
        update_environment_file(ENV_FILE_PATH, updates)
    except OSError as exc:
        raise CourseNexusError(
            code="MODEL_CONFIG_WRITE_FAILED",
            message="模型配置写入失败",
            status_code=500,
        ) from exc

    rag_index_manager = get_rag_index_manager()
    rag_index_manager.close()
    get_settings.cache_clear()
    refreshed_settings = get_settings()
    refresh_logging_redactor(refreshed_settings)
    return build_model_runtime_config(refreshed_settings)


def build_model_runtime_config(settings: Settings) -> ModelRuntimeConfigRead:
    embedding = _read_endpoint(settings, "embedding")
    general = _read_endpoint(settings, "course_qa")
    general_signatures = {
        _endpoint_signature(settings, purpose)
        for purpose in GENERAL_MODEL_PURPOSES
    }
    return ModelRuntimeConfigRead(
        embedding=embedding,
        general=general,
        general_config_consistent=len(general_signatures) == 1,
    )


def update_environment_file(env_path: Path, updates: dict[str, str]) -> None:
    """Replace selected dotenv values atomically while preserving unrelated lines."""
    with _ENV_WRITE_LOCK:
        existing = env_path.read_text(encoding="utf-8-sig") if env_path.exists() else ""
        updated = _replace_environment_values(existing, updates)
        temp_dir = env_path.parent / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f".env.{uuid4().hex}.tmp"
        try:
            descriptor = os.open(
                temp_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
                file.write(updated)
                file.flush()
                os.fsync(file.fileno())
            if env_path.exists():
                os.chmod(temp_path, env_path.stat().st_mode)
            os.replace(temp_path, env_path)
        finally:
            temp_path.unlink(missing_ok=True)


def _updated_secret(candidate, existing: str | None) -> str:
    if candidate is None:
        return (existing or "").strip()
    return candidate.get_secret_value().strip()


def _build_environment_updates(
    payload: ModelRuntimeConfigUpdate,
    *,
    embedding_key: str,
    general_key: str,
) -> dict[str, str]:
    updates = {
        "EMBEDDING_API_KEY": embedding_key,
        "EMBEDDING_BASE_URL": payload.embedding.base_url,
        "EMBEDDING_MODEL": payload.embedding.model,
    }
    for purpose in GENERAL_MODEL_PURPOSES:
        prefix = purpose.upper()
        updates[f"{prefix}_API_KEY"] = general_key
        updates[f"{prefix}_BASE_URL"] = payload.general.base_url
        updates[f"{prefix}_MODEL"] = payload.general.model
    return updates


def _read_endpoint(settings: Settings, purpose: str) -> ModelEndpointConfigRead:
    api_key, base_url, model = _endpoint_signature(settings, purpose)
    return ModelEndpointConfigRead(
        model=model,
        base_url=base_url or None,
        api_key_configured=bool(api_key),
        api_key_hint=_api_key_hint(api_key),
    )


def _endpoint_signature(
    settings: Settings,
    purpose: str,
) -> tuple[str, str, str]:
    api_key = (getattr(settings, f"{purpose}_api_key") or "").strip()
    base_url = (getattr(settings, f"{purpose}_base_url") or "").strip()
    model = (getattr(settings, f"{purpose}_model") or "").strip()
    return api_key, base_url, model


def _api_key_hint(api_key: str) -> str | None:
    if not api_key:
        return None
    visible_length = min(_API_KEY_HINT_LENGTH, max(0, len(api_key) - 1))
    return f"{api_key[:visible_length]}••••"


def _replace_environment_values(content: str, updates: dict[str, str]) -> str:
    newline = "\r\n" if "\r\n" in content else "\n"
    pending = dict(updates)
    output: list[str] = []

    for line in content.splitlines(keepends=True):
        line_without_ending = line.rstrip("\r\n")
        line_ending = line[len(line_without_ending) :]
        match = _ENV_ASSIGNMENT_PATTERN.match(line_without_ending)
        key = match.group("key") if match else None
        if key in updates:
            output.append(f"{key}={_encode_environment_value(updates[key])}{line_ending or newline}")
            pending.pop(key, None)
        else:
            output.append(line)

    if pending:
        if output and not output[-1].endswith(("\n", "\r")):
            output[-1] += newline
        if output and output[-1].strip():
            output.append(newline)
        output.append("# Managed by CourseNexus model configuration" + newline)
        for key, value in pending.items():
            output.append(f"{key}={_encode_environment_value(value)}{newline}")
    return "".join(output)


def _encode_environment_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
