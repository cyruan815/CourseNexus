from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.users.schemas import ChangePasswordRequest, UserCreate, UserLogin, UserRead
from app.modules.users.service import (
    authenticate_user,
    build_auth_response,
    change_password,
    register_user,
)
from app.shared.responses import success_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    user = register_user(db, payload)
    auth_response = build_auth_response(user)
    return success_response(auth_response.model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/login")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    user = authenticate_user(db, username=payload.username, password=payload.password)
    auth_response = build_auth_response(user)
    return success_response(auth_response.model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/me")
def me(request: Request, current_user: User = Depends(get_required_user)) -> dict[str, object]:
    return success_response(
        UserRead.model_validate(current_user).model_dump(mode="json"),
        request_id=get_request_id(request),
    )


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_required_user)) -> dict[str, object]:
    return success_response({"logged_out": True}, request_id=get_request_id(request))


@router.post("/change-password")
def change_password_endpoint(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    change_password(
        db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return success_response(
        {"password_changed": True, "relogin_required": True},
        request_id=get_request_id(request),
    )
