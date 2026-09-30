# ADR 0008：前端统一文件预览器

- Status: Accepted
- Date: 2026-10-01

## Context

CourseNexus 当前仅在资料工作区和引用定位弹窗中预览 PDF。DOCX、PPTX、图片与文本资料已经可以上传和解析，但没有统一的原文件查看体验。各业务页面如果分别管理鉴权下载、对象 URL、加载状态和格式渲染，会造成重复实现，也会把具体第三方库扩散到业务模块。

课程资料属于当前用户的私有数据。预览链路不能依赖把文件上传到公开 Office 在线查看服务，也不能要求 Word、PowerPoint 或独立文档服务器。当前目标是只读查看，不提供 Office 编辑能力，也不承诺与桌面 Microsoft Office 像素级一致。

## Options

1. 所有非 PDF 文件由后端预先转换为 PDF，前端统一使用 PDF 查看器。
2. 使用 Microsoft Office Online、ONLYOFFICE 或商业统一文档 SDK。
3. 建设项目级统一预览组件，由内部适配器直接读取原文件数据：PDF 复用浏览器查看能力，DOCX 使用 `docx-preview`，PPTX 使用 `@aiden0z/pptx-renderer`，图片和纯文本使用浏览器原生能力。

## Decision

采用方案 3：

- 在 `frontend/src/components/file-preview/` 提供业务无关的统一预览组件。组件只接收已经取得的 `Blob`、文件名、MIME 类型和项目内部文件类型，不自行请求业务 API。
- 资料等业务模块负责鉴权获取原文件，并把文件数据传给统一组件；业务页面不得直接 import DOCX 或 PPTX 渲染库。
- PDF 使用临时 object URL 交给浏览器内置 PDF 查看能力；图片和纯文本使用浏览器原生元素安全展示。
- DOCX 通过 `docx-preview` 从 `ArrayBuffer` 只读渲染，关闭 altChunk 渲染；PPTX 通过 `@aiden0z/pptx-renderer` 从 `ArrayBuffer` 只读渲染，并启用库提供的压缩包与资源限制。PPTX 的 SmartArt/EMF 内嵌 PDF 回退使用项目自托管的 PDF.js 模块和 Worker，不请求第三方 CDN。
- DOCX、PPTX 适配器及其依赖使用动态 `import()`，普通页面和 PDF 预览不加载 Office 渲染依赖。
- 统一外壳拥有格式识别、加载/失败/不支持状态、对象 URL 生命周期和适配器销毁；格式适配器只负责把一个文件渲染到受控容器。
- 私有文件不发送给第三方服务。渲染失败时显示明确错误并保留原文件下载入口，不静默替换成解析文本。

## Reasons

- 业务页面只依赖一个稳定组件接口，未来可以替换单个格式的渲染器，而不影响资料工作区、引用定位或后续页面。
- 原始 DOCX/PPTX 直接在浏览器中解析和绘制，避免维护服务端 Office 转换、派生文件缓存、字体环境和失败补偿。
- 专用只读渲染器比完整 Office 编辑器更符合当前需求，依赖面和交互复杂度更可控。
- 动态加载把较大的 Office 依赖限制在用户确实打开相应文件时。

## Consequences

- `frontend/package.json` 增加 `docx-preview`、`@aiden0z/pptx-renderer` 及其 `pdfjs-dist` peer dependency。
- 浏览器必须下载并在本地解析整个 Office 文件；继续受单份上传 50 MiB 上限约束，渲染器还必须启用压缩包和资源数量限制。
- DOCX 分页、缺失字体、PPTX 动画、复杂三维效果、OLE 及部分 EMF/WMF 可能与桌面 Office 不完全一致；必须使用真实课程文件做回归。
- 资料原文件接口需要在维持用户归属、存储根目录和 `private, no-store` 约束的前提下，从仅返回 PDF 扩展为返回受支持的上传文件。
- 如果未来要求像素级 Office 保真、动画播放或编辑，需要另立 ADR 评估商业 SDK 或服务端 Office 转换，不在本决策中隐式扩大范围。
