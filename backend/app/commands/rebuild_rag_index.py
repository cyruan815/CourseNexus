from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.logging import configure_logging, get_logger
from app.core.paths import assert_no_legacy_data_conflicts
from app.db.session import SessionLocal
from app.integrations.rag.base import RagChunk, RagIndex
from app.integrations.rag.llama_index_chroma import create_openai_chroma_rag_index
from app.modules.materials.models import CourseMaterial, MaterialChunk


logger = get_logger("command.rebuild_rag")


@dataclass(frozen=True)
class RebuildRagIndexResult:
    material_count: int
    chunk_count: int


def rebuild_all(*, db: Session, rag_index: RagIndex) -> RebuildRagIndexResult:
    rag_index.clear()
    return _index_rows(_parsed_chunk_rows(db), rag_index=rag_index)


def rebuild_material(*, db: Session, rag_index: RagIndex, material_id: str) -> RebuildRagIndexResult:
    material = db.execute(
        select(CourseMaterial).where(
            CourseMaterial.id == material_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status != "deleted",
        )
    ).scalar_one_or_none()
    if material is None:
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)

    rag_index.delete_material(material.id)
    if material.parse_status != "parsed":
        return RebuildRagIndexResult(material_count=0, chunk_count=0)

    return _index_rows(_parsed_chunk_rows(db, material_id=material.id), rag_index=rag_index)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the CourseNexus material RAG index from SQLite chunks.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--all", action="store_true", help="Rebuild the configured Chroma collection from all parsed materials.")
    target.add_argument("--material-id", help="Rebuild one material's derived index records.")
    args = parser.parse_args(argv)

    settings = get_settings()
    assert_no_legacy_data_conflicts(
        database_url=settings.database_url,
        file_storage_path=settings.file_storage_path,
        chroma_persist_path=settings.chroma_persist_path,
    )
    configure_logging(settings)
    started_at = perf_counter()
    endpoint = settings.model_endpoint("embedding")
    if not endpoint.api_key:
        logger.error("索引重建失败：Embedding 配置缺失 | code=INDEXING_FAILED")
        return 1

    rag_index = create_openai_chroma_rag_index(
        persist_path=settings.chroma_persist_path,
        collection_name=settings.chroma_collection,
        api_key=endpoint.api_key,
        embedding_model=endpoint.model,
        api_base_url=endpoint.base_url,
    )
    try:
        with SessionLocal() as db:
            if args.all:
                result = rebuild_all(db=db, rag_index=rag_index)
            else:
                result = rebuild_material(db=db, rag_index=rag_index, material_id=args.material_id)
    except CourseNexusError as exc:
        cause = exc.__cause__
        logger.error(
            "索引重建失败 | code=%s cost_ms=%.2f",
            exc.code,
            (perf_counter() - started_at) * 1000,
            exc_info=(type(cause), cause, cause.__traceback__) if cause is not None else None,
        )
        return 1
    except Exception as exc:
        logger.error(
            "索引重建失败 | code=INDEXING_FAILED cost_ms=%.2f",
            (perf_counter() - started_at) * 1000,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return 1

    logger.info(
        "索引重建成功 | materials=%d chunks=%d cost_ms=%.2f",
        result.material_count,
        result.chunk_count,
        (perf_counter() - started_at) * 1000,
    )
    return 0


def _index_rows(
    rows: list[tuple[CourseMaterial, MaterialChunk]],
    *,
    rag_index: RagIndex,
) -> RebuildRagIndexResult:
    rag_chunks = [_rag_chunk_for_row(material, chunk) for material, chunk in rows]
    rag_index.index_chunks(rag_chunks)
    return RebuildRagIndexResult(
        material_count=len({chunk.material_id for chunk in rag_chunks}),
        chunk_count=len(rag_chunks),
    )


def _parsed_chunk_rows(db: Session, material_id: str | None = None) -> list[tuple[CourseMaterial, MaterialChunk]]:
    statement = (
        select(CourseMaterial, MaterialChunk)
        .join(MaterialChunk, MaterialChunk.material_id == CourseMaterial.id)
        .where(
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status == "parsed",
        )
        .order_by(CourseMaterial.id.asc(), MaterialChunk.chunk_index.asc())
    )
    if material_id is not None:
        statement = statement.where(CourseMaterial.id == material_id)

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def _rag_chunk_for_row(material: CourseMaterial, chunk: MaterialChunk) -> RagChunk:
    return RagChunk(
        chunk_id=chunk.id,
        user_id=material.user_id,
        course_id=material.course_id,
        material_id=material.id,
        folder_id=material.folder_id,
        chunk_index=chunk.chunk_index,
        text=chunk.content_text,
        page=chunk.page,
        page_index=chunk.page_index,
        heading=chunk.heading,
    )


if __name__ == "__main__":
    raise SystemExit(main())
