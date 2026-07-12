from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.course_qa.models import SourceCitation


def detach_material_references(db: Session, material_ids: list[str]) -> None:
    if not material_ids:
        return
    db.execute(
        update(SourceCitation)
        .where(SourceCitation.material_id.in_(material_ids))
        .values(material_id=None, chunk_id=None)
    )
