"""跨领域共享的 Study Mode 测试样本构造入口。

按 V1 收尾 E02 要求，收敛多个测试文件重复出现的计划树与讲义样本构造。
契约依据（构造出的样本必须满足）：

- ``docs/domains/study-mode/plan-lifecycle.md``：保存与预览校验要求每个一级任务
  恰好包含一个 ``quiz``/``test`` 子任务并排在当天最后；非最后一天的测试覆盖当天
  前置学习任务的资料，最后一天的测试覆盖全计划资料；每个二级任务必须关联范围内资料。
- ``docs/domains/study-mode/task-content.md``：讲义 Markdown 必须至少包含一张
  安全内联 SVG 图示，且不得包含 Mermaid 代码块。
"""
from __future__ import annotations


SAFE_HANDOUT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 72" role="img" '
    'aria-label="学习概念示意图" style="max-width:100%;height:auto">'
    '<rect x="6" y="18" width="70" height="34" rx="6" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<text x="24" y="40" font-size="14">概念</text>'
    '<line x1="76" y1="35" x2="118" y2="35" stroke="currentColor" stroke-width="2"/>'
    '<rect x="118" y="18" width="70" height="34" rx="6" fill="none" stroke="currentColor" stroke-width="2"/>'
    '<text x="136" y="40" font-size="14">应用</text>'
    "</svg>"
)


def handout_markdown(*, title: str, body: str) -> str:
    """构造能通过讲义安全 SVG 图示校验的 Markdown 样本。"""
    return f"# {title}\n\n{body}\n\n{SAFE_HANDOUT_SVG}"


def study_subtask(
    *,
    title: str,
    subtask_type: str,
    material_ids: list[str],
    description: str = "学习内容",
    estimated_minutes: int = 30,
    citation_chunk_ids: list[str] | None = None,
    sort_order: int = 1,
) -> dict[str, object]:
    """构造学习计划二级任务字典。"""
    return {
        "title": title,
        "subtask_type": subtask_type,
        "description": description,
        "related_material_ids": list(material_ids),
        "estimated_minutes": estimated_minutes,
        "citation_chunk_ids": citation_chunk_ids or [],
        "sort_order": sort_order,
    }


def compliant_daily_task(
    *,
    title: str,
    task_date: str,
    sort_order: int,
    plan_material_ids: list[str],
    study_subtasks: list[dict[str, object]] | None = None,
    assessment_title: str = "当日测试",
) -> dict[str, object]:
    """构造满足保存契约的一级任务：学习/复习子任务 + 排最后的唯一测试子任务。

    测试子任务覆盖全计划资料集合，因此同时满足“非最后一天覆盖当天资料”和
    “最后一天综合覆盖全计划资料”两条规则（覆盖集为要求集的超集即合法）。
    ``study_subtasks`` 可传自定义 learn/review 子任务，不得包含 quiz/test。
    """
    studies = (
        study_subtasks
        if study_subtasks is not None
        else [study_subtask(title=f"学习 {title}", subtask_type="learn", material_ids=plan_material_ids)]
    )
    assessment = study_subtask(
        title=assessment_title,
        subtask_type="test",
        material_ids=sorted(set(plan_material_ids)),
        description="完成当日测试",
        estimated_minutes=15,
        sort_order=len(studies) + 1,
    )
    return {
        "title": title,
        "task_date": task_date,
        "sort_order": sort_order,
        "subtasks": [*studies, assessment],
    }
