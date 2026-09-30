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
from app.modules.course_qa.schemas import ConversationRead, CourseQuestionCreate, MessageRead
from app.modules.course_qa.service import ask_course_question, list_conversation_messages, list_course_conversations
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["course_qa"])


def get_model_provider() -> ModelProvider:
    return create_model_provider("course_qa")


@router.get("/courses/{course_id}/conversations")
def list_conversations_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    conversations = list_course_conversations(db, user_id=current_user.id, course_id=course_id)
    data = [ConversationRead.model_validate(conversation).model_dump(mode="json") for conversation in conversations]
    return success_response(data, request_id=get_request_id(request))


@router.get("/conversations/{conversation_id}/messages")
def list_messages_endpoint(
    conversation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    messages = list_conversation_messages(db, user_id=current_user.id, conversation_id=conversation_id)
    data = [message.model_dump(mode="json") for message in messages]
    return success_response(data, request_id=get_request_id(request))


@router.post("/courses/{course_id}/qa/questions")
def ask_question_endpoint(
    course_id: str,
    payload: CourseQuestionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_model_provider),
    rag_index: RagIndex = Depends(get_retrieval_rag_index),
) -> dict[str, object]:
    settings = get_settings()
    answer = ask_course_question(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        rag_index=rag_index,
        top_k=settings.rag_similarity_top_k,
    )
    return success_response(answer.model_dump(mode="json"), request_id=get_request_id(request))
