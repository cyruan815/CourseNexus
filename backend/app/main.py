from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware

settings = get_settings()
configure_logging(settings)
app = FastAPI(title="CourseNexus API", version="0.1.0")

app.add_middleware(RequestIdMiddleware, slow_request_ms=settings.slow_request_ms)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
