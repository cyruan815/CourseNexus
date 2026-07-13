from __future__ import annotations

from subprocess import CompletedProcess, TimeoutExpired

import pytest

from app.core.errors import CourseNexusError
from app.integrations.markmap.preprocessor import MarkmapLibPreprocessor


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
    result = MarkmapLibPreprocessor().transform("- Root\n  - Child")
    assert result["root"]["content"] == "Root"
    assert result["root"]["children"][0]["content"] == "Child"
    assert result["assets"] == {"styles": [], "scripts": []}
