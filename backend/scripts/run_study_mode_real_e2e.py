from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


GOAL_TEXT = "我要两天内深度学习计算机网络物理层的知识点，今天是2026年7月13日"
SOURCE_PDF_LABEL = "<local validation PDF>"


class RunLogger:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.log_path = run_dir / "run.log.jsonl"
        self.events: list[dict[str, object]] = []

    def event(self, step: str, status: str, **fields: object) -> None:
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "status": status,
            **fields,
        }
        self.events.append(payload)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        print(f"[{status}] {step}")


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _summarize(value: object, *, max_chars: int = 1400) -> object:
    if isinstance(value, dict):
        return {
            key: _summarize(item, max_chars=max_chars)
            for key, item in value.items()
            if key.lower() not in {"access_token", "authorization", "password"}
        }
    if isinstance(value, list):
        return [_summarize(item, max_chars=max_chars) for item in value[:20]]
    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + "...[truncated]"
    return value


def _write_json(path: Path, data: object) -> None:
    path.write_text(_json(data), encoding="utf-8")


def _configure_isolated_runtime(run_dir: Path) -> None:
    db_path = run_dir / "course_nexus_real_e2e.db"
    upload_dir = run_dir / "uploads"
    chroma_dir = run_dir / "chroma"
    app_log_dir = run_dir / "app-logs"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["FILE_STORAGE_PATH"] = str(upload_dir)
    os.environ["CHROMA_PERSIST_PATH"] = str(chroma_dir)
    os.environ["CHROMA_COLLECTION"] = f"course_nexus_e2e_{datetime.now().strftime('%H%M%S')}_{uuid4().hex[:8]}"
    os.environ["LOG_DIR"] = str(app_log_dir)
    os.environ["LOG_LEVEL"] = "INFO"


def _setup_app() -> object:
    import app.db.models  # noqa: F401
    from app.db.base import Base
    from app.db.session import engine
    from app.main import app

    Base.metadata.create_all(engine)
    return app


def _response_payload(response: object) -> dict[str, object]:
    try:
        return response.json()
    except Exception:
        return {"raw_text": getattr(response, "text", "")}


def _api_json(
    client: object,
    logger: RunLogger,
    *,
    method: str,
    path: str,
    step: str,
    expected_status: int = 200,
    **kwargs: object,
) -> dict[str, object]:
    started = perf_counter()
    response = client.request(method, path, **kwargs)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    payload = _response_payload(response)
    status_code = getattr(response, "status_code", None)
    logger.event(
        step,
        "ok" if status_code == expected_status else "failed",
        method=method,
        path=path,
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        response=_summarize(payload),
    )
    if status_code != expected_status:
        raise RuntimeError(f"{step} failed: HTTP {status_code} {path}\n{_json(payload)}")
    return payload


def _api_file(
    client: object,
    logger: RunLogger,
    *,
    path: str,
    step: str,
    output_path: Path,
    headers: dict[str, str],
    expected_status: int = 200,
) -> None:
    started = perf_counter()
    response = client.get(path, headers=headers)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    status_code = response.status_code
    logger.event(
        step,
        "ok" if status_code == expected_status else "failed",
        method="GET",
        path=path,
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        content_type=response.headers.get("content-type"),
        bytes=len(response.content),
    )
    if status_code != expected_status:
        raise RuntimeError(f"{step} failed: HTTP {status_code} {path}\n{response.text}")
    output_path.write_bytes(response.content)


def _count_chunks(material_id: str) -> int:
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.modules.materials.models import MaterialChunk

    with SessionLocal() as db:
        return len(db.execute(select(MaterialChunk).where(MaterialChunk.material_id == material_id)).scalars().all())


def _find_subtask(saved: dict[str, object], allowed_types: set[str]) -> dict[str, object] | None:
    subtasks = saved["data"]["subtasks"]
    assert isinstance(subtasks, list)
    for subtask in subtasks:
        if isinstance(subtask, dict) and subtask.get("subtask_type") in allowed_types:
            return subtask
    return None


def _diagnostic_answers(questions_payload: dict[str, object]) -> dict[str, object]:
    data = questions_payload["data"]
    assert isinstance(data, dict)
    questions = data["questions"]
    assert isinstance(questions, list)
    topic_mastery: list[dict[str, str]] = []
    for question in questions:
        if not isinstance(question, dict):
            continue
        if question.get("question_type") == "topic_mastery":
            topic_mastery.append(
                {
                    "topic_id": str(question.get("topic_id")),
                    "topic_title": str(question.get("topic_title")),
                    "mastery_level": "heard",
                }
            )
    if not topic_mastery:
        raise RuntimeError("diagnostic questions did not include topic_mastery items")
    return {
        "question_version": data.get("question_version", "study_plan_diagnostic_v1"),
        "topic_mastery": topic_mastery,
        "weak_area": "calculation",
        "diagnostic_note": "我想重点补信道带宽、码元速率、奈奎斯特/香农公式、编码与调制题目的解题步骤。",
    }


def _build_save_payload(preview_payload: dict[str, object]) -> dict[str, object]:
    data = preview_payload["data"]
    assert isinstance(data, dict)
    return {
        "client_flow": "wizard_v1",
        "title": data["title"],
        "goal_text": data["goal_text"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "duration_days": data.get("duration_days"),
        "daily_available_minutes": data["daily_available_minutes"],
        "recommended_daily_minutes": data.get("recommended_daily_minutes"),
        "daily_minutes_source": data.get("daily_minutes_source"),
        "preference": data.get("preference", "mastery"),
        "diagnostic_profile": data.get("diagnostic_profile", {}),
        "material_snapshot": data.get("material_snapshot", {}),
        "material_scope": data["material_scope"],
        "coverage": data.get("coverage", {}),
        "capacity": data.get("capacity", {}),
        "generation_metadata": data.get("generation_metadata", {}),
        "tasks": data["tasks"],
    }


def _validate_pdf(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "starts_with_pdf_header": path.read_bytes().startswith(b"%PDF"),
    }
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        result["page_count"] = len(reader.pages)
        first_text = reader.pages[0].extract_text() if reader.pages else ""
        result["first_page_text_excerpt"] = (first_text or "")[:500]
    except Exception as exc:
        result["pypdf_error"] = repr(exc)
    return result


def _write_report(
    *,
    run_dir: Path,
    logger: RunLogger,
    status: str,
    started_at: datetime,
    context: dict[str, object],
    error: str | None = None,
) -> Path:
    report_path = run_dir / "report.md"
    elapsed = datetime.now(timezone.utc) - started_at
    lines = [
        "# Study Mode Real E2E 测试报告",
        "",
        f"- 状态：{status}",
        f"- 开始时间：{started_at.isoformat()}",
        f"- 总耗时：{elapsed}",
        f"- 资料：`{context.get('source_pdf', SOURCE_PDF_LABEL)}`",
        f"- 自然语言目标：{GOAL_TEXT}",
        f"- 运行日志：`{logger.log_path.name}`",
        f"- 应用日志目录：`app-logs/`",
        "",
        "## 关键结果",
        "",
        f"- course_id：`{context.get('course_id', '')}`",
        f"- material_id：`{context.get('material_id', '')}`",
        f"- material parse_status：`{context.get('parse_status', '')}`",
        f"- chunk_count：`{context.get('chunk_count', '')}`",
        f"- plan_id：`{context.get('plan_id', '')}`",
        f"- learn/review subtask：`{context.get('learn_subtask_id', '')}`",
        f"- quiz/test subtask：`{context.get('quiz_subtask_id', '')}`",
        f"- handout content：`{context.get('handout_content_id', '')}`",
        f"- task_test content：`{context.get('task_test_content_id', '')}`",
        "",
        "## 产物",
        "",
        f"- 讲义 PDF：`{context.get('handout_pdf', '')}`",
        f"- 测试题 Markdown：`{context.get('task_test_markdown', '')}`",
        f"- QA 回答 JSON：`{context.get('qa_answer_json', '')}`",
        f"- API 摘要 JSON：`{context.get('summary_json', '')}`",
        "",
        "## 学前诊断答案",
        "",
        "```json",
        _json(context.get("diagnostic_answers", {})),
        "```",
        "",
        "## 计划摘要",
        "",
        "```json",
        _json(context.get("plan_summary", {})),
        "```",
        "",
        "## 生成内容摘要",
        "",
        "```json",
        _json(context.get("content_summary", {})),
        "```",
        "",
        "## PDF 验证",
        "",
        "```json",
        _json(context.get("pdf_validation", {})),
        "```",
        "",
        "## 运行日志摘录",
        "",
        "```jsonl",
    ]
    lines.extend(json.dumps(event, ensure_ascii=False, default=str) for event in logger.events[-20:])
    lines.append("```")
    if error:
        lines.extend(["", "## 错误", "", "```text", error, "```"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def run(args: argparse.Namespace) -> int:
    started_at = datetime.now(timezone.utc)
    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "docs" / "domains" / "study-mode" / "validation" / f"real-e2e-physical-layer-{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = RunLogger(run_dir)
    context: dict[str, object] = {"source_pdf": args.pdf.name}
    try:
        _configure_isolated_runtime(run_dir)
        app = _setup_app()
        from fastapi.testclient import TestClient

        client = TestClient(app, raise_server_exceptions=False)
        username = f"study_e2e_{run_stamp}_{uuid4().hex[:6]}"
        password = f"study-e2e-{uuid4().hex}"
        register = _api_json(
            client,
            logger,
            method="POST",
            path="/api/v1/auth/register",
            step="register user",
            json={"username": username, "password": password},
        )
        token = register["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        course = _api_json(
            client,
            logger,
            method="POST",
            path="/api/v1/courses",
            step="create course",
            headers=headers,
            json={"name": "计算机网络", "description": "Study Mode real E2E"},
        )
        course_id = course["data"]["id"]
        context["course_id"] = course_id

        with args.pdf.open("rb") as file:
            upload = _api_json(
                client,
                logger,
                method="POST",
                path=f"/api/v1/courses/{course_id}/materials",
                step="upload material",
                headers=headers,
                files={"file": (args.pdf.name, file, "application/pdf")},
            )
        material_id = upload["data"]["id"]
        context["material_id"] = material_id

        parsed = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/materials/{material_id}/parse-retries",
            step="parse material and index chunks",
            headers=headers,
        )
        material_data = parsed["data"]
        context["parse_status"] = material_data.get("parse_status")
        context["parse_quality"] = material_data.get("parse_quality")
        context["chunk_count"] = _count_chunks(str(material_id))
        _write_json(run_dir / "material.json", parsed)
        if material_data.get("parse_status") != "parsed":
            raise RuntimeError(f"material parse failed: {_json(material_data)}")

        material_scope = {"include_all_parsed_materials": False, "material_ids": [material_id]}
        config = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plan-config-parses",
            step="parse natural language config with model",
            headers=headers,
            json={"goal_text": GOAL_TEXT, "material_scope": material_scope},
        )
        _write_json(run_dir / "config_parse.json", config)

        questions = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
            step="build diagnostic questions",
            headers=headers,
            json={"goal_text": GOAL_TEXT, "material_scope": material_scope},
        )
        diagnostic_answers = _diagnostic_answers(questions)
        context["diagnostic_answers"] = diagnostic_answers
        _write_json(run_dir / "diagnostic_questions.json", questions)
        _write_json(run_dir / "diagnostic_answers.json", diagnostic_answers)

        profile = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plan-diagnostic-profiles",
            step="derive diagnostic profile",
            headers=headers,
            json={**diagnostic_answers, "material_scope": material_scope},
        )
        diagnostic_profile = profile["data"]
        _write_json(run_dir / "diagnostic_profile.json", profile)

        preview = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plans/preview",
            step="generate study plan preview with model",
            headers=headers,
            json={
                "goal_text": GOAL_TEXT,
                "start_date": "2026-07-13",
                "duration_days": 2,
                "preference": "mastery",
                "diagnostic_profile": diagnostic_profile,
                "material_scope": material_scope,
            },
        )
        _write_json(run_dir / "plan_preview.json", preview)

        save_payload = _build_save_payload(preview)
        saved = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plans",
            step="save confirmed plan",
            headers={**headers, "Idempotency-Key": f"study-mode-real-e2e-{run_stamp}"},
            json=save_payload,
        )
        _write_json(run_dir / "plan_saved.json", saved)
        context["plan_id"] = saved["data"]["plan"]["id"]

        learn_subtask = _find_subtask(saved, {"learn", "review"})
        quiz_subtask = _find_subtask(saved, {"quiz", "test"})
        if learn_subtask is None:
            raise RuntimeError("saved plan did not contain a learn/review subtask")
        if quiz_subtask is None:
            raise RuntimeError("saved plan did not contain a quiz/test subtask")
        context["learn_subtask_id"] = learn_subtask["id"]
        context["quiz_subtask_id"] = quiz_subtask["id"]
        context["plan_summary"] = {
            "title": saved["data"]["plan"]["title"],
            "task_count": len(saved["data"]["tasks"]),
            "subtask_count": len(saved["data"]["subtasks"]),
            "subtasks": [
                {
                    "id": subtask["id"],
                    "title": subtask["title"],
                    "type": subtask["subtask_type"],
                    "sort_order": subtask["sort_order"],
                }
                for subtask in saved["data"]["subtasks"]
            ],
        }

        qa = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/study-subtasks/{learn_subtask['id']}/qa/questions",
            step="ask execution-page QA with model",
            headers=headers,
            json={"question": "请基于我的资料解释奈奎斯特公式和香农公式的区别，并指出适用场景。"},
        )
        qa_path = run_dir / "execution_qa_answer.json"
        _write_json(qa_path, qa)
        context["qa_answer_json"] = qa_path.name

        handout = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/study-subtasks/{learn_subtask['id']}/handouts",
            step="generate handout with model",
            headers=headers,
            json={"force_regenerate": True, "parameters": {"language": "zh-CN", "detail_level": "deep"}},
        )
        task_test = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/study-subtasks/{quiz_subtask['id']}/task-tests",
            step="generate task test with model",
            headers=headers,
            json={
                "force_regenerate": True,
                "parameters": {
                    "question_count": 3,
                    "question_types": ["single_choice", "short_answer"],
                    "difficulty": "medium",
                },
            },
        )
        _write_json(run_dir / "handout_content.json", handout)
        _write_json(run_dir / "task_test_content.json", task_test)
        handout_id = handout["data"]["id"]
        task_test_id = task_test["data"]["id"]
        context["handout_content_id"] = handout_id
        context["task_test_content_id"] = task_test_id
        context["content_summary"] = {
            "handout_title": handout["data"].get("title"),
            "handout_status": handout["data"].get("generation_status"),
            "handout_sections": len(handout["data"].get("content_json", {}).get("sections", [])),
            "task_test_title": task_test["data"].get("title"),
            "task_test_status": task_test["data"].get("generation_status"),
            "task_test_questions": len(task_test["data"].get("content_json", {}).get("questions", [])),
        }

        handout_pdf = run_dir / f"handout-{handout_id}.pdf"
        task_test_md = run_dir / f"task-test-{task_test_id}.md"
        _api_file(
            client,
            logger,
            path=f"/api/v1/generated-contents/{handout_id}/exports/pdf",
            step="export handout pdf",
            output_path=handout_pdf,
            headers=headers,
        )
        _api_file(
            client,
            logger,
            path=f"/api/v1/generated-contents/{task_test_id}/exports/markdown",
            step="export task test markdown",
            output_path=task_test_md,
            headers=headers,
        )
        context["handout_pdf"] = handout_pdf.name
        context["task_test_markdown"] = task_test_md.name
        context["pdf_validation"] = _validate_pdf(handout_pdf)

        summary_path = run_dir / "summary.json"
        context["summary_json"] = summary_path.name
        _write_json(summary_path, context)
        report = _write_report(
            run_dir=run_dir,
            logger=logger,
            status="PASS",
            started_at=started_at,
            context=context,
        )
        logger.event("write report", "ok", report=str(report))
        print(str(report))
        return 0
    except Exception as exc:
        error = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.event("run failed", "failed", error=error)
        summary_path = run_dir / "summary.json"
        context["summary_json"] = summary_path.name
        _write_json(summary_path, context)
        report = _write_report(
            run_dir=run_dir,
            logger=logger,
            status="FAIL",
            started_at=started_at,
            context=context,
            error=error,
        )
        print(str(report))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real Study Mode E2E flow with configured model providers.")
    parser.add_argument("--pdf", type=Path, required=True, help="PDF material to upload for the E2E run")
    args = parser.parse_args()
    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
