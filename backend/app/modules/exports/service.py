from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.exports.renderer import render_handout_pdf, render_task_test_markdown
from app.modules.generated_content.service import get_generated_content_detail


def export_generated_content_markdown(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
) -> tuple[str, str]:
    content = get_generated_content_detail(db, user_id=user_id, generated_content_id=generated_content_id)
    if content.content_type != "task_test":
        raise CourseNexusError(
            code="EXPORT_UNSUPPORTED_CONTENT_TYPE",
            message="当前内容类型不支持 Markdown 导出",
            status_code=409,
            details={"content_type": content.content_type, "export_format": "markdown"},
        )
    if content.generation_status != "success":
        raise CourseNexusError(
            code="EXPORT_CONTENT_NOT_READY",
            message="生成内容尚未成功，无法导出",
            status_code=409,
            details={"generation_status": content.generation_status},
        )

    markdown = render_task_test_markdown(content)
    return markdown, f"task-test-{content.id}.md"


def export_generated_content_pdf(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
) -> tuple[bytes, str]:
    content = get_generated_content_detail(db, user_id=user_id, generated_content_id=generated_content_id)
    if content.content_type != "handout":
        raise CourseNexusError(
            code="EXPORT_UNSUPPORTED_CONTENT_TYPE",
            message="当前内容类型不支持 PDF 导出",
            status_code=409,
            details={"content_type": content.content_type, "export_format": "pdf"},
        )
    if content.generation_status != "success":
        raise CourseNexusError(
            code="EXPORT_CONTENT_NOT_READY",
            message="生成内容尚未成功，无法导出",
            status_code=409,
            details={"generation_status": content.generation_status},
        )

    try:
        pdf = render_handout_pdf(content)
    except CourseNexusError:
        raise
    except Exception as exc:
        raise CourseNexusError(
            code="EXPORT_FAILED",
            message="PDF 导出失败",
            status_code=500,
        ) from exc
    return pdf, f"handout-{content.id}.pdf"
