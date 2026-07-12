from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.db.session import get_db
from app.modules.exports.service import export_generated_content_markdown, export_generated_content_pdf
from app.modules.users.models import User

router = APIRouter(tags=["exports"])


@router.get("/generated-contents/{generated_content_id}/exports/markdown")
def export_generated_content_markdown_endpoint(
    generated_content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> Response:
    markdown, filename = export_generated_content_markdown(
        db,
        user_id=current_user.id,
        generated_content_id=generated_content_id,
    )
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/generated-contents/{generated_content_id}/exports/pdf")
def export_generated_content_pdf_endpoint(
    generated_content_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> Response:
    pdf, filename = export_generated_content_pdf(
        db,
        user_id=current_user.id,
        generated_content_id=generated_content_id,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
