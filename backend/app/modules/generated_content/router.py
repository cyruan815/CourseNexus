from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.generated_content.schemas import GeneratedContentRead
from app.modules.generated_content.service import get_generated_content_detail, list_generated_contents
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["generated_content"])


@router.get("/courses/{course_id}/generated-contents")
def list_generated_contents_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    contents = list_generated_contents(db, user_id=current_user.id, course_id=course_id)
    data = [GeneratedContentRead.model_validate(content).model_dump(mode="json") for content in contents]
    return success_response(data, request_id=get_request_id(request))


@router.get("/generated-contents/{generated_content_id}")
def get_generated_content_endpoint(
    generated_content_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    content = get_generated_content_detail(db, user_id=current_user.id, generated_content_id=generated_content_id)
    data = GeneratedContentRead.model_validate(content).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))
