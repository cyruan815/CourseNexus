from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired, run

import pytest

from app.core.errors import CourseNexusError
from app.integrations.markmap.preprocessor import MarkmapLibPreprocessor


def _skip_when_markmap_lib_unavailable() -> None:
    script_dir = Path(__file__).resolve().parents[2] / "scripts"
    try:
        completed = run(
            ["node", "--input-type=module", "-e", "import('markmap-lib')"],
            cwd=script_dir,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
            encoding="utf-8",
        )
    except (OSError, TimeoutExpired):
        pytest.skip("markmap-lib runtime is unavailable; run pnpm install at repo root")
    if completed.returncode != 0:
        pytest.skip("markmap-lib runtime is unavailable; run pnpm install at repo root")

def test_markmap_preprocessor_sends_markdown_to_node_and_parses_result(tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def runner(args, **kwargs):
        calls.append({"args": args, **kwargs})
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"root":{"content":"Root","children":[]},"features":{},"assets":{"styles":[],"scripts":[]}}',
            stderr="",
        )

    script = tmp_path / "transform.mjs"
    processor = MarkmapLibPreprocessor(node_command="node-test", script_path=script, runner=runner)

    result = processor.transform("- Root")

    assert result["root"]["content"] == "Root"
    assert calls[0]["args"] == ["node-test", str(script)]
    assert calls[0]["input"] == "- Root"


@pytest.mark.parametrize(
    "stdout",
    ["not json", '{"features":{},"assets":{"styles":[],"scripts":[]}}'],
)
def test_markmap_preprocessor_rejects_invalid_output(tmp_path, stdout: str) -> None:
    def runner(args, **kwargs):
        return CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    processor = MarkmapLibPreprocessor(script_path=tmp_path / "transform.mjs", runner=runner)
    with pytest.raises(CourseNexusError) as exc_info:
        processor.transform("- Root")
    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_markmap_preprocessor_maps_process_failure(tmp_path) -> None:
    def runner(args, **kwargs):
        return CompletedProcess(args=args, returncode=1, stdout="", stderr="failed")

    processor = MarkmapLibPreprocessor(script_path=tmp_path / "transform.mjs", runner=runner)
    with pytest.raises(CourseNexusError) as exc_info:
        processor.transform("- Root")
    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_markmap_preprocessor_maps_timeout(tmp_path) -> None:
    def runner(args, **kwargs):
        raise TimeoutExpired(args, 5)

    processor = MarkmapLibPreprocessor(script_path=tmp_path / "transform.mjs", runner=runner)
    with pytest.raises(CourseNexusError) as exc_info:
        processor.transform("- Root")
    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_real_markmap_lib_transform_returns_renderable_tree() -> None:
    _skip_when_markmap_lib_unavailable()
    result = MarkmapLibPreprocessor().transform("- Root\n  - Child")
    assert result["root"]["content"] == "Root"
    assert result["root"]["children"][0]["content"] == "Child"
    assert result["assets"] == {"styles": [], "scripts": []}


def test_real_markmap_lib_transform_returns_json_safe_formula_assets() -> None:
    result = MarkmapLibPreprocessor().transform("- $x^2$")

    assert result["features"] == {"katex": True}
    assert result["assets"]["styles"]
    assert result["assets"]["scripts"]
    assert all(item["type"] == "script" for item in result["assets"]["scripts"])
