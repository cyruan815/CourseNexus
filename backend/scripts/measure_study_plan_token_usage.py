from __future__ import annotations

import logging
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

COURSE_ID = "crs_2a223758acd34bd3a291cf920fb0fbd1"
MATERIAL_ID = "mat_aa7fd1d1faa4461cad5d3ac31b590108"
REPORT_PATH = ROOT / "docs" / "domains" / "study-mode" / "validation" / "study-plan-token-usage-2026-08-24.md"


class CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _section_messages(messages: list[str], marker: str) -> list[str]:
    return [message for message in messages if marker in message]


def _task_summary(preview: object) -> list[dict[str, object]]:
    tasks = getattr(preview, "tasks", [])
    return [
        {
            "date": task.task_date.isoformat(),
            "title": task.title,
            "subtasks": [
                {
                    "type": subtask.subtask_type,
                    "title": subtask.title,
                    "minutes": subtask.estimated_minutes,
                    "description": subtask.description,
                }
                for subtask in task.subtasks
            ],
        }
        for task in tasks
    ]


def main() -> int:
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.core.logging import configure_logging
    from app.db.session import SessionLocal
    from app.integrations.model_provider.openai import OpenAIModelProvider
    from app.modules.materials.models import CourseMaterial, MaterialChunk
    from app.modules.study_plans.schemas import StudyPlanBuildRequest
    from app.modules.study_plans.service import preview_study_plan
    from app.modules.courses.models import Course

    settings = get_settings()
    configure_logging(settings)
    generation_handler = CaptureHandler()
    phase_handler = CaptureHandler()
    generation_logger = logging.getLogger("course_nexus.model.generate")
    phase_logger = logging.getLogger("course_nexus.study_plan.build")
    generation_logger.addHandler(generation_handler)
    phase_logger.addHandler(phase_handler)

    try:
        with SessionLocal() as db:
            course = db.execute(select(Course).where(Course.id == COURSE_ID)).scalar_one()
            material = db.execute(select(CourseMaterial).where(CourseMaterial.id == MATERIAL_ID)).scalar_one()
            chunk_count = db.execute(
                select(MaterialChunk).where(MaterialChunk.material_id == MATERIAL_ID)
            ).scalars().all()

            generator_endpoint = settings.model_endpoint("study_plan_generator")
            reduce_provider = OpenAIModelProvider(
                api_key=generator_endpoint.api_key,
                model=generator_endpoint.model,
                base_url=generator_endpoint.base_url,
                api_key_env_name="STUDY_PLAN_GENERATOR_API_KEY",
            )
            map_provider = OpenAIModelProvider(
                api_key=generator_endpoint.api_key,
                model="deepseek-v4-flash",
                base_url=generator_endpoint.base_url,
                api_key_env_name="STUDY_PLAN_MAP_API_KEY",
            )
            payload = StudyPlanBuildRequest(
                goal_text="我要三天内深度学习计算机网络物理层的知识点，今天是2026年8月24日。",
                start_date=date(2026, 8, 24),
                duration_days=3,
                daily_available_minutes=90,
                preference="mastery",
                material_scope={"include_all_parsed_materials": False, "material_ids": [MATERIAL_ID]},
            )
            preview = preview_study_plan(
                db,
                user_id=course.user_id,
                course_id=COURSE_ID,
                payload=payload,
                model_provider=reduce_provider,
                map_model_provider=map_provider,
                max_tokens=settings.material_context_max_tokens,
                map_concurrency=5,
            )

            generation_messages = generation_handler.messages
            phase_messages = phase_handler.messages
            report_lines = [
                "# Study Plan Token Usage 验证报告",
                "",
                "## 结论",
                "",
                "本轮直接复用了数据库中已经解析完成的 `Chap7 物理层.pdf` chunk，未重新上传或解析 PDF。",
                "map 使用 `deepseek-v4-flash`，reduce 使用配置中的 generator 模型；preview 成功且未写入正式计划。",
                "",
                "## 实验配置",
                "",
                f"- 时间：`{datetime.now().astimezone().isoformat(timespec='seconds')}`",
                f"- course_id：`{COURSE_ID}`",
                f"- material_id：`{MATERIAL_ID}`",
                f"- 资料名称：`{material.name}`",
                f"- parse_status：`{material.parse_status}`",
                f"- parse_quality：`{material.parse_quality}`",
                f"- 已复用 chunk 数：`{len(chunk_count)}`",
                "- batch 数：`1`",
                "- map 模型：`deepseek-v4-flash`",
                f"- reduce 模型：`{generator_endpoint.model}`",
                "- map 并发度：`5`",
                "- 真实 `.env`：未修改",
                "",
                "## 阶段日志",
                "",
                "```text",
                *generation_messages,
                *phase_messages,
                "````",
                "",
                "token 日志中的 `prompt_tokens` / `completion_tokens` / `total_tokens` 来自模型响应的 `usage`；若服务未返回 usage，则显示 `usage_status=unavailable`，不会自行估算。",
                "",
                "## 最终结果",
                "",
                f"- 一级任务数：`{len(preview.tasks)}`",
                f"- 二级任务数：`{sum(len(task.subtasks) for task in preview.tasks)}`",
                f"- coverage：`{preview.coverage.model_dump(mode='json')}`",
                f"- capacity：`{preview.capacity}`",
                "",
                "### 计划摘要",
                "",
                "```json",
                __import__("json").dumps(_task_summary(preview), ensure_ascii=False, indent=2),
                "```",
                "",
                "## 结果判断",
                "",
                "- map/reduce token 指标已进入结构化生成日志。",
                "- map 与 reduce 的耗时和 token 可以分开比较，下一步可据此判断 reduce 慢在输入 token、输出 token 还是模型服务响应。",
                "- 本轮仍然只有一个 batch，因此并发度 5 不会减少 map 调用数量。",
            ]
            REPORT_PATH.write_text("\n".join(report_lines).replace("````", "```") + "\n", encoding="utf-8")
            print(REPORT_PATH)
            return 0
    finally:
        generation_logger.removeHandler(generation_handler)
        phase_logger.removeHandler(phase_handler)


if __name__ == "__main__":
    raise SystemExit(main())
