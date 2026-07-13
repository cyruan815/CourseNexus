from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.errors import CourseNexusError


Runner = Callable[..., subprocess.CompletedProcess[str]]


class MarkmapLibPreprocessor:
    def __init__(
        self,
        *,
        node_command: str = "node",
        script_path: Path | None = None,
        timeout_seconds: float = 15,
        runner: Runner = subprocess.run,
    ) -> None:
        self.node_command = node_command
        self.script_path = script_path or Path(__file__).resolve().parents[3] / "scripts" / "markmap-transform.mjs"
        self.timeout_seconds = timeout_seconds
        self.runner = runner

    def transform(self, markdown: str) -> dict[str, object]:
        try:
            completed = self.runner(
                [self.node_command, str(self.script_path)],
                input=markdown,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                encoding="utf-8",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise self._error() from exc
        if completed.returncode != 0:
            raise self._error()
        try:
            result: Any = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise self._error() from exc
        if not isinstance(result, dict) or not isinstance(result.get("root"), dict):
            raise self._error()
        if not isinstance(result.get("features"), dict):
            raise self._error()
        assets = result.get("assets")
        if not isinstance(assets, dict) or not isinstance(assets.get("styles"), list) or not isinstance(assets.get("scripts"), list):
            raise self._error()
        return result

    @staticmethod
    def _error() -> CourseNexusError:
        return CourseNexusError(
            code="GENERATION_SCHEMA_INVALID",
            message="Markmap preprocessing failed",
            status_code=502,
        )
