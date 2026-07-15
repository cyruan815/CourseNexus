# ADR 0007：前端讲义 Mermaid 与原始 SVG 渲染

- Status: Accepted
- Date: 2026-07-15

## Context

任务讲义已经使用 `react-markdown + remark-gfm + remark-math + rehype-katex` 渲染 Markdown、表格、公式和 callout。当前本地 POC 还需要展示两类图形内容：Markdown 中直接提供的 `<svg>`，以及 fenced code block 中的 Mermaid 图表。

讲义正文虽然来自本地生成链路，但模型会处理用户输入和上传资料，不能把生成结果当作同源应用代码执行。前端必须在保留必要 SVG 能力的同时阻止原始 HTML、事件属性、危险 URL 和 Mermaid 输出中的可执行内容进入 DOM。后端 HTML 预览接口和 PDF Mermaid 对齐仍是后续工作。

## Options

1. 继续只渲染基础 Markdown，把 SVG 和 Mermaid 留作普通代码文本。
2. 后端统一把 Markdown、SVG 和 Mermaid 转成 HTML，再由前端展示。
3. 保留当前前端 Markdown renderer，引入 `rehype-raw` 解析原始 SVG，并引入 `mermaid` 在浏览器中把 Mermaid 代码块转换为 SVG。

## Decision

采用方案 3：

- `rehype-raw` 后接 `rehype-sanitize`，通过明确的 SVG 元素、属性和 URL 协议白名单保留必要图形；`script`、`iframe`、`object`、`embed`、`foreignObject`、`style` 和事件属性不得进入 React 渲染树。
- `mermaid` 作为前端运行时依赖；`language-mermaid` fenced code block 由独立 `MermaidDiagram` 组件异步渲染为内联 SVG。
- Mermaid 使用 `startOnLoad: false`、`securityLevel: "strict"` 和根级 `htmlLabels: false`，让图表标签输出为原生 SVG 文本而不是 `foreignObject` HTML。
- Mermaid 渲染出的 SVG 在注入前再次经过元素、属性和 URL 白名单净化；不允许通过 `dangerouslySetInnerHTML` 绕过同等安全边界。
- Mermaid 通过动态 `import()` 加载，避免普通讲义在首段解析时立即执行图表库。
- Mermaid 渲染失败时保留原始代码并显示失败提示；其他 fenced code block 继续按普通 `<pre><code>` 展示。
- Markdown 图片语法引用的 `.svg` 文件继续走现有 `<img>` 路径；原始 SVG、SVG 图片和 Mermaid 输出统一受响应式宽度样式约束。

## Reasons

- 保持 `HandoutMarkdownRenderer({ markdown })` 的公开 API 不变，详情页和开发预览页自动共享能力。
- Mermaid 原生输出 SVG，文字清晰且适合随讲义容器缩放。
- 标准 AST、净化和图表布局依赖避免维护自制 HTML/SVG 解析器或 Mermaid 语法实现。
- 动态加载把 Mermaid 的较大依赖图限制在确实出现 Mermaid 代码块的讲义路径。

## Consequences

- `frontend/package.json` 和 `pnpm-lock.yaml` 增加 `mermaid`、`rehype-raw` 与 `rehype-sanitize` 及其传递依赖。
- 原始 HTML 和 Mermaid SVG 都受白名单限制；新增 SVG 元素、属性或 URL 能力时必须先评估安全边界并补回归测试。
- Mermaid 图表只在浏览器前端渲染；当前 PDF renderer 不会因为本 ADR 自动获得 Mermaid 支持。
- 测试覆盖 Mermaid 严格模式、原生 SVG 文本标签、异步成功/失败、原始 HTML 注入、危险链接、事件属性和普通代码块回归行为。
