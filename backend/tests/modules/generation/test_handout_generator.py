from __future__ import annotations

from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.handout.generator import HandoutGenerator
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch, MaterialContextResult


def _context() -> MaterialContextResult:
    return MaterialContextResult(
        no_parsed_material=False,
        chunks=[
            ContextChunk(
                material_id="mat_1",
                chunk_id="chunk_1",
                chunk_index=0,
                material_name="数据库讲义.pdf",
                page="1",
                page_index=0,
                heading="关系模型",
                content_text="关系模型由关系、属性、元组和约束组成。",
            )
        ],
    )


def _batch() -> MaterialContextBatch:
    context = _context()
    return MaterialContextBatch(chunks=context.chunks, material_ids=["mat_1"], estimated_tokens=10)


class PromptCapturingTextProvider(MockModelProvider):
    def __init__(self, text: str) -> None:
        super().__init__(text_outputs=[text])
        self.prompts: list[str] = []

    def generate_text(self, *, prompt: str) -> str:
        self.prompts.append(prompt)
        return super().generate_text(prompt=prompt)


def test_handout_generator_returns_markdown_content_without_structured_json_or_citations() -> None:
    markdown = "# 主键讲义\n\n## 概览\n\n主键用于唯一标识表中的一行。"
    provider = PromptCapturingTextProvider(markdown)

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"language": "zh-CN", "detail_level": "standard", "handout_title": "主键讲义", "source_note": "本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。"},
    )

    assert output.title == "主键讲义"
    assert output.content == "# 主键讲义\n\n本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。\n\n## 概览\n\n主键用于唯一标识表中的一行。"
    assert output.content_json == {"format": "markdown", "schema_version": 1}
    assert output.item_citation_chunk_ids == {}


def test_handout_generator_prompt_requests_complete_markdown_not_json_or_html() -> None:
    provider = PromptCapturingTextProvider("# 物理层概念讲义\n\n正文")

    HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={
            "language": "zh-CN",
            "content_depth": "detailed",
            "example_intensity": "high",
            "assessment_intensity": "high",
            "review_intensity": "standard",
            "course_name": "计算机网络",
            "task_title": "物理层核心概念",
            "subtask_title": "物理层概念与通信基础",
            "subtask_type": "learn",
            "subtask_description": "理解物理层基本概念和通信模型。",
            "estimated_minutes": 45,
            "plan_goal": "两天内深度学习计算机网络物理层。",
            "diagnostic_foundation_needed": True,
            "diagnostic_weak_area": "calculation",
            "diagnostic_weak_topics": ["Nyquist / Shannon 公式"],
            "diagnostic_note": "希望多讲公式怎么用。",
            "teaching_strategy_hint": "加强公式变量、单位、适用条件、代入步骤和计算例题。",
            "handout_title": "物理层概念与通信基础讲义",
            "source_note": "本讲义基于《计算机网络.pdf》中“物理层概念与通信基础”相关内容生成。",
        },
    )

    prompt = provider.prompts[0]
    assert "课程名称：计算机网络" in prompt
    assert "当前二级任务标题：物理层概念与通信基础" in prompt
    assert "预计学习时间：45 分钟" in prompt
    assert "诊断薄弱方向：calculation" in prompt
    assert "请直接输出一份完整 Markdown 讲义" in prompt
    assert "讲义标题必须是：物理层概念与通信基础讲义" in prompt
    assert "一级标题下一段必须原样写入来源说明：本讲义基于《计算机网络.pdf》中“物理层概念与通信基础”相关内容生成。" in prompt
    assert "块级公式只使用独立的 $$...$$" in prompt
    assert "禁止使用 \\(...\\) 和 \\[...\\]" in prompt
    assert "禁止用单独一行的 [ 和 ] 包裹公式" in prompt
    assert "支持的 callout 类型只有 NOTE、EXAMPLE、SUMMARY、WARNING、TIP" in prompt
    assert "> [!NOTE] 注意" in prompt
    assert "> [!EXAMPLE] 例题" in prompt
    assert "> [!SUMMARY] 核心结论" in prompt
    assert "> [!WARNING] 易错点" in prompt
    assert "> [!TIP] 解题提示" in prompt
    assert "callout 正文每一行都必须继续以 > 开头" in prompt
    assert "不要把整篇正文都写成 callout" in prompt
    assert "自测题或填空题的空格线使用全角低线" in prompt
    assert "不要使用连续 ASCII 下划线 ______" in prompt
    assert "不要输出 JSON" in prompt
    assert "不要输出 HTML" in prompt
    assert "不要写 citation marker" in prompt
    assert "只输出符合 HandoutContent schema 的 JSON 对象" not in prompt
    assert "每个 section 必须填写 source_citation_ids" not in prompt


def test_handout_generator_strips_markdown_code_fence_wrappers() -> None:
    provider = PromptCapturingTextProvider("```markdown\n# 主键讲义\n\n正文\n```")

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"handout_title": "主键讲义"},
    )

    assert output.content == "# 主键讲义\n\n正文"



def test_handout_generator_preserves_markdown_math_delimiters_verbatim() -> None:
    provider = PromptCapturingTextProvider(
        "# 错误标题\n\n"
        "## 概览\n\n"
        "行内公式 $C = B \\log_2(1 + S/N)$ 保持原样。\n\n"
        "$$\nC = B \\log_2(1 + S/N)\n$$"
    )

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"handout_title": "信道容量讲义", "source_note": "本讲义基于《数据库讲义.pdf》中“信道容量”相关内容生成。"},
    )

    assert output.content == (
        "# 信道容量讲义\n\n"
        "本讲义基于《数据库讲义.pdf》中“信道容量”相关内容生成。\n\n"
        "## 概览\n\n"
        "行内公式 $C = B \\log_2(1 + S/N)$ 保持原样。\n\n"
        "$$\nC = B \\log_2(1 + S/N)\n$$"
    )


def test_handout_generator_does_not_rewrite_code_or_regular_brackets() -> None:
    markdown = (
        "# 主键讲义\n\n"
        "普通链接 [CourseNexus](https://example.com) 保持不变。\n\n"
        "行内代码 `\\[x\\]` 保持不变。\n\n"
        "```text\n"
        "[\n"
        "\\frac{S}{N}\n"
        "]\n"
        "```\n\n"
        "- [ ] 待办项保持不变。"
    )
    provider = PromptCapturingTextProvider(markdown)

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"handout_title": "主键讲义"},
    )

    assert "[CourseNexus](https://example.com)" in output.content
    assert "`\\[x\\]`" in output.content
    assert "```text\n[\n\\frac{S}{N}\n]\n```" in output.content
    assert "- [ ] 待办项保持不变。" in output.content


def test_handout_generator_replaces_model_heading_and_deduplicates_source_note() -> None:
    provider = PromptCapturingTextProvider(
        "# 模型乱写标题\n\n"
        "本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。\n\n"
        "## 概览\n\n正文"
    )

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"handout_title": "主键讲义", "source_note": "本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。"},
    )

    assert output.content == "# 主键讲义\n\n本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。\n\n## 概览\n\n正文"


def test_handout_generator_adds_heading_when_model_omits_heading() -> None:
    provider = PromptCapturingTextProvider("## 概览\n\n正文")

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"handout_title": "主键讲义", "source_note": "本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。"},
    )

    assert output.content.startswith("# 主键讲义\n\n本讲义基于《数据库讲义.pdf》中“主键”相关内容生成。\n\n## 概览")

def test_handout_generator_rejects_empty_markdown() -> None:
    provider = PromptCapturingTextProvider("   ")

    try:
        HandoutGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={},
        )
    except Exception as exc:
        assert getattr(exc, "code", None) == "GENERATION_SCHEMA_INVALID"
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("empty markdown should be rejected")
