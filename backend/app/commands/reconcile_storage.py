from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Literal, Sequence

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.logging import configure_logging, get_logger
from app.core.paths import assert_no_legacy_data_conflicts
from app.db.session import SessionLocal
from app.integrations.rag.base import RagIndexRecord
from app.integrations.rag.llama_index_chroma import open_existing_chroma_rag_index
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialParseVersion


logger = get_logger("command.reconcile_storage")
IssueSeverity = Literal["notice", "warning"]


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    severity: IssueSeverity
    resource_type: str
    resource_id: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationReport:
    schema_version: int
    status: Literal["clean", "notices", "inconsistent"]
    issue_count: int
    inconsistency_count: int
    checked_counts: dict[str, int]
    issues: tuple[ReconciliationIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "issue_count": self.issue_count,
            "inconsistency_count": self.inconsistency_count,
            "checked_counts": dict(self.checked_counts),
            "issues": [asdict(issue) for issue in self.issues],
        }


def reconcile_storage(
    *,
    db: Session,
    storage_root: str | Path,
    rag_records: Sequence[RagIndexRecord],
    now: datetime | None = None,
    building_stale_after: timedelta = timedelta(hours=1),
) -> ReconciliationReport:
    effective_now = _as_utc(now or datetime.now(timezone.utc))
    materials = list(db.scalars(select(CourseMaterial).order_by(CourseMaterial.id)))
    versions = list(db.scalars(select(MaterialParseVersion).order_by(MaterialParseVersion.id)))
    chunks = list(db.scalars(select(MaterialChunk).order_by(MaterialChunk.id)))
    material_by_id = {material.id: material for material in materials}
    version_by_id = {version.id: version for version in versions}
    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    issues: list[ReconciliationIssue] = []

    _check_material_files(
        issues=issues,
        storage_root=Path(storage_root),
        materials=materials,
    )
    _check_parse_versions(
        issues=issues,
        materials=materials,
        versions=versions,
        version_by_id=version_by_id,
        now=effective_now,
        building_stale_after=building_stale_after,
    )
    _check_vectors(
        issues=issues,
        materials=materials,
        chunks=chunks,
        material_by_id=material_by_id,
        chunk_by_id=chunk_by_id,
        rag_records=rag_records,
    )

    ordered_issues = tuple(
        sorted(
            issues,
            key=lambda issue: (issue.severity, issue.code, issue.resource_type, issue.resource_id),
        )
    )
    inconsistency_count = sum(issue.severity == "warning" for issue in ordered_issues)
    status: Literal["clean", "notices", "inconsistent"]
    if inconsistency_count:
        status = "inconsistent"
    elif ordered_issues:
        status = "notices"
    else:
        status = "clean"
    return ReconciliationReport(
        schema_version=1,
        status=status,
        issue_count=len(ordered_issues),
        inconsistency_count=inconsistency_count,
        checked_counts={
            "materials": len(materials),
            "parse_versions": len(versions),
            "chunks": len(chunks),
            "vectors": len(rag_records),
        },
        issues=ordered_issues,
    )


def render_human_report(report: ReconciliationReport) -> str:
    counts = report.checked_counts
    lines = [
        f"Storage reconciliation: {report.status}",
        (
            "Checked "
            f"materials={counts['materials']} parse_versions={counts['parse_versions']} "
            f"chunks={counts['chunks']} vectors={counts['vectors']}"
        ),
        f"Issues={report.issue_count} inconsistencies={report.inconsistency_count}",
    ]
    for issue in report.issues:
        details = " ".join(
            f"{key}={_human_value(value)}" for key, value in sorted(issue.details.items())
        )
        suffix = f" {details}" if details else ""
        lines.append(
            f"- [{issue.severity}] {issue.code} "
            f"{issue.resource_type}={issue.resource_id}{suffix}"
        )
    return "\n".join(lines)


def report_exit_code(report: ReconciliationReport) -> int:
    return 1 if report.inconsistency_count else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only reconciliation for CourseNexus SQLite, uploaded files, and Chroma."
    )
    parser.add_argument("--json", action="store_true", help="Emit the stable JSON report schema.")
    parser.add_argument(
        "--building-stale-minutes",
        type=_non_negative_int,
        default=60,
        help="Mark building parse versions older than this threshold as stale (default: 60).",
    )
    args = parser.parse_args(argv)

    try:
        settings = get_settings()
        assert_no_legacy_data_conflicts(
            database_url=settings.database_url,
            file_storage_path=settings.file_storage_path,
            chroma_persist_path=settings.chroma_persist_path,
        )
        configure_logging(settings)
        _assert_configured_database_exists(settings.database_url)
        rag_index = open_existing_chroma_rag_index(
            persist_path=settings.chroma_persist_path,
            collection_name=settings.chroma_collection,
        )
        rag_records = [] if rag_index is None else rag_index.list_records()
        with SessionLocal() as db:
            report = reconcile_storage(
                db=db,
                storage_root=settings.file_storage_path,
                rag_records=rag_records,
                building_stale_after=timedelta(minutes=args.building_stale_minutes),
            )
    except Exception as exc:
        _render_command_error(exc, json_output=args.json)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    else:
        print(render_human_report(report))
    return report_exit_code(report)


def _check_material_files(
    *,
    issues: list[ReconciliationIssue],
    storage_root: Path,
    materials: list[CourseMaterial],
) -> None:
    root = storage_root.resolve()
    material_keys = {(item.user_id, item.course_id, item.id) for item in materials}
    for material in materials:
        if (
            material.source_type != "file"
            or material.deleted_at is not None
            or material.parse_status == "deleted"
        ):
            continue
        file_path = _safe_stored_file_path(root, material.file_url)
        if file_path is None or not file_path.is_file():
            issues.append(
                ReconciliationIssue(
                    code="MATERIAL_FILE_MISSING",
                    severity="warning",
                    resource_type="material",
                    resource_id=material.id,
                    details={"course_id": material.course_id, "user_id": material.user_id},
                )
            )

    if not root.is_dir():
        return
    for user_dir in _child_directories(root, excluded_names={".trash"}):
        for course_dir in _child_directories(user_dir):
            for material_dir in _child_directories(course_dir):
                key = (user_dir.name, course_dir.name, material_dir.name)
                if key not in material_keys:
                    issues.append(
                        ReconciliationIssue(
                            code="ORPHAN_MATERIAL_DIRECTORY",
                            severity="warning",
                            resource_type="material_directory",
                            resource_id="/".join(key),
                        )
                    )


def _check_parse_versions(
    *,
    issues: list[ReconciliationIssue],
    materials: list[CourseMaterial],
    versions: list[MaterialParseVersion],
    version_by_id: dict[str, MaterialParseVersion],
    now: datetime,
    building_stale_after: timedelta,
) -> None:
    active_versions_by_material: dict[str, list[MaterialParseVersion]] = defaultdict(list)
    for version in versions:
        if version.status == "active":
            active_versions_by_material[version.material_id].append(version)
        elif version.status in {"failed", "retired"}:
            issues.append(
                ReconciliationIssue(
                    code="PARSE_VERSION_RETAINED",
                    severity="notice",
                    resource_type="parse_version",
                    resource_id=version.id,
                    details={"material_id": version.material_id, "status": version.status},
                )
            )
        elif version.status == "building":
            created_at = _as_utc(version.created_at)
            stale = now - created_at > building_stale_after
            issues.append(
                ReconciliationIssue(
                    code=("PARSE_VERSION_BUILDING_STALE" if stale else "PARSE_VERSION_BUILDING"),
                    severity=("warning" if stale else "notice"),
                    resource_type="parse_version",
                    resource_id=version.id,
                    details={"material_id": version.material_id},
                )
            )

    for material in materials:
        active_versions = active_versions_by_material.get(material.id, [])
        if len(active_versions) > 1:
            issues.append(
                ReconciliationIssue(
                    code="MULTIPLE_ACTIVE_PARSE_VERSIONS",
                    severity="warning",
                    resource_type="material",
                    resource_id=material.id,
                    details={"active_version_count": len(active_versions)},
                )
            )
        pointer = material.active_parse_version_id
        if pointer is None:
            if active_versions:
                issues.append(
                    ReconciliationIssue(
                        code="ACTIVE_PARSE_VERSION_POINTER_INVALID",
                        severity="warning",
                        resource_type="material",
                        resource_id=material.id,
                        details={"reason": "missing_pointer"},
                    )
                )
            continue
        pointed_version = version_by_id.get(pointer)
        if (
            pointed_version is None
            or pointed_version.material_id != material.id
            or pointed_version.course_id != material.course_id
            or pointed_version.user_id != material.user_id
            or pointed_version.status != "active"
        ):
            issues.append(
                ReconciliationIssue(
                    code="ACTIVE_PARSE_VERSION_POINTER_INVALID",
                    severity="warning",
                    resource_type="material",
                    resource_id=material.id,
                    details={"reason": "missing_or_non_active_target", "version_id": pointer},
                )
            )


def _check_vectors(
    *,
    issues: list[ReconciliationIssue],
    materials: list[CourseMaterial],
    chunks: list[MaterialChunk],
    material_by_id: dict[str, CourseMaterial],
    chunk_by_id: dict[str, MaterialChunk],
    rag_records: Sequence[RagIndexRecord],
) -> None:
    records_by_active_scope: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in rag_records:
        if not all((record.user_id, record.course_id, record.material_id, record.parse_version_id)):
            issues.append(
                ReconciliationIssue(
                    code="VECTOR_METADATA_INVALID",
                    severity="warning",
                    resource_type="vector",
                    resource_id=record.chunk_id,
                )
            )
        db_chunk = chunk_by_id.get(record.chunk_id)
        if db_chunk is None:
            issues.append(
                ReconciliationIssue(
                    code="ORPHAN_VECTOR",
                    severity="warning",
                    resource_type="vector",
                    resource_id=record.chunk_id,
                    details={
                        "material_id": record.material_id,
                        "version_id": record.parse_version_id,
                    },
                )
            )
        else:
            material = material_by_id.get(db_chunk.material_id)
            expected_metadata = (
                material is not None
                and record.user_id == material.user_id
                and record.course_id == material.course_id
                and record.material_id == db_chunk.material_id
                and record.parse_version_id == db_chunk.parse_version_id
            )
            if not expected_metadata:
                issues.append(
                    ReconciliationIssue(
                        code="VECTOR_METADATA_MISMATCH",
                        severity="warning",
                        resource_type="vector",
                        resource_id=record.chunk_id,
                    )
                )
            if material is not None and (
                material.deleted_at is not None or material.parse_status == "deleted"
            ):
                issues.append(
                    ReconciliationIssue(
                        code="VECTOR_FOR_DELETED_MATERIAL",
                        severity="warning",
                        resource_type="vector",
                        resource_id=record.chunk_id,
                        details={"material_id": material.id},
                    )
                )
        if record.material_id and record.parse_version_id:
            records_by_active_scope[(record.material_id, record.parse_version_id)].add(record.chunk_id)

    chunks_by_version: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        chunks_by_version[chunk.parse_version_id].add(chunk.id)
    for material in materials:
        version_id = material.active_parse_version_id
        if version_id is None or material.deleted_at is not None or material.parse_status == "deleted":
            continue
        expected = chunks_by_version.get(version_id, set())
        actual = records_by_active_scope.get((material.id, version_id), set())
        if expected != actual:
            issues.append(
                ReconciliationIssue(
                    code="ACTIVE_VECTOR_SET_MISMATCH",
                    severity="warning",
                    resource_type="parse_version",
                    resource_id=version_id,
                    details={
                        "material_id": material.id,
                        "db_chunk_count": len(expected),
                        "vector_count": len(actual),
                        "missing_vector_count": len(expected - actual),
                        "extra_vector_count": len(actual - expected),
                    },
                )
            )


def _safe_stored_file_path(root: Path, file_url: str | None) -> Path | None:
    if not file_url:
        return None
    candidate = (root / file_url).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _child_directories(path: Path, *, excluded_names: set[str] | None = None) -> list[Path]:
    excluded = excluded_names or set()
    try:
        return sorted(
            (item for item in path.iterdir() if item.is_dir() and item.name not in excluded),
            key=lambda item: item.name,
        )
    except OSError as exc:
        raise CourseNexusError(
            code="STORAGE_RECONCILIATION_FAILED",
            message="文件存储对账读取失败",
            status_code=500,
        ) from exc


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _human_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).replace("\n", " ")


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _assert_configured_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return
    if not Path(url.database).is_file():
        raise CourseNexusError(
            code="DATABASE_NOT_FOUND",
            message="SQLite 数据库不存在，请先完成初始化或迁移",
            status_code=500,
        )


def _render_command_error(exc: Exception, *, json_output: bool) -> None:
    code = exc.code if isinstance(exc, CourseNexusError) else "STORAGE_RECONCILIATION_FAILED"
    if json_output:
        print(
            json.dumps(
                {"schema_version": 1, "status": "error", "error_code": code},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
    else:
        print(f"Storage reconciliation failed: {code}", file=sys.stderr)
    cause = exc.__cause__ or exc
    logger.error(
        "跨存储对账失败 | code=%s",
        code,
        exc_info=(type(cause), cause, cause.__traceback__),
    )


if __name__ == "__main__":
    raise SystemExit(main())
