from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_rag_index, get_required_user
from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.integrations.file_storage.base import FileStorage
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.base import Parser
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.base import RagIndex
from app.modules.materials.schemas import (
    MaterialFolderAssignment,
    MaterialFolderCreate,
    MaterialFolderRead,
    MaterialFolderUpdate,
    MaterialLinkCreate,
    MaterialRead,
)
from app.modules.materials.service import (
    create_material_folder,
    create_link_material,
    delete_material_folder,
    delete_material,
    get_material_detail,
    list_material_folders,
    list_course_materials,
    move_material_to_folder,
    parse_material,
    update_material_folder,
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


def _material_data(material) -> dict[str, object]:
    return MaterialRead.model_validate(material).model_dump(mode="json")


def _folder_data(folder) -> dict[str, object]:
    return MaterialFolderRead.model_validate(folder).model_dump(mode="json")


@router.get("/courses/{course_id}/material-folders")
def list_material_folders_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    folders = list_material_folders(db, current_user.id, course_id)
    return success_response([_folder_data(folder) for folder in folders], request_id=get_request_id(request))


@router.post("/courses/{course_id}/material-folders")
def create_material_folder_endpoint(
    course_id: str,
    payload: MaterialFolderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    folder = create_material_folder(db, user_id=current_user.id, course_id=course_id, payload=payload)
    return success_response(_folder_data(folder), request_id=get_request_id(request))


@router.patch("/material-folders/{folder_id}")
def update_material_folder_endpoint(
    folder_id: str,
    payload: MaterialFolderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    folder = update_material_folder(db, user_id=current_user.id, folder_id=folder_id, payload=payload)
    return success_response(_folder_data(folder), request_id=get_request_id(request))


@router.delete("/material-folders/{folder_id}")
def delete_material_folder_endpoint(
    folder_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    rag_index: RagIndex = Depends(get_rag_index),
) -> dict[str, object]:
    folder = delete_material_folder(db, user_id=current_user.id, folder_id=folder_id, rag_index=rag_index)
    return success_response(_folder_data(folder), request_id=get_request_id(request))


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
    folder_id: str | None = Form(default=None),
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
        folder_id=folder_id,
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


@router.patch("/materials/{material_id}/folder")
def move_material_to_folder_endpoint(
    material_id: str,
    payload: MaterialFolderAssignment,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    rag_index: RagIndex = Depends(get_rag_index),
) -> dict[str, object]:
    material = move_material_to_folder(
        db,
        user_id=current_user.id,
        material_id=material_id,
        folder_id=payload.folder_id,
        rag_index=rag_index,
    )
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
