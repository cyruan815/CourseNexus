from __future__ import annotations

from app.integrations.rag.base import RagChunk, RagScopeFilter
from app.integrations.rag.fake import FakeRagIndex


def rag_chunk(
    chunk_id: str,
    *,
    user_id: str = "u1",
    course_id: str = "math",
    material_id: str = "m1",
    folder_id: str | None = None,
    chunk_index: int = 0,
    text: str = "matrix eigenvalue",
    parse_version_id: str = "mpv_1",
) -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        folder_id=folder_id,
        chunk_index=chunk_index,
        text=text,
        page="1",
        page_index=0,
        heading="A",
        parse_version_id=parse_version_id,
    )


def test_fake_rag_index_filters_and_ranks() -> None:
    index = FakeRagIndex()
    index.index_chunks(
        [
            rag_chunk("c1", text="matrix eigenvalue"),
            rag_chunk("c2", course_id="history", material_id="m2", text="matrix eigenvalue"),
        ]
    )

    hits = index.retrieve(
        query="eigenvalue",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c1"]


def test_fake_rag_index_ranks_by_token_overlap() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", text="matrix", material_id="m1"),
            rag_chunk("c2", text="matrix eigenvalue diagonalization", material_id="m1"),
        ]
    )

    hits = index.retrieve(
        query="matrix eigenvalue",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c2", "c1"]
    assert hits[0].score > hits[1].score


def test_fake_rag_index_breaks_equal_scores_by_chunk_index() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", chunk_index=2, text="matrix", material_id="m1"),
            rag_chunk("c2", chunk_index=1, text="matrix", material_id="m1"),
        ]
    )

    hits = index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c2", "c1"]
    assert hits[0].score == hits[1].score


def test_fake_rag_index_applies_selected_material_filter() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", material_id="m1"),
            rag_chunk("c2", material_id="m2"),
        ]
    )

    hits = index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math", material_ids=("m2",)),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c2"]


def test_fake_rag_index_isolates_users() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", user_id="u1"),
            rag_chunk("c2", user_id="u2"),
        ]
    )

    hits = index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c1"]


def test_fake_rag_index_delete_material_removes_records() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", material_id="m1"),
            rag_chunk("c2", material_id="m2"),
        ]
    )

    index.delete_material("m1")

    assert set(index.records) == {"c2"}


def test_fake_rag_index_delete_materials_removes_all_requested_records() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", material_id="m1"),
            rag_chunk("c2", material_id="m2"),
            rag_chunk("c3", material_id="m3"),
        ]
    )

    index.delete_materials(["m1", "m2"])

    assert set(index.records) == {"c3"}


def test_fake_rag_index_deletes_and_lists_one_parse_version() -> None:
    index = FakeRagIndex.from_chunks(
        [
            rag_chunk("c1", material_id="m1", parse_version_id="mpv_1"),
            rag_chunk("c2", material_id="m1", parse_version_id="mpv_2"),
        ]
    )

    assert index.list_parse_version_chunk_ids("mpv_1") == {"c1"}

    index.delete_parse_version("mpv_1")

    assert set(index.records) == {"c2"}
