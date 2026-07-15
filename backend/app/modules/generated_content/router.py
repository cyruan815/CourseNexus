from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.generated_content.schemas import FlashcardCardsUpdate, GeneratedContentUpdate
from app.modules.generated_content.service import (
    delete_generated_content,
    get_generated_content_detail,
    list_generated_contents,
    rename_generated_content,
    update_flashcard_cards,
)
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
    data = [content.model_dump(mode="json") for content in contents]
    return success_response(data, request_id=get_request_id(request))


@router.get("/generated-contents/{generated_content_id}")
def get_generated_content_endpoint(
    generated_content_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    content = get_generated_content_detail(db, user_id=current_user.id, generated_content_id=generated_content_id)
    data = content.model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.patch("/generated-contents/{generated_content_id}")
def rename_generated_content_endpoint(
    generated_content_id: str,
    payload: GeneratedContentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    content = rename_generated_content(
        db,
        user_id=current_user.id,
        generated_content_id=generated_content_id,
        title=payload.title,
    )
    return success_response(content.model_dump(mode="json"), request_id=get_request_id(request))


@router.delete("/generated-contents/{generated_content_id}")
def delete_generated_content_endpoint(
    generated_content_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    content = delete_generated_content(
        db,
        user_id=current_user.id,
        generated_content_id=generated_content_id,
    )
    return success_response(content.model_dump(mode="json"), request_id=get_request_id(request))


@router.patch("/generated-contents/{generated_content_id}/flashcards")
def update_flashcard_cards_endpoint(
    generated_content_id: str,
    payload: FlashcardCardsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    content = update_flashcard_cards(
        db,
        user_id=current_user.id,
        generated_content_id=generated_content_id,
        cards=[card.model_dump(mode="json") for card in payload.cards],
    )
    return success_response(content.model_dump(mode="json"), request_id=get_request_id(request))
