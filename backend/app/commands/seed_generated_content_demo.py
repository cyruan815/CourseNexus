from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.core.security import hash_password
from app.db.session import SessionLocal
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
    *, db: Session, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD
) -> SeedGeneratedContentDemoResult:
    user = db.get(User, DEMO_USER_ID) or User(id=DEMO_USER_ID, username=username)
    user.username = username
    user.password_hash = hash_password(password)
    user.nickname = "Generated Content Demo"
    user.status = "active"
    user.deleted_at = None
    db.add(user)

    course = db.get(Course, DEMO_COURSE_ID) or Course(id=DEMO_COURSE_ID, user_id=user.id, name="Generation Demo")
    course.user_id = user.id
    course.name = "Generation Demo"
    course.description = "Local generated-content detail demo"
    course.teacher = "CourseNexus"
    course.term = "2025-2026-spring"
    course.status = "active"
    course.deleted_at = None
    db.add(course)

    material = db.get(CourseMaterial, DEMO_MATERIAL_ID) or CourseMaterial(
        id=DEMO_MATERIAL_ID, user_id=user.id, course_id=course.id, name="demo.md",
        material_type="markdown", source_type="file", file_url="dev-seed/generated-content-demo/source.md",
    )
    material.user_id = user.id
    material.course_id = course.id
    material.name = "demo.md"
    material.parse_status = "parsed"
    material.parse_error = None
    material.page_count = 1
    material.deleted_at = None
    db.add(material)

    chunk = db.get(MaterialChunk, DEMO_CHUNK_ID) or MaterialChunk(
        id=DEMO_CHUNK_ID, material_id=material.id, course_id=course.id, chunk_index=0,
        content_text="Limits describe how a function changes near a point.",
    )
    chunk.material_id = material.id
    chunk.course_id = course.id
    chunk.chunk_index = 0
    chunk.page = None
    chunk.page_index = 0
    chunk.heading = "Functions and Limits"
    chunk.content_text = "Limits describe how a function changes near a point."
    chunk.embedding_id = None
    db.add(chunk)

    content = db.get(AIGeneratedContent, DEMO_CONTENT_ID) or AIGeneratedContent(
        id=DEMO_CONTENT_ID, user_id=user.id, course_id=course.id,
        content_type="outline", title="Generated Outline Demo",
    )
    content.user_id = user.id
    content.course_id = course.id
    content.content_type = "outline"
    content.title = "Generated Outline Demo"
    content.content = None
    content.content_json = {"sections": [{
        "id": "sec_001", "title": "1. Functions and Limits",
        "summary": "Review limit definitions and common calculations.",
        "review_suggestion": "Review the definition before examples.", "sort_order": 1,
    }]}
    content.generation_status = "success"
    content.material_scope_json = {"include_all_parsed_materials": True, "material_ids": []}
    content.error_code = None
    content.deleted_at = None
    db.add(content)
    db.commit()

    return SeedGeneratedContentDemoResult(
        username=username, password=password, user_id=user.id, course_id=course.id,
        material_id=material.id, chunk_id=chunk.id, generated_content_id=content.id,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed local generated-content demo data.")
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        result = seed_demo_generated_content(db=db, username=args.username, password=args.password)
    print(f"Seeded {result.generated_content_id} for {result.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
