from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.integrations.file_storage.base import FileStorage
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.base import Parser
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.base import RagIndex
from app.integrations.rag.llama_index_chroma import create_openai_chroma_rag_index
from app.modules.materials.schemas import MaterialLinkCreate, MaterialRead
from app.modules.materials.service import (
    create_link_material,
    delete_material,
    get_material_detail,
    list_course_materials,
    parse_material,
    upload_file_material,
)
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["materials"])


def get_material_storage() -> FileStorage:
    settings = get_settings()
    return LocalFileStorage(
        root_path=settings.file_storage_path,
        max_file_size_bytes=settings.max_upload_file_size_bytes,
    )


def get_material_parser() -> Parser:
    from app.integrations.parsers.docling_parser import DoclingParser
    from app.integrations.parsers.routing import RoutingParser

    settings = get_settings()
    return RoutingParser(
        plain_text=PlainTextParser(),
        docling=DoclingParser(max_tokens=settings.rag_chunk_max_tokens),
    )


def get_rag_index() -> RagIndex:
    settings = get_settings()
    if not settings.openai_api_key:
        raise CourseNexusError(code="INDEXING_FAILED", message="资料索引配置缺失", status_code=502)
    return create_openai_chroma_rag_index(
        persist_path=settings.chroma_persist_path,
        collection_name=settings.chroma_collection,
        api_key=settings.openai_api_key,
        embedding_model=settings.openai_embedding_model,
    )


def _material_data(material) -> dict[str, object]:
    return MaterialRead.model_validate(material).model_dump(mode="json")


@router.get("/courses/{course_id}/materials")
def list_materials_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    materials = list_course_materials(db, current_user.id, course_id)
    data = [_material_data(material) for material in materials]
    return success_response(data, request_id=get_request_id(request))


@router.post("/courses/{course_id}/materials")
def upload_material_endpoint(
    course_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    storage: FileStorage = Depends(get_material_storage),
) -> dict[str, object]:
    material = upload_file_material(
        db,
        user_id=current_user.id,
        course_id=course_id,
        filename=file.filename or "",
        stream=file.file,
        content_type=file.content_type,
        storage=storage,
    )
    return success_response(_material_data(material), request_id=get_request_id(request))


@router.post("/courses/{course_id}/material-links")
def create_link_material_endpoint(
    course_id: str,
    payload: MaterialLinkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    material = create_link_material(db, user_id=current_user.id, course_id=course_id, payload=payload)
    return success_response(_material_data(material), request_id=get_request_id(request))


@router.get("/materials/{material_id}")
def get_material_endpoint(
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    material = get_material_detail(db, current_user.id, material_id)
    return success_response(_material_data(material), request_id=get_request_id(request))


@router.delete("/materials/{material_id}")
def delete_material_endpoint(
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    rag_index: RagIndex = Depends(get_rag_index),
) -> dict[str, object]:
    material = delete_material(db, current_user.id, material_id, rag_index=rag_index)
    return success_response(_material_data(material), request_id=get_request_id(request))


@router.post("/materials/{material_id}/parse-retries")
def retry_parse_material_endpoint(
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    parser: Parser = Depends(get_material_parser),
    storage: FileStorage = Depends(get_material_storage),
    rag_index: RagIndex = Depends(get_rag_index),
) -> dict[str, object]:
    material = parse_material(
        db,
        user_id=current_user.id,
        material_id=material_id,
        parser=parser,
        rag_index=rag_index,
        storage_root=getattr(storage, "root_path", get_settings().file_storage_path),
    )
    return success_response(_material_data(material), request_id=get_request_id(request))
