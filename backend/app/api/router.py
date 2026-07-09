from fastapi import APIRouter, Request

from app.core.request_id import get_request_id
from app.modules.course_qa.router import router as course_qa_router
from app.modules.courses.router import router as courses_router
from app.modules.generated_content.router import router as generated_content_router
from app.modules.generation.orchestrator.router import router as generation_router
from app.modules.materials.router import router as materials_router
from app.modules.study_plans.router import router as study_plans_router
from app.modules.users.router import router as users_router
from app.shared.responses import success_response

api_router = APIRouter()

api_router.include_router(users_router)
api_router.include_router(courses_router)
api_router.include_router(materials_router)
api_router.include_router(course_qa_router)
api_router.include_router(generated_content_router)
api_router.include_router(generation_router)
api_router.include_router(study_plans_router)


@api_router.get("/health", tags=["system"])
def health(request: Request) -> dict[str, object]:
    return success_response({"status": "ok"}, request_id=get_request_id(request))
