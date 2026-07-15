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


DEFAULT_GOAL_TEXT = "我要两天内深度学习计算机网络物理层的知识点，今天是2026年7月13日；最后安排 10 道选择题和 3 道计算题检验 Nyquist/Shannon 公式、编码和调制。"
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


def _planned_generation_parameters(saved: dict[str, object], subtask: dict[str, object], content_type: str) -> dict[str, object]:
    data = saved.get("data")
    if not isinstance(data, dict):
        return {}
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return {}
    task_by_id = {task.get("id"): task for task in tasks if isinstance(task, dict)}
    task = task_by_id.get(subtask.get("task_id"))
    if not isinstance(task, dict):
        return {}
    plan = data.get("plan")
    config = plan.get("parsed_config_json") if isinstance(plan, dict) else None
    task_snapshot = config.get("task_snapshot") if isinstance(config, dict) else None
    if not isinstance(task_snapshot, list):
        return {}
    for task_item in task_snapshot:
        if not isinstance(task_item, dict) or task_item.get("sort_order") != task.get("sort_order"):
            continue
        subtasks = task_item.get("subtasks")
        if not isinstance(subtasks, list):
            return {}
        for subtask_item in subtasks:
            if not isinstance(subtask_item, dict) or subtask_item.get("sort_order") != subtask.get("sort_order"):
                continue
            generation_parameters = subtask_item.get("generation_parameters")
            if not isinstance(generation_parameters, dict):
                return {}
            content_parameters = generation_parameters.get(content_type)
            return content_parameters if isinstance(content_parameters, dict) else {}
    return {}


def _run_warnings(context: dict[str, object]) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    capacity = context.get("plan_capacity")
    if isinstance(capacity, dict) and "PLAN_OVER_CAPACITY" in capacity.get("warnings", []):
        warnings.append(
            {
                "code": "PLAN_OVER_CAPACITY",
                "message": "\u8ba1\u5212\u4f30\u7b97\u603b\u65f6\u957f\u8d85\u8fc7\u53ef\u7528\u603b\u65f6\u957f\u3002",
                "estimated_total_minutes": capacity.get("estimated_total_minutes"),
                "available_total_minutes": capacity.get("available_total_minutes"),
                "suggestions": ["\u589e\u52a0\u6bcf\u65e5\u65f6\u95f4", "\u589e\u52a0\u5b66\u4e60\u5929\u6570", "\u6539\u7528\u5feb\u901f\u6a21\u5f0f", "\u51cf\u5c11\u6d4b\u8bd5\u6216 review \u5f3a\u5ea6"],
            }
        )
    request_parameters = context.get("task_test_request_parameters")
    if isinstance(request_parameters, dict) and request_parameters:
        warnings.append(
            {
                "code": "TASK_TEST_PARAMETERS_OVERRIDDEN",
                "message": "\u672c\u6b21 task-test \u8bf7\u6c42\u663e\u5f0f\u8986\u76d6\u4e86\u8ba1\u5212\u5efa\u8bae\u53c2\u6570\u3002",
                "request_parameters": request_parameters,
            }
        )
    return warnings


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
    payload = path.read_bytes()
    result: dict[str, object] = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "starts_with_pdf_header": payload.startswith(b"%PDF"),
        "has_eof_marker": b"%%EOF" in payload[-2048:],
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
        f"- 自然语言目标：{context.get('goal_text', '')}",
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
        f"- 讲义 Markdown：`{context.get('handout_markdown', '')}`",
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
        "## Markdown 验证",
        "",
        "```json",
        _json(context.get("markdown_validation", {})),
        "```",
        "",
        "## Warnings",
        "",
        "```json",
        _json(context.get("warnings", [])),
        "```",
        "",
        "## PDF 导出问题页证据",
        "",
        "```json",
        _json(context.get("pdf_issue_evidence", {})),
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
    goal_text = args.goal
    context: dict[str, object] = {"source_pdf": args.pdf.name, "goal_text": goal_text}
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
            json={"goal_text": goal_text, "material_scope": material_scope},
        )
        _write_json(run_dir / "config_parse.json", config)

        questions = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
            step="build diagnostic questions",
            headers=headers,
            json={"goal_text": goal_text, "material_scope": material_scope},
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

        config_data = config.get("data", {}) if isinstance(config, dict) else {}
        preview_request = {
            "goal_text": goal_text,
            "start_date": config_data.get("start_date") or datetime.now().date().isoformat(),
            "duration_days": config_data.get("duration_days") or 2,
            "preference": config_data.get("preference") or "mastery",
            "diagnostic_profile": diagnostic_profile,
            "material_scope": material_scope,
        }
        if config_data.get("end_date") and not config_data.get("duration_days"):
            preview_request["end_date"] = config_data["end_date"]
        if config_data.get("daily_available_minutes") is not None:
            preview_request["daily_available_minutes"] = config_data["daily_available_minutes"]
        context["preview_request"] = preview_request

        preview = _api_json(
            client,
            logger,
            method="POST",
            path=f"/api/v1/courses/{course_id}/study-plans/preview",
            step="generate study plan preview with model",
            headers=headers,
            json=preview_request,
        )
        _write_json(run_dir / "plan_preview.json", preview)
        preview_data = preview["data"]
        context["plan_capacity"] = preview_data.get("capacity", {}) if isinstance(preview_data, dict) else {}

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
        quiz_subtask = _find_subtask(saved, {"test"}) or _find_subtask(saved, {"quiz"})
        if learn_subtask is None:
            raise RuntimeError("saved plan did not contain a learn/review subtask")
        if quiz_subtask is None:
            raise RuntimeError("saved plan did not contain a quiz/test subtask")
        context["learn_subtask_id"] = learn_subtask["id"]
        context["quiz_subtask_id"] = quiz_subtask["id"]
        planned_task_test_parameters = _planned_generation_parameters(saved, quiz_subtask, "task_test")
        context["planned_task_test_parameters"] = planned_task_test_parameters
        context["task_test_request_parameters"] = {}
        context["plan_summary"] = {
            "title": saved["data"]["plan"]["title"],
            "capacity": context.get("plan_capacity", {}),
            "planned_task_test_parameters": planned_task_test_parameters,
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
            json={"force_regenerate": True, "parameters": {}},
        )
        _write_json(run_dir / "handout_content.json", handout)
        _write_json(run_dir / "task_test_content.json", task_test)
        handout_id = handout["data"]["id"]
        task_test_id = task_test["data"]["id"]
        handout_markdown = str(handout["data"].get("content") or "")
        handout_md = run_dir / f"handout-{handout_id}.md"
        handout_md.write_text(handout_markdown.rstrip() + "\n", encoding="utf-8")
        context["handout_content_id"] = handout_id
        context["task_test_content_id"] = task_test_id
        context["handout_markdown"] = handout_md.name
        context["content_summary"] = {
            "handout_title": handout["data"].get("title"),
            "handout_status": handout["data"].get("generation_status"),
            "handout_markdown_bytes": len(handout_markdown.encode("utf-8")),
            "task_test_title": task_test["data"].get("title"),
            "task_test_status": task_test["data"].get("generation_status"),
            "task_test_questions": len(task_test["data"].get("content_json", {}).get("questions", [])),
            "planned_task_test_parameters": planned_task_test_parameters,
            "task_test_request_parameters": context.get("task_test_request_parameters", {}),
        }

        planned_question_count = planned_task_test_parameters.get("question_count")
        actual_question_count = context["content_summary"]["task_test_questions"]
        if isinstance(planned_question_count, int) and actual_question_count != planned_question_count:
            raise RuntimeError(
                f"task_test question count mismatch: planned={planned_question_count}, actual={actual_question_count}"
            )


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
        markdown_text = task_test_md.read_text(encoding="utf-8")
        context["markdown_validation"] = {
            "handout_bytes": len(handout_markdown.encode("utf-8")),
            "handout_contains_callout": any(marker in handout_markdown for marker in ("[!NOTE]", "[!EXAMPLE]", "[!SUMMARY]", "[!WARNING]", "[!TIP]")),
            "handout_contains_sources_unavailable": "Sources: unavailable" in handout_markdown,
            "handout_contains_formula_not_decoded": "formula-not-decoded" in handout_markdown,
            "bytes": task_test_md.stat().st_size,
            "contains_sources_unavailable": "Sources: unavailable" in markdown_text,
        }
        pdf_validation = context["pdf_validation"]
        if not pdf_validation.get("starts_with_pdf_header") or not pdf_validation.get("has_eof_marker"):
            raise RuntimeError(f"handout pdf validation failed: {_json(pdf_validation)}")
        if not context["markdown_validation"]["handout_contains_callout"]:
            raise RuntimeError("handout markdown does not contain supported callout syntax")
        if context["markdown_validation"]["handout_contains_sources_unavailable"]:
            raise RuntimeError("handout markdown contains Sources: unavailable")
        if context["markdown_validation"]["handout_contains_formula_not_decoded"]:
            raise RuntimeError("handout markdown contains formula-not-decoded")
        if context["markdown_validation"]["contains_sources_unavailable"]:
            raise RuntimeError("task-test markdown contains Sources: unavailable")

        context["pdf_issue_evidence"] = {
            "source_pdf": str(args.pdf),
            "fixed_export_pdf": handout_pdf.name,
            "handout_markdown_excerpt": handout_markdown[:800],
        }
        context["warnings"] = _run_warnings(context)

        summary_path = run_dir / "summary.json"
        context["summary_json"] = summary_path.name
        _write_json(summary_path, context)
        report_status = "PASS_WITH_WARNINGS" if context["warnings"] else "PASS"
        report = _write_report(
            run_dir=run_dir,
            logger=logger,
            status=report_status,
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
    parser.add_argument("--goal", default=DEFAULT_GOAL_TEXT, help="Natural language study goal for config parsing and plan preview")
    args = parser.parse_args()
    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
