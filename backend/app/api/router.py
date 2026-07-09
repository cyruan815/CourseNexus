from fastapi import APIRouter, Request

from app.core.request_id import get_request_id
from app.modules.courses.router import router as courses_router
from app.modules.users.router import router as users_router
from app.shared.responses import success_response

api_router = APIRouter()

api_router.include_router(users_router)
api_router.include_router(courses_router)


@api_router.get("/health", tags=["system"])
def health(request: Request) -> dict[str, object]:
    return success_response({"status": "ok"}, request_id=get_request_id(request))
