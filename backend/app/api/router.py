from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
