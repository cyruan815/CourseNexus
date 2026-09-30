from __future__ import annotations

from io import BytesIO

import pytest
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.base import RagScopeFilter, RetrievalHit
from app.integrations.rag.fake import FakeRagIndex
from app.modules.material_context.schemas import MaterialScope
from app.modules.material_context.service import retrieve_relevant_context
from app.modules.materials.service import parse_material, upload_file_material


def test_relevant_context_preserves_hit_order_scope_and_score(db: Session, context_seed) -> None:
    first_chunk, second_chunk = context_seed.math_chunks

    class OrderedRagIndex:
        def __init__(self) -> None:
            self.seen_scope: RagScopeFilter | None = None

        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            self.seen_scope = scope
            return [
                RetrievalHit(chunk_id=second_chunk.id, score=0.9),
                RetrievalHit(chunk_id=first_chunk.id, score=0.7),
            ]

    rag_index = OrderedRagIndex()

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="eigenvalue",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.math_material.id],
        ),
        rag_index=rag_index,
        top_k=8,
    )

    assert [chunk.chunk_id for chunk in result.chunks] == [second_chunk.id, first_chunk.id]
    assert [chunk.score for chunk in result.chunks] == [0.9, 0.7]
    assert [chunk.chunk_index for chunk in result.chunks] == [1, 0]
    assert rag_index.seen_scope == RagScopeFilter(
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_ids=(context_seed.math_material.id,),
        chunk_ids=(first_chunk.id, second_chunk.id),
    )


def test_relevant_context_uses_selected_material_ids(db: Session, context_seed) -> None:
    class RecordingRagIndex(FakeRagIndex):
        def __init__(self) -> None:
            super().__init__()
            self.seen_scope: RagScopeFilter | None = None

        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            self.seen_scope = scope
            return super().retrieve(query=query, scope=scope, top_k=top_k)

    rag_index = RecordingRagIndex.from_chunks(context_seed.rag_index.records.values())

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="eigenvalue",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.math_material.id, context_seed.folder_material.id],
        ),
        rag_index=rag_index,
        top_k=8,
    )

    assert {chunk.material_id for chunk in result.chunks} == {
        context_seed.math_material.id,
        context_seed.folder_material.id,
    }
    assert rag_index.seen_scope is not None
    assert rag_index.seen_scope.user_id == context_seed.user.id
    assert rag_index.seen_scope.course_id == context_seed.course.id
    assert set(rag_index.seen_scope.material_ids) == {
        context_seed.math_material.id,
        context_seed.folder_material.id,
    }


def test_relevant_context_rejects_cross_user_material_id(db: Session, tmp_path, context_seed) -> None:
    other_rag_index = FakeRagIndex()
    other_material = upload_file_material(
        db,
        user_id=context_seed.other_user.id,
        course_id=context_seed.other_course.id,
        filename="bob.txt",
        stream=BytesIO(b"bob eigenvalue"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
    )
    parse_material(
        db,
        user_id=context_seed.other_user.id,
        material_id=other_material.id,
        parser=PlainTextParser(),
        rag_index=other_rag_index,
        storage_root=tmp_path,
    )

    with pytest.raises(CourseNexusError) as exc_info:
        retrieve_relevant_context(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            query="eigenvalue",
            material_scope=MaterialScope(include_all_parsed_materials=False, material_ids=[other_material.id]),
            rag_index=context_seed.rag_index,
            top_k=4,
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_relevant_context_returns_empty_result_when_no_hits(db: Session, context_seed) -> None:
    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="unmatched",
        material_scope=MaterialScope(),
        rag_index=context_seed.rag_index,
        top_k=4,
    )

    assert result.chunks == []
    assert result.no_parsed_material is False


def test_relevant_context_ignores_stale_vector_chunk_ids(db: Session, context_seed) -> None:
    valid_chunk = context_seed.history_chunks[0]

    class StaleRagIndex:
        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            return [
                RetrievalHit(chunk_id="chk_stale", score=1.0),
                RetrievalHit(chunk_id=valid_chunk.id, score=0.6),
            ]

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="source",
        material_scope=MaterialScope(),
        rag_index=StaleRagIndex(),
        top_k=4,
    )

    assert [chunk.chunk_id for chunk in result.chunks] == [valid_chunk.id]
    assert result.chunks[0].score == 0.6


def test_relevant_context_filters_hits_against_sql_scope_after_reload(db: Session, context_seed) -> None:
    out_of_scope_chunk = context_seed.history_chunks[0]

    class StaleMetadataRagIndex:
        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            return [RetrievalHit(chunk_id=out_of_scope_chunk.id, score=0.9)]

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="source",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.math_material.id],
        ),
        rag_index=StaleMetadataRagIndex(),
        top_k=4,
    )

    assert result.chunks == []
    assert result.no_parsed_material is False


def test_relevant_context_does_not_call_rag_when_scope_has_no_chunks(db: Session, context_seed) -> None:
    class FailingRagIndex:
        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            raise AssertionError("RAG retrieval should not run without available chunks")

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="anything",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.empty_material.id],
        ),
        rag_index=FailingRagIndex(),
        top_k=4,
    )

    assert result.chunks == []
    assert result.no_parsed_material is True


def test_relevant_context_treats_selected_unparsed_material_as_no_parsed(
    db: Session,
    tmp_path,
    context_seed,
) -> None:
    uploaded_material = upload_file_material(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        filename="uploaded.txt",
        stream=BytesIO(b"not parsed yet"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
    )

    class FailingRagIndex:
        def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
            raise AssertionError("RAG retrieval should not run without parsed chunks")

    result = retrieve_relevant_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        query="anything",
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[uploaded_material.id],
        ),
        rag_index=FailingRagIndex(),
        top_k=4,
    )

    assert result.chunks == []
    assert result.no_parsed_material is True
