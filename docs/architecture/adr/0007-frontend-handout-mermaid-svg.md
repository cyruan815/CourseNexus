# ADR 0007：前端讲义 Mermaid 与原始 SVG 渲染

- Status: Accepted
- Date: 2026-07-15

## Context

任务讲义已经使用 `react-markdown + remark-gfm + remark-math + rehype-katex` 渲染 Markdown、表格、公式和 callout。当前本地 POC 还需要展示两类图形内容：Markdown 中直接提供的 `<svg>`，以及 fenced code block 中的 Mermaid 图表。

本阶段讲义内容来自本地可信生成链路，用户明确选择先验证效果，不把原始 HTML 净化作为本次范围。后端 HTML 预览接口、PDF Mermaid 对齐和面向不可信内容的安全隔离仍是后续工作。

## Options

1. 继续只渲染基础 Markdown，把 SVG 和 Mermaid 留作普通代码文本。
2. 后端统一把 Markdown、SVG 和 Mermaid 转成 HTML，再由前端展示。
3. 保留当前前端 Markdown renderer，引入 `rehype-raw` 解析原始 SVG，并引入 `mermaid` 在浏览器中把 Mermaid 代码块转换为 SVG。

## Decision

采用方案 3：

- `rehype-raw` 加入 `ReactMarkdown.rehypePlugins`，允许可信讲义中的原始 `<svg>` 进入 React 渲染树。
- `mermaid` 作为前端运行时依赖；`language-mermaid` fenced code block 由独立 `MermaidDiagram` 组件异步渲染为内联 SVG。
- Mermaid 使用 `startOnLoad: false` 和 `securityLevel: "loose"`，符合本地可信 POC 的功能优先边界。
- Mermaid 通过动态 `import()` 加载，避免普通讲义在首段解析时立即执行图表库。
- Mermaid 渲染失败时保留原始代码并显示失败提示；其他 fenced code block 继续按普通 `<pre><code>` 展示。
- Markdown 图片语法引用的 `.svg` 文件继续走现有 `<img>` 路径；原始 SVG、SVG 图片和 Mermaid 输出统一受响应式宽度样式约束。

## Reasons

- 保持 `HandoutMarkdownRenderer({ markdown })` 的公开 API 不变，详情页和开发预览页自动共享能力。
- Mermaid 原生输出 SVG，文字清晰且适合随讲义容器缩放。
- 两个依赖分别承担标准 AST 解析和图表布局，避免维护自制 HTML/SVG 解析器或 Mermaid 语法实现。
- 动态加载把 Mermaid 的较大依赖图限制在确实出现 Mermaid 代码块的讲义路径。

## Consequences

- `frontend/package.json` 和 `pnpm-lock.yaml` 增加 `mermaid` 与 `rehype-raw` 及其传递依赖。
- 原始 HTML 不经过净化，当前实现只能用于可信本地 POC 内容；在接入用户可编辑内容、外部 Markdown 或生产环境前，必须新增净化、白名单或隔离渲染边界。
- Mermaid 图表只在浏览器前端渲染；当前 PDF renderer 不会因为本 ADR 自动获得 Mermaid 支持。
- 测试需要 mock Mermaid 的异步渲染，覆盖成功、失败和普通代码块回归行为。
