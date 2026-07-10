from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.main import app
from app.modules.study_plans import router as study_plan_router


class ConfigParseProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        self.prompts.append(prompt)
        return output_schema.model_validate(
            {
                "goal_text": "精通传输层",
                "start_date": "2026-07-11",
                "end_date": "2026-07-24",
                "daily_available_minutes": 60,
                "preference": "mastery",
                "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
                "unresolved_fields": [],
            }
        )


@pytest.fixture()
def api_context() -> Generator[tuple[TestClient, ConfigParseProvider], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    provider = ConfigParseProvider()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[study_plan_router.get_model_provider] = lambda: provider
    try:
        yield TestClient(app), provider
    finally:
        app.dependency_overrides.clear()


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def create_course(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": "Computer Networks"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_config_parse_endpoint_returns_success_envelope(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, provider = api_context
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-config-parses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "goal_text": "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "goal_text": "精通传输层",
        "start_date": "2026-07-11",
        "end_date": "2026-07-24",
        "daily_available_minutes": 60,
        "preference": "mastery",
        "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        "unresolved_fields": [],
    }
    assert provider.prompts


def test_config_parse_endpoint_requires_authentication(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context

    response = client.post(
        "/api/v1/courses/crs_missing/study-plan-config-parses",
        json={"goal_text": "两周掌握传输层"},
    )

    assert response.status_code == 401