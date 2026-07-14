# ADR 0006: Handout PDF Rendering Pipeline

## Status

Accepted

## Context

Study Mode 的任务讲义导出需要把 `AIGeneratedContent.content` 中保存的 Markdown 产物转换为学生可阅读的 PDF。旧实现直接手写 PDF 对象流，只能输出基础文本，难以正确处理 Markdown 表格、标题层级、数学公式、分页边距和中文/英文混排。

本地 POC 仍保持 FastAPI 单体后端和同步导出接口。导出不保存历史、不调用模型、不修改原 `AIGeneratedContent`，失败时由 exports service 映射为 `EXPORT_FAILED`。

## Options

1. 保留手写 PDF 对象流，继续补充字体和换行规则。
2. 使用 `markdown-it-py` + Jinja2 生成语义化 HTML，再通过 Playwright Chromium 打印 PDF。
3. 使用 Pandoc + XeLaTeX/LuaLaTeX 直接从 Markdown 生成 PDF。
4. 使用 WeasyPrint 等纯 Python HTML/CSS PDF 引擎。

## Decision

选择方案 2，并在后端导出用临时 HTML 中接入本地 KaTeX。

任务讲义导出采用：

```text
AIGeneratedContent.content Markdown
-> markdown-it-py HTML
-> 本地 KaTeX CSS/JS auto-render
-> Playwright Chromium page.pdf()
-> PDF bytes
```

后端运行依赖 `markdown-it-py`、`jinja2` 和 `playwright`；仓库根依赖 `katex` 提供 PDF 渲染所需的本地 CSS、JS 和字体资源。`render_markdown_pdf(markdown, title=...)` 保持同步函数签名，内部生成临时 HTML、复制 KaTeX fonts 目录，然后通过 Playwright 打印为 PDF。
## Reasons

- 浏览器打印引擎天然支持 Markdown 转 HTML 后的表格、标题、列表、长文本换行和 A4 分页，比手写 PDF 对象流更适合讲义。
- Playwright 的 `page.pdf()` 能稳定控制纸张尺寸、边距、背景和 print CSS，并能执行 KaTeX auto-render，使 PDF 接近浏览器真实排版。
- 方案保持导出 API 契约不变，只替换 renderer 内部实现，风险边界集中在 `backend/app/modules/exports/renderer.py`。
- Pandoc/TeX 公式质量高但运行环境更重；WeasyPrint 集成简单但无法直接执行浏览器侧 KaTeX 自动渲染。

## Consequences

- 本地和 CI 环境若运行 handout PDF 导出或相关测试，需要在后端 Python 环境安装依赖后额外执行 `python -m playwright install chromium`；Conda / pip 安装 `playwright` 包本身不会下载浏览器二进制。
- 后端依赖声明必须包含 `markdown-it-py`、`jinja2` 和 `playwright`；根 `package.json` 必须包含 `katex`，并保持 `pnpm-lock.yaml` 同步。
- 导出层应继续清洗用户可见引用残留，不展示 `formula-not-decoded`、``、``、`` 等 parser/OCR 噪声。
- PDF 视觉质量以后应通过渲染 PNG 或人工抽检验证；文本抽取只能作为辅助检查。
- PDF HTML 必须等待 `window.__COURSE_NEXUS_MATH_READY__` 和字体加载完成；若出现 `.katex-error` 或 KaTeX runtime 错误，导出失败并由 service 映射为 `EXPORT_FAILED`。若后续替换为前端打印页或其他 PDF 引擎，必须更新本 ADR 和 `docs/domains/study-mode/task-content.md`。

## 2026-07-15 Update: Markdown Callout Rendering

Handout PDF renderer now shares the same callout contract as the frontend handout Markdown renderer. The source Markdown must use GitHub alert style blockquotes such as `> [!NOTE] 注意` and `> [!EXAMPLE] 例题 1`; the generator prompt is responsible for producing that syntax and must not output HTML callouts.

The PDF pipeline remains Markdown -> markdown-it-py HTML -> local KaTeX auto-render -> Playwright PDF. After markdown-it-py renders HTML, `render_markdown_pdf_html()` decorates only blockquotes whose first paragraph starts with one supported marker: `NOTE`, `EXAMPLE`, `SUMMARY`, `WARNING`, or `TIP`. Decorated blocks become `.pdf-callout` containers with rounded backgrounds and no left accent border. Unsupported or ordinary blockquotes keep the default quote styling.

This keeps PDF behavior aligned with the React renderer while preserving a small backend surface area: no database schema changes, no generated content migration, and no frontend print route dependency.