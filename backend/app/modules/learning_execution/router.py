from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.learning_execution.schemas import ExecutionContextRead
from app.modules.learning_execution.service import get_execution_context
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["learning_execution"])


@router.get("/study-subtasks/{subtask_id}/execution-context")
def get_execution_context_endpoint(
    subtask_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_execution_context(db, user_id=current_user.id, subtask_id=subtask_id)
    return success_response(ExecutionContextRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))