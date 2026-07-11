from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401
import app.modules.generation.orchestrator.router as generation_router
from app.core.errors import CourseNexusError
from app.db.base import Base
from app.db.session import get_db
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.base import ModelAnswer, ModelProvider, StructuredOutputT
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generation.orchestrator.contracts import Generator as ContentGenerator
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.material_context.schemas import ContextChunk
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.router import get_material_storage, get_rag_index
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@dataclass(frozen=True)
class ApiIdentity:
    username: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class RecordingStructuredModelProvider:
    def __init__(self, *outputs: BaseModel | dict[str, Any]) -> None:
        self.outputs = list(outputs)
        self.calls: list[tuple[str, type[BaseModel]]] = []

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        return ModelAnswer(answer_text=question, citation_chunk_ids=[chunk.chunk_id for chunk in context_chunks])

    def generate_structured(
        self, *, prompt: str, output_schema: type[StructuredOutputT]
    ) -> StructuredOutputT:
        self.calls.append((prompt, output_schema))
        if not self.outputs:
            raise AssertionError("No queued structured output")
        return output_schema.model_validate(self.outputs.pop(0))


class FailingModelProvider:
    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        raise self._error()

    def generate_structured(
        self, *, prompt: str, output_schema: type[StructuredOutputT]
    ) -> StructuredOutputT:
        raise self._error()

    @staticmethod
    def _error() -> CourseNexusError:
        return CourseNexusError(code="GENERATION_FAILED", message="Stable provider failure", status_code=500)


@pytest.fixture()
def sqlite_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db(sqlite_engine: Engine) -> Generator[Session, None, None]:
    session = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(sqlite_engine: Engine, tmp_path: Path) -> Generator[TestClient, None, None]:
    testing_session = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)
    rag_index = FakeRagIndex()

    def override_get_db() -> Generator[Session, None, None]:
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_material_storage] = lambda: LocalFileStorage(
        root_path=tmp_path, max_file_size_bytes=4096
    )
    app.dependency_overrides[get_rag_index] = lambda: rag_index
    app.dependency_overrides[generation_router.get_generation_model_provider_factory] = (
        lambda: lambda content_type: MockModelProvider()
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def api_identity_factory(client: TestClient) -> Callable[[str], ApiIdentity]:
    def create(username: str) -> ApiIdentity:
        response = client.post(
            "/api/v1/auth/register", json={"username": username, "password": "password123"}
        )
        assert response.status_code == 200
        return ApiIdentity(username=username, token=response.json()["data"]["access_token"])

    return create


@pytest.fixture()
def alice_api(api_identity_factory: Callable[[str], ApiIdentity]) -> ApiIdentity:
    return api_identity_factory("alice")


@pytest.fixture()
def bob_api(api_identity_factory: Callable[[str], ApiIdentity]) -> ApiIdentity:
    return api_identity_factory("bob")


@pytest.fixture()
def api_course_factory(client: TestClient) -> Callable[[ApiIdentity, str], str]:
    def create(identity: ApiIdentity, name: str = "Linear Algebra") -> str:
        response = client.post("/api/v1/courses", json={"name": name}, headers=identity.headers)
        assert response.status_code == 200
        return response.json()["data"]["id"]

    return create


@pytest.fixture()
def api_material_factory(client: TestClient) -> Callable[..., str]:
    def create(
        identity: ApiIdentity,
        course_id: str,
        *,
        filename: str = "notes.md",
        content: bytes = b"# Intro\nAlpha\n",
        parse: bool = True,
    ) -> str:
        upload = client.post(
            f"/api/v1/courses/{course_id}/materials",
            headers=identity.headers,
            files={"file": (filename, content, "text/markdown")},
        )
        assert upload.status_code == 200
        material_id = upload.json()["data"]["id"]
        if parse:
            parsed = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=identity.headers)
            assert parsed.status_code == 200
        return material_id

    return create


@pytest.fixture()
def alice_user(db: Session) -> User:
    return register_user(db, UserCreate(username="alice-service", password="password123"))


@pytest.fixture()
def bob_user(db: Session) -> User:
    return register_user(db, UserCreate(username="bob-service", password="password123"))


@pytest.fixture()
def owned_course(db: Session, alice_user: User) -> Course:
    return create_course(db, alice_user.id, CourseCreate(name="Linear Algebra"))


@pytest.fixture()
def parsed_material_factory(db: Session, tmp_path: Path) -> Callable[..., CourseMaterial]:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096)

    def create(user_id: str, course_id: str, *, filename: str, content: str) -> CourseMaterial:
        material = upload_file_material(
            db,
            user_id=user_id,
            course_id=course_id,
            filename=filename,
            stream=BytesIO(content.encode("utf-8")),
            content_type="text/markdown",
            storage=storage,
        )
        return parse_material(
            db,
            user_id=user_id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )

    return create


@pytest.fixture()
def parsed_materials(
    db: Session,
    alice_user: User,
    owned_course: Course,
    parsed_material_factory: Callable[..., CourseMaterial],
) -> tuple[CourseMaterial, CourseMaterial]:
    first = parsed_material_factory(
        alice_user.id, owned_course.id, filename="algebra.md", content="Vectors\n\nMatrices"
    )
    second = parsed_material_factory(
        alice_user.id, owned_course.id, filename="geometry.md", content="Angles\n\nTriangles"
    )
    chunks = list(db.query(MaterialChunk).filter(MaterialChunk.material_id.in_([first.id, second.id])))
    assert len(chunks) >= 4
    chunks[0].page = None
    chunks[0].page_index = None
    db.commit()
    return first, second


@pytest.fixture(params=["uploaded", "parse_failed"])
def invalid_material(
    db: Session,
    alice_user: User,
    owned_course: Course,
    parsed_material_factory: Callable[..., CourseMaterial],
    request: pytest.FixtureRequest,
) -> CourseMaterial:
    material = parsed_material_factory(
        alice_user.id, owned_course.id, filename=f"{request.param}.md", content="Not usable"
    )
    material.parse_status = request.param
    material.parse_error = "PARSE_FAILED" if request.param == "parse_failed" else None
    db.commit()
    return material


@pytest.fixture()
def recording_provider_factory() -> Callable[..., RecordingStructuredModelProvider]:
    return RecordingStructuredModelProvider


@pytest.fixture()
def failing_model_provider() -> ModelProvider:
    return FailingModelProvider()


@pytest.fixture()
def registry_factory() -> Callable[[str, Callable[[ModelProvider], ContentGenerator]], GeneratorRegistry]:
    def create(content_type: str, factory: Callable[[ModelProvider], ContentGenerator]) -> GeneratorRegistry:
        registry = GeneratorRegistry()
        registry.register(content_type, factory)
        return registry

    return create
