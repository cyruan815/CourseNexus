from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
import app.db.models  # noqa: F401
from app.db.session import SessionLocal
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.users.models import User


DEFAULT_USERNAME = "demo@example.com"
DEFAULT_PASSWORD = "password123"

DEMO_USER_ID = "usr_demo_generated_content"
DEMO_COURSE_ID = "crs_demo_generated_content"
DEMO_MATERIAL_ID = "mat_demo_generated_content"
DEMO_CHUNK_ID = "chk_demo_generated_content"
DEMO_CONTENT_ID = "gen_demo_outline"
DEMO_CITATION_ID = "cit_demo_outline_1"


@dataclass(frozen=True)
class SeedGeneratedContentDemoResult:
    username: str
    password: str
    user_id: str
    course_id: str
    material_id: str
    chunk_id: str
    generated_content_id: str


def seed_demo_generated_content(
    *,
    db: Session,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
) -> SeedGeneratedContentDemoResult:
    user = _upsert_user(db, username=username, password=password)
    course = _upsert_course(db, user_id=user.id)
    material = _upsert_material(db, user_id=user.id, course_id=course.id)
    chunk = _upsert_chunk(db, course_id=course.id, material_id=material.id)
    content = _upsert_generated_content(db, user_id=user.id, course_id=course.id)
    _upsert_citation(db, content_id=content.id, material=material, chunk=chunk)
    db.commit()

    return SeedGeneratedContentDemoResult(
        username=username,
        password=password,
        user_id=user.id,
        course_id=course.id,
        material_id=material.id,
        chunk_id=chunk.id,
        generated_content_id=content.id,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed a local CourseNexus demo user, course, and generated content detail record.",
    )
    parser.add_argument("--username", default=DEFAULT_USERNAME, help=f"Demo login username. Default: {DEFAULT_USERNAME}")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help=f"Demo login password. Default: {DEFAULT_PASSWORD}")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        result = seed_demo_generated_content(db=db, username=args.username, password=args.password)

    print("Seeded generated content demo data:")
    print(f"  login: {result.username} / {result.password}")
    print(f"  course_id: {result.course_id}")
    print(f"  generated_content_id: {result.generated_content_id}")
    print(f"  frontend path: /generated-contents/{result.generated_content_id}")
    return 0


def _upsert_user(db: Session, *, username: str, password: str) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        user = User(
            id=DEMO_USER_ID,
            username=username,
            password_hash=hash_password(password),
            nickname="生成内容演示用户",
            status="active",
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.nickname = user.nickname or "生成内容演示用户"
        user.status = "active"
        user.deleted_at = None
    db.flush()
    return user


def _upsert_course(db: Session, *, user_id: str) -> Course:
    course = db.get(Course, DEMO_COURSE_ID)
    if course is None:
        course = Course(
            id=DEMO_COURSE_ID,
            user_id=user_id,
            name="生成内容详情演示课",
            description="本地开发态 seed 数据，用于手动查看生成内容详情页。",
            teacher="CourseNexus",
            term="2025-2026-spring",
            status="active",
        )
        db.add(course)
    else:
        course.user_id = user_id
        course.name = "生成内容详情演示课"
        course.description = "本地开发态 seed 数据，用于手动查看生成内容详情页。"
        course.teacher = "CourseNexus"
        course.term = "2025-2026-spring"
        course.status = "active"
        course.deleted_at = None
    db.flush()
    return course


def _upsert_material(db: Session, *, user_id: str, course_id: str) -> CourseMaterial:
    material = db.get(CourseMaterial, DEMO_MATERIAL_ID)
    if material is None:
        material = CourseMaterial(
            id=DEMO_MATERIAL_ID,
            user_id=user_id,
            course_id=course_id,
            name="演示资料.md",
            material_type="markdown",
            source_type="file",
            file_url="dev-seed/generated-content-demo/source.md",
            parse_status="parsed",
            page_count=1,
        )
        db.add(material)
    else:
        material.user_id = user_id
        material.course_id = course_id
        material.name = "演示资料.md"
        material.material_type = "markdown"
        material.source_type = "file"
        material.file_url = "dev-seed/generated-content-demo/source.md"
        material.parse_status = "parsed"
        material.parse_error = None
        material.page_count = 1
        material.deleted_at = None
    db.flush()
    return material


def _upsert_chunk(db: Session, *, course_id: str, material_id: str) -> MaterialChunk:
    chunk = db.get(MaterialChunk, DEMO_CHUNK_ID)
    if chunk is None:
        chunk = MaterialChunk(
            id=DEMO_CHUNK_ID,
            material_id=material_id,
            course_id=course_id,
            chunk_index=0,
            page=None,
            page_index=0,
            heading="函数与极限",
            content_text="极限定义用于描述函数在某一点附近的变化趋势。",
            embedding_id=None,
        )
        db.add(chunk)
    else:
        chunk.material_id = material_id
        chunk.course_id = course_id
        chunk.chunk_index = 0
        chunk.page = None
        chunk.page_index = 0
        chunk.heading = "函数与极限"
        chunk.content_text = "极限定义用于描述函数在某一点附近的变化趋势。"
        chunk.embedding_id = None
    db.flush()
    return chunk


def _upsert_generated_content(db: Session, *, user_id: str, course_id: str) -> AIGeneratedContent:
    content_json = {
        "sections": [
            {
                "id": "sec_demo_limit",
                "title": "函数与极限",
                "summary": "梳理极限定义、左右极限和常见极限计算方法。",
                "review_suggestion": "先复盘定义，再用典型题检查运算熟练度。",
                "source_citation_ids": [DEMO_CITATION_ID],
                "sort_order": 1,
            }
        ]
    }
    content = db.get(AIGeneratedContent, DEMO_CONTENT_ID)
    if content is None:
        content = AIGeneratedContent(
            id=DEMO_CONTENT_ID,
            user_id=user_id,
            course_id=course_id,
            content_type="outline",
            title="生成内容详情演示提纲",
            content="函数与极限复习提纲",
            content_json=content_json,
            generation_status="success",
            material_scope_json={"include_all_parsed_materials": True, "material_ids": []},
            error_code=None,
        )
        db.add(content)
    else:
        content.user_id = user_id
        content.course_id = course_id
        content.content_type = "outline"
        content.title = "生成内容详情演示提纲"
        content.content = "函数与极限复习提纲"
        content.content_json = content_json
        content.generation_status = "success"
        content.material_scope_json = {"include_all_parsed_materials": True, "material_ids": []}
        content.error_code = None
        content.deleted_at = None
    db.flush()
    return content


def _upsert_citation(
    db: Session,
    *,
    content_id: str,
    material: CourseMaterial,
    chunk: MaterialChunk,
) -> SourceCitation:
    citation = db.get(SourceCitation, DEMO_CITATION_ID)
    if citation is None:
        citation = SourceCitation(
            id=DEMO_CITATION_ID,
            generated_content_id=content_id,
            material_id=material.id,
            chunk_id=chunk.id,
            material_name=material.name,
            page=None,
            page_index=0,
            hit_text="极限定义用于描述函数在某一点附近的变化趋势。",
            sort_order=1,
        )
        db.add(citation)
    else:
        citation.message_id = None
        citation.generated_content_id = content_id
        citation.material_id = material.id
        citation.chunk_id = chunk.id
        citation.material_name = material.name
        citation.page = None
        citation.page_index = 0
        citation.hit_text = "极限定义用于描述函数在某一点附近的变化趋势。"
        citation.sort_order = 1
    db.flush()
    return citation


if __name__ == "__main__":
    raise SystemExit(main())
