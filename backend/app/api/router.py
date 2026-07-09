from fastapi import APIRouter, Request

from app.core.request_id import get_request_id
from app.shared.responses import success_response

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health(request: Request) -> dict[str, object]:
    return success_response({"status": "ok"}, request_id=get_request_id(request))
