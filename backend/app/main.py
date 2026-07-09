from fastapi import FastAPI

from app.api.router import api_router
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware

app = FastAPI(title="CourseNexus API", version="0.1.0")

app.add_middleware(RequestIdMiddleware)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
