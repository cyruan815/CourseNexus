from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.modules.model_runtime.schemas import ModelRuntimeConfigUpdate
from app.modules.model_runtime.service import (
    get_model_runtime_config,
    save_model_runtime_config,
)
from app.modules.users.models import User
from app.shared.responses import success_response


router = APIRouter(prefix="/model-runtime", tags=["model-runtime"])


@router.get("/config")
def get_model_runtime_config_endpoint(
    request: Request,
    _current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    config = get_model_runtime_config()
    return success_response(
        config.model_dump(mode="json"),
        request_id=get_request_id(request),
    )


@router.put("/config")
def update_model_runtime_config_endpoint(
    payload: ModelRuntimeConfigUpdate,
    request: Request,
    _current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    config = save_model_runtime_config(payload)
    return success_response(
        config.model_dump(mode="json"),
        request_id=get_request_id(request),
    )
