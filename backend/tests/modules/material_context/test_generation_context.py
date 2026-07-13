from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.material_context.schemas import MaterialScope
from app.modules.material_context.service import resolve_generation_context


def test_generation_context_contains_all_selected_materials_in_stable_order(
    db: Session,
    context_seed,
) -> None:
    selected_ids = [context_seed.history_material.id, context_seed.math_material.id]

    context = resolve_generation_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=selected_ids,
        ),
        max_tokens=10_000,
    )

    assert context is not None
    assert context.material_ids == sorted(selected_ids)
    assert [(chunk.material_id, chunk.chunk_index) for chunk in context.chunks] == sorted(
        (chunk.material_id, chunk.chunk_index) for chunk in context.chunks
    )
    assert f"===== Material: {context_seed.history_material.name} =====" in context.text
    assert f"===== Material: {context_seed.math_material.name} =====" in context.text
    assert context.estimated_tokens > 0


def test_generation_context_preserves_heading_boundaries(db: Session, context_seed) -> None:
    context = resolve_generation_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.math_material.id],
        ),
        max_tokens=10_000,
    )

    assert context is not None
    for chunk in context.chunks:
        if chunk.heading:
            assert f"Heading: {chunk.heading}" in context.text


def test_generation_context_returns_none_for_empty_selection(db: Session, context_seed) -> None:
    context = resolve_generation_context(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_scope=MaterialScope(include_all_parsed_materials=False, material_ids=[]),
        max_tokens=10_000,
    )

    assert context is None


def test_generation_context_rejects_total_context_over_limit(db: Session, context_seed) -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        resolve_generation_context(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(include_all_parsed_materials=True),
            max_tokens=1,
        )

    assert exc_info.value.code == "MATERIAL_CONTEXT_TOO_LARGE"
    assert exc_info.value.status_code == 400


def test_generation_context_counts_chinese_tokens_before_model_call(db: Session, context_seed) -> None:
    context_seed.math_chunks[0].content_text = "进程是正在执行的程序实例。" * 1000
    db.add(context_seed.math_chunks[0])
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        resolve_generation_context(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[context_seed.math_material.id],
            ),
            max_tokens=4_000,
        )

    assert exc_info.value.code == "MATERIAL_CONTEXT_TOO_LARGE"


def test_generation_context_rejects_explicit_unparsed_material_in_mixed_scope(
    db: Session,
    context_seed,
) -> None:
    context_seed.empty_material.parse_status = "uploaded"
    db.add(context_seed.empty_material)
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        resolve_generation_context(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[context_seed.math_material.id, context_seed.empty_material.id],
            ),
            max_tokens=10_000,
        )

    assert exc_info.value.code == "NOT_FOUND"
    assert exc_info.value.status_code == 404
