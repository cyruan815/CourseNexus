# ADR 0006: Handout PDF Rendering Pipeline

## Status

Accepted

## Context

Study Mode 的今日讲义导出需要把结构化 `handout.content_json` 和真实回归 Markdown 产物转换为学生可阅读的 PDF。旧实现直接手写 PDF 对象流，只能输出基础文本，难以正确处理 Markdown 表格、标题层级、长公式片段、分页边距和中文/英文混排。

本地 POC 仍保持 FastAPI 单体后端和同步导出接口。导出不保存历史、不调用模型、不修改原 `AIGeneratedContent`，失败时由 exports service 映射为 `EXPORT_FAILED`。

## Options

1. 保留手写 PDF 对象流，继续补充字体和换行规则。
2. 使用 `markdown-it-py` + Jinja2 生成语义化 HTML，再通过 Playwright Chromium 打印 PDF。
3. 使用 Pandoc + XeLaTeX/LuaLaTeX 直接从 Markdown 生成 PDF。
4. 使用 WeasyPrint 等纯 Python HTML/CSS PDF 引擎。

## Decision

选择方案 2。

今日讲义导出采用：

```text
handout.content_json / Markdown
-> Markdown
-> HTML
-> Playwright Chromium page.pdf()
-> PDF bytes
```

后端新增运行依赖 `markdown-it-py`、`jinja2` 和 `playwright`。`render_handout_pdf()` 保持同步函数签名，内部先把结构化 handout 渲染为 Markdown，再复用 Markdown/HTML/Playwright 打印链路。独立 Markdown 回归转换复用同一 renderer。

当前不捆绑 KaTeX 静态资源；公式先保持为可换行文本。后续若接入本地 KaTeX，必须在 HTML 打印前等待公式和字体加载完成，并检查 `.katex-error`。

## Reasons

- 浏览器打印引擎天然支持 Markdown 转 HTML 后的表格、标题、列表、长文本换行和 A4 分页，比手写 PDF 对象流更适合讲义。
- Playwright 的 `page.pdf()` 能稳定控制纸张尺寸、边距、背景和 print CSS，适合后续增加页眉页脚、KaTeX 和视觉回归。
- 方案保持导出 API 契约不变，只替换 renderer 内部实现，风险边界集中在 `backend/app/modules/exports/renderer.py`。
- Pandoc/TeX 公式质量高但运行环境更重；WeasyPrint 集成简单但无法直接执行浏览器侧 KaTeX 自动渲染。

## Consequences

- 本地和 CI 环境若运行 handout PDF 导出测试，需要安装 Playwright Chromium：`uv run playwright install chromium`。
- 后端依赖声明必须包含 `markdown-it-py`、`jinja2` 和 `playwright`。
- 导出层应继续清洗用户可见引用残留，不展示 `formula-not-decoded`、``、``、`` 等 parser/OCR 噪声。
- PDF 视觉质量以后应通过渲染 PNG 或人工抽检验证；文本抽取只能作为辅助检查。
- 若后续引入 KaTeX 静态资源或替换 PDF 引擎，必须更新本 ADR 和 `docs/domains/study-mode/task-content.md`。