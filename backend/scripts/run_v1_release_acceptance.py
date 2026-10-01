from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import json
import mimetypes
import os
from pathlib import Path
import sys
from time import perf_counter
from typing import Literal
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SAMPLE_DIR = BACKEND / "tests" / "fixtures" / "release_samples"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp"
REQUIRED_MODEL_PURPOSES = ("embedding", "course_qa", "outline", "study_plan_generator")

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@dataclass(frozen=True)
class ValidationEvent:
    timestamp: str
    step: str
    status: Literal["passed", "failed"]
    elapsed_ms: float | None = None
    resource_ids: dict[str, str] | None = None
    error_code: str | None = None


class ValidationLog:
    def __init__(self, run_dir: Path) -> None:
        self.path = run_dir / "events.jsonl"
        self.events: list[ValidationEvent] = []

    def record(
        self,
        step: str,
        status: Literal["passed", "failed"],
        *,
        elapsed_ms: float | None = None,
        resource_ids: dict[str, str] | None = None,
        error_code: str | None = None,
    ) -> None:
        event = ValidationEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            step=step,
            status=status,
            elapsed_ms=elapsed_ms,
            resource_ids=resource_ids,
            error_code=error_code,
        )
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(_without_none(asdict(event)), sort_keys=True) + "\n")
        print(f"[{status}] {step}")


class AcceptanceFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _without_none(value: dict[str, object]) -> dict[str, object]:
    return {key: item for key, item in value.items() if item is not None}


def _configure_isolated_runtime(run_dir: Path) -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["ENABLE_MOCK_MODEL_PROVIDER"] = "false"
    os.environ["DATABASE_URL"] = f"sqlite:///{(run_dir / 'release.db').as_posix()}"
    os.environ["FILE_STORAGE_PATH"] = str(run_dir / "uploads")
    os.environ["CHROMA_PERSIST_PATH"] = str(run_dir / "chroma")
    os.environ["CHROMA_COLLECTION"] = f"v1_release_{uuid4().hex}"
    os.environ["LOG_DIR"] = str(run_dir / "app-logs")
    os.environ["LOG_LEVEL"] = "WARNING"


def _missing_model_purposes(settings: object) -> list[str]:
    return [
        purpose
        for purpose in REQUIRED_MODEL_PURPOSES
        if not (settings.model_endpoint(purpose).api_key or "").strip()
    ]


def _migrate_database() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(config, "head")


def _error_code(response: object) -> str:
    try:
        payload = response.json()
    except Exception:
        return "HTTP_ERROR"
    if not isinstance(payload, dict):
        return "HTTP_ERROR"
    error = payload.get("error")
    if not isinstance(error, dict):
        return "HTTP_ERROR"
    code = error.get("code")
    return code if isinstance(code, str) and code else "HTTP_ERROR"


def _request_json(
    client: object,
    log: ValidationLog,
    *,
    step: str,
    method: str,
    path: str,
    resource_ids: dict[str, str] | None = None,
    **kwargs: object,
) -> dict[str, object]:
    started = perf_counter()
    response = client.request(method, path, **kwargs)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    if response.status_code != 200:
        code = _error_code(response)
        log.record(
            step,
            "failed",
            elapsed_ms=elapsed_ms,
            resource_ids=resource_ids,
            error_code=code,
        )
        raise AcceptanceFailure(code)
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        log.record(step, "failed", elapsed_ms=elapsed_ms, error_code="INVALID_RESPONSE")
        raise AcceptanceFailure("INVALID_RESPONSE")
    log.record(step, "passed", elapsed_ms=elapsed_ms, resource_ids=resource_ids)
    return payload["data"]


def _upload_and_parse_samples(
    client: object,
    log: ValidationLog,
    *,
    course_id: str,
    headers: dict[str, str],
) -> tuple[list[str], list[str]]:
    material_ids: list[str] = []
    version_ids: list[str] = []
    for extension in ("txt", "pdf", "docx", "pptx"):
        sample = SAMPLE_DIR / f"limits-and-continuity.{extension}"
        mime_type = mimetypes.guess_type(sample.name)[0] or "application/octet-stream"
        with sample.open("rb") as source:
            uploaded = _request_json(
                client,
                log,
                step=f"upload_{extension}",
                method="POST",
                path=f"/api/v1/courses/{course_id}/materials",
                resource_ids={"course_id": course_id},
                headers=headers,
                files={"file": (sample.name, source, mime_type)},
            )
        material_id = str(uploaded["id"])
        parsed = _request_json(
            client,
            log,
            step=f"parse_{extension}",
            method="POST",
            path=f"/api/v1/materials/{material_id}/parse-retries",
            resource_ids={"course_id": course_id, "material_id": material_id},
            headers=headers,
        )
        if parsed.get("parse_status") != "parsed" or not parsed.get("is_learning_ready"):
            raise AcceptanceFailure("MATERIAL_NOT_LEARNING_READY")
        version_id = parsed.get("active_parse_version_id")
        if not isinstance(version_id, str) or not version_id:
            raise AcceptanceFailure("ACTIVE_PARSE_VERSION_MISSING")
        material_ids.append(material_id)
        version_ids.append(version_id)
    return material_ids, version_ids


def _save_payload(preview: dict[str, object]) -> dict[str, object]:
    payload = dict(preview)
    payload.pop("course_id", None)
    payload["client_flow"] = "wizard_v1"
    return payload


def _run_workflow(run_dir: Path, log: ValidationLog) -> dict[str, object]:
    from fastapi.testclient import TestClient

    from app.commands.reconcile_storage import reconcile_storage
    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.main import app

    settings = get_settings()
    run_suffix = uuid4().hex[:12]
    with TestClient(app, raise_server_exceptions=False) as client:
        username = f"release_{run_suffix}"
        password = f"release-{uuid4().hex}"
        _request_json(
            client,
            log,
            step="register",
            method="POST",
            path="/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        login = _request_json(
            client,
            log,
            step="login",
            method="POST",
            path="/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        token = login.get("access_token")
        if not isinstance(token, str) or not token:
            raise AcceptanceFailure("ACCESS_TOKEN_MISSING")
        headers = {"Authorization": f"Bearer {token}"}

        course = _request_json(
            client,
            log,
            step="create_course",
            method="POST",
            path="/api/v1/courses",
            headers=headers,
            json={"name": "V1 Release Check"},
        )
        course_id = str(course["id"])
        material_ids, version_ids = _upload_and_parse_samples(
            client,
            log,
            course_id=course_id,
            headers=headers,
        )
        scope = {"include_all_parsed_materials": False, "material_ids": material_ids}

        answer = _request_json(
            client,
            log,
            step="course_qa",
            method="POST",
            path=f"/api/v1/courses/{course_id}/qa/questions",
            resource_ids={"course_id": course_id},
            headers=headers,
            json={
                "question": "Explain the three conditions for continuity using the course materials.",
                "material_scope": scope,
                "source_page": "course_detail",
            },
        )
        citations = answer.get("source_citations")
        if answer.get("answer_type") != "grounded" or not isinstance(citations, list) or not citations:
            raise AcceptanceFailure("GROUNDED_CITATION_MISSING")

        generated = _request_json(
            client,
            log,
            step="generate_outline",
            method="POST",
            path=f"/api/v1/courses/{course_id}/generations",
            resource_ids={"course_id": course_id},
            headers=headers,
            json={
                "content_type": "outline",
                "material_scope": scope,
                "parameters": {"section_count": 3},
            },
        )
        if generated.get("generation_status") != "success":
            raise AcceptanceFailure("GENERATION_NOT_SUCCESSFUL")

        start_date = date.today() + timedelta(days=1)
        end_date = start_date + timedelta(days=2)
        preview = _request_json(
            client,
            log,
            step="preview_study_plan",
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plans/preview",
            resource_ids={"course_id": course_id},
            headers=headers,
            json={
                "goal_text": "Review limits and continuity with a final assessment",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily_available_minutes": 90,
                "preference": "balanced",
                "material_scope": scope,
            },
        )
        saved = _request_json(
            client,
            log,
            step="save_study_plan",
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plans",
            resource_ids={"course_id": course_id},
            headers={**headers, "Idempotency-Key": f"v1-release-{run_suffix}"},
            json=_save_payload(preview),
        )
        plan = saved.get("plan")
        if not isinstance(plan, dict) or not plan.get("id"):
            raise AcceptanceFailure("STUDY_PLAN_MISSING")

        rag_index = app.state.rag_index_manager.require_index(
            missing_code="RAG_NOT_CONFIGURED",
            missing_message="RAG is not configured",
        )
        with SessionLocal() as db:
            report = reconcile_storage(
                db=db,
                storage_root=settings.file_storage_path,
                rag_records=rag_index.list_records(),
            )
        if report.inconsistency_count:
            raise AcceptanceFailure("STORAGE_INCONSISTENT")
        log.record("reconcile_storage", "passed")

    return {
        "course_id": course_id,
        "material_ids": material_ids,
        "material_version_ids": version_ids,
        "conversation_id": answer.get("conversation_id"),
        "generated_content_id": generated.get("id"),
        "study_plan_id": plan.get("id"),
        "reconciliation_status": report.status,
        "reconciliation_inconsistency_count": report.inconsistency_count,
    }


def _write_result(
    run_dir: Path,
    log: ValidationLog,
    *,
    status: Literal["passed", "failed"],
    started_at: datetime,
    resources: dict[str, object] | None = None,
    error_code: str | None = None,
) -> None:
    result = _without_none(
        {
            "schema_version": 1,
            "status": status,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(log.events),
            "resources": resources,
            "error_code": error_code,
        }
    )
    (run_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> int:
    started_at = datetime.now(timezone.utc)
    run_dir = output_root / (
        f"v1-release-validation-{started_at.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)
    log = ValidationLog(run_dir)
    _configure_isolated_runtime(run_dir)

    try:
        from app.core.config import get_settings

        settings = get_settings()
        missing = _missing_model_purposes(settings)
        if settings.enable_mock_model_provider:
            raise AcceptanceFailure("MOCK_MODEL_PROVIDER_FORBIDDEN")
        if missing:
            raise AcceptanceFailure("MODEL_PROVIDER_NOT_CONFIGURED")

        migration_started = perf_counter()
        _migrate_database()
        log.record(
            "migrate_database",
            "passed",
            elapsed_ms=round((perf_counter() - migration_started) * 1000, 2),
        )
        resources = _run_workflow(run_dir, log)
        _write_result(
            run_dir,
            log,
            status="passed",
            started_at=started_at,
            resources=resources,
        )
        print(run_dir)
        return 0
    except AcceptanceFailure as exc:
        log.record("release_acceptance", "failed", error_code=exc.code)
        _write_result(
            run_dir,
            log,
            status="failed",
            started_at=started_at,
            error_code=exc.code,
        )
        print(run_dir)
        return 2
    except Exception:
        log.record("release_acceptance", "failed", error_code="UNEXPECTED_ERROR")
        _write_result(
            run_dir,
            log,
            status="failed",
            started_at=started_at,
            error_code="UNEXPECTED_ERROR",
        )
        print(run_dir)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated V1 acceptance flow with real model providers only."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory that receives v1-release-validation-* run directories.",
    )
    args = parser.parse_args()
    return run(output_root=args.output_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
