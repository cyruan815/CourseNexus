from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware

settings = get_settings()
configure_logging(settings)
app = FastAPI(title="CourseNexus API", version="0.1.0")

app.add_middleware(RequestIdMiddleware, slow_request_ms=settings.slow_request_ms)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
