from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user, get_retrieval_rag_index
from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.factory import create_model_provider
from app.integrations.rag.base import RagIndex
from app.modules.learning_execution.schemas import (
    ExecutionContextRead,
    HandoutGenerationRequest,
    SubTaskCompletionResult,
    TaskQAQuestionRequest,
    SubTaskCompletionUpdate,
    TaskTestGenerationRequest,
)
from app.modules.learning_execution.service import (
    ask_subtask_question,
    generate_handout_for_subtask,
    generate_task_test_for_subtask,
    get_execution_context,
    set_subtask_completion,
)
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["learning_execution"])


def get_handout_model_provider() -> ModelProvider:
    return create_model_provider("handout")


def get_task_test_model_provider() -> ModelProvider:
    return create_model_provider("task_test")


def get_task_qa_model_provider() -> ModelProvider:
    return create_model_provider("course_qa")


@router.get("/study-subtasks/{subtask_id}/execution-context")
def get_execution_context_endpoint(
    subtask_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_execution_context(db, user_id=current_user.id, subtask_id=subtask_id)
    return success_response(ExecutionContextRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/study-subtasks/{subtask_id}/handouts")
def generate_handout_endpoint(
    subtask_id: str,
    payload: HandoutGenerationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_handout_model_provider),
) -> dict[str, object]:
    settings = get_settings()
    data = generate_handout_for_subtask(
        db,
        user_id=current_user.id,
        subtask_id=subtask_id,
        parameters=payload.parameters.model_dump(mode="json", exclude_unset=True),
        force_regenerate=payload.force_regenerate,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
    )
    return success_response(data.model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/study-subtasks/{subtask_id}/task-tests")
def generate_task_test_endpoint(
    subtask_id: str,
    payload: TaskTestGenerationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_task_test_model_provider),
) -> dict[str, object]:
    settings = get_settings()
    data = generate_task_test_for_subtask(
        db,
        user_id=current_user.id,
        subtask_id=subtask_id,
        parameters=payload.parameters.model_dump(mode="json", exclude_unset=True),
        force_regenerate=payload.force_regenerate,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
    )
    return success_response(data.model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/study-subtasks/{subtask_id}/qa/questions")
def ask_subtask_question_endpoint(
    subtask_id: str,
    payload: TaskQAQuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_task_qa_model_provider),
    rag_index: RagIndex = Depends(get_retrieval_rag_index),
) -> dict[str, object]:
    settings = get_settings()
    answer = ask_subtask_question(
        db,
        user_id=current_user.id,
        subtask_id=subtask_id,
        conversation_id=payload.conversation_id,
        question=payload.question,
        model_provider=model_provider,
        rag_index=rag_index,
        top_k=settings.rag_similarity_top_k,
    )
    return success_response(answer.model_dump(mode="json"), request_id=get_request_id(request))


@router.put("/study-subtasks/{subtask_id}/completion")
def update_subtask_completion_endpoint(
    subtask_id: str,
    payload: SubTaskCompletionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = set_subtask_completion(db, user_id=current_user.id, subtask_id=subtask_id, completed=payload.completed)
    return success_response(SubTaskCompletionResult.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))
