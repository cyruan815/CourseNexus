# Tech Debt Tracker

## 一句话定位

本文件集中记录 CourseNexus 当前已知技术债，避免散落在聊天记录、临时计划或局部代码注释里。

## 技术债清单

| 编号 | 事项 | 影响 | 优先级 | 状态 |
| --- | --- | --- | --- | --- |
| TD-001 | 统一错误响应和请求 ID 已落地。 | 基础契约已由后端测试覆盖。 | 高 | 已关闭（2026-07-09） |
| TD-002 | 本地鉴权和 `user_id` 注入已落地。 | 课程及后续业务资源已有归属校验基础。 | 高 | 已关闭（2026-07-09） |
| TD-003 | repository / service / schema 分层样板已落地。 | 主要基础模块已按统一结构实现。 | 高 | 已关闭（2026-07-09） |
| TD-004 | `.txt` / `.md` 解析、切片和引用定位已实现；复杂文档已接入 Docling adapter，图片 OCR 质量验收仍后置。 | PDF、PPT、Word 可进入解析路由；图片 OCR 效果仍需专门夹具验证。 | 高 | 部分完成 |
| TD-005 | 模型 provider、纯文本 parser、文件存储 adapter、LlamaIndex / Chroma RAG adapter 已实现；课程问答生产路径已接入相关性检索。 | 共享 RAG 基础设施和问答消费链路可验证，具体生成能力仍需后续业务任务。 | 高 | 已关闭（2026-07-10） |
| TD-006 | 前端 API client、路由、错误态和课程工作台壳已落地；完整资料和问答 UI 未实现。 | 后端能力可验证，但产品交互尚不完整。 | 中 | 部分完成 |
| TD-007 | SQLite 本地库已可迁移，但尚未形成数据库 reset/seed/dev data 规范。 | 多人本地调试时初始数据和迁移状态容易不一致。 | 中 | 待处理 |
| TD-008 | 生成内容 `content_json` 结构已在文档中定义，但没有 schema 校验代码。 | 模型输出结构可能漂移，前端渲染和后续导出会不稳定。 | 中 | 待处理 |
| TD-009 | 缺少后台任务或任务状态执行器。 | 资料解析、模型生成、PDF 导出等长耗时能力只能同步或手工模拟。 | 中 | 待处理 |
| TD-010 | 端到端验收尚未建立。 | 后续学习闭环容易出现前后端契约偏差。 | 中 | 待处理 |
| TD-011 | Docling + LlamaIndex + Chroma 本地摄取、索引、删除、重建和持久化验证已落地。 | Chroma 作为可重建派生索引，已由 rebuild 命令和集成测试覆盖。 | 高 | 已关闭（2026-07-10） |
| TD-012 | `material-context` 已区分问答相关性检索和指定材料全覆盖读取，并提供覆盖执行器和参考消费者；`course-qa` 已迁移到问答检索接口。 | 具体生成模块仍需逐步迁移到全材料批次接口。 | 高 | 已关闭（2026-07-10） |
| TD-013 | 指定材料生成的具体 schema、提示词和业务质量尚未实现。 | Flashcard、Quiz、Mindmap 仍需后续业务团队基于基础设施分别开发。 | 中 | 后续业务阶段 |
| TD-014 | AI 学习计划仍为确定性占位。 | S02 已接入全材料 map/reduce、保存幂等、替换、重生成和软删除。 | 高 | 已关闭（2026-07-11） |
| TD-015 | 公共 `OpenAIModelProvider.answer_question()` 固定调用 Responses API，尚未兼容仅提供 Chat Completions API 的 OpenAI-compatible 服务。 | DeepSeek 等不支持 `/responses` 的服务会让课程问答和 Study Mode 任务级问答稳定返回 `GENERATION_FAILED`；支持 Responses API 的模型不受影响。 | 高 | 待合并后统一修复 |
| TD-016 | 讲义 PDF 的 Markdown/HTML/Playwright 渲染链路尚未限制外部网络请求。 | 当前本地 POC 不阻塞使用；未来部署到共享服务或处理不可信生成内容时，Markdown 图片可能让后端 Chromium 请求内网或外部地址。 | 中 | 待处理（本地 POC 后置） |
| TD-017 | [资料理解流水线完整性与检索质量改造](material-understanding-pipeline-tech-debt.md)：当前把解析成功近似为内容完整，且问答检索缺少目录治理、去重、任务路由和全文覆盖保证。 | 可能静默漏页/漏元素、误标 `complete`、重解析破坏旧可用结果，并让 Top-K 被重复目录占满；涉及多格式解析、数据/索引兼容和前端透明度。 | 高 | 待规划（独立大型改造） |

## TD-015：问答模型接口兼容

### 当前行为

- 问题位于 `backend/app/integrations/model_provider/openai.py::OpenAIModelProvider.answer_question()`，属于 `main` 公共模型 provider，不是 Study Mode 的局部实现问题。
- 当前问答固定调用 `client.responses.create()`；课程详情 Agent 问答和 Study Mode 执行页任务级问答都复用该入口。
- 结构化生成路径已经能在 Responses API 不可用时回退到 Chat Completions，但普通问答路径没有同等兼容逻辑。
- 真实 Study Mode E2E 已观察到 `deepseek-chat` 调用 `/responses` 返回 404，因此任务级问答步骤被跳过；这不影响支持 Responses API 的 OpenAI 模型。

### 处理决定

- 允许当前业务 PR 先合并，合并后在公共模型 provider 中统一修复，业务模块不得各自复制或绕过模型调用逻辑。
- POC 阶段可在确认 Responses endpoint 不受支持时回退 `chat.completions.create()`；不得把鉴权失败、限流或普通服务端错误一律视为可回退条件。
- 后续若供应商差异继续扩大，应评估增加显式接口模式配置，例如 `responses`、`chat_completions` 和 `auto`，避免依赖失败探测决定调用协议。

### 完成标准

- 支持 Responses API 的 provider 继续通过原路径完成问答。
- `/responses` 明确不受支持时，能通过 Chat Completions 完成课程问答和任务级问答。
- 401、403、429 和非兼容性 5xx 不被错误回退，并继续返回稳定错误码。
- 补充 provider 单元测试，以及课程问答和 Study Mode 任务级问答的真实 provider E2E；验证报告不得再以跳过任务级问答作为通过条件。
- 修复后同步更新模型配置说明、相关领域文档和本技术债状态。

### 2026-07-13 补充：PR #1 候选回退与后续统一收口

- PR #1 最新分支已在同一公共 `OpenAIModelProvider.answer_question()` 中加入候选回退：先调用 `responses.create()`，仅在异常状态码为 404 时调用同一 provider 的 `chat.completions.create()`。课程详情 Agent 问答与 Study Mode 任务级问答仍复用该公共入口，不存在业务模块各自实现一套问答调用的情况。
- 该改动可作为验证 DeepSeek 当前 `/responses` 404 问题的 POC 兼容措施，但不能据此关闭 TD-015。HTTP 404 还可能来自错误的 `base_url`、模型或部署不存在、网关路由异常等配置/运行问题；仅按状态码回退可能掩盖真实故障，也会让只支持 Chat Completions 的 provider 在每次问答时先产生一次失败请求。
- 当前决定：允许业务 PR 合并后统一完成 provider 协议适配；合并前对候选回退至少验证不破坏 Responses API provider、能覆盖真实 DeepSeek 问答、且不会把 401、403、429、5xx 或网络错误误回退。
- 后续公共基础设施应提供显式协议模式（建议 `responses`、`chat_completions`、`auto`），使已知 provider 可直接选择正确 endpoint；`auto` 仅可在可确认的 endpoint 不支持场景下回退，并应按 `base_url + model` 缓存已探测的能力，避免每次请求重复试错。
- 设计/实现时需记录实际选择的协议和回退原因，但不得记录 API key、完整 prompt、资料正文或用户问题；若新增公共配置字段或 provider 策略，应同步更新配置契约、相关领域文档，并评估是否需要 ADR。

## TD-016：讲义 PDF 渲染网络访问边界

### 当前行为与接受范围

- PR #7 将讲义 PDF 导出改为 Markdown -> HTML -> Playwright Chromium 打印。`markdown-it-py` 默认允许 Markdown 图片语法，浏览器加载本地 HTML 时会继续请求图片中的 `http://` 或 `https://` 地址。
- 当前阶段只运行本地 POC，开发者主动导出自己课程中的生成内容；该风险暂不阻塞 PR #7 的本地功能验收，也不要求本轮修改 renderer。
- 该接受仅适用于本地、可信开发环境，不表示共享部署环境可以继续开放任意网络访问。

### 后续处理触发条件

满足下列任一条件时，必须在部署或开放使用前处理本技术债：

- 后端部署到可访问内网服务、云元数据地址或其他敏感网络资源的机器。
- 平台开放给非开发者、多用户或其他不完全可信用户使用。
- 讲义正文、引用摘录或其他 Markdown 输入可被上传资料、模型输出或用户输入间接控制。
- PDF 导出改为后台任务、批量任务或自动触发，用户不再逐次确认导出。

### 建议方案与完成标准

- 首选在 Playwright page 创建后注册请求拦截，只允许当前本地 HTML 文档及明确审核过的静态资源；默认拒绝 `http://`、`https://` 和其他非必要协议。
- 如果产品明确需要远程图片，应由后端受控下载器执行协议、域名、DNS 解析结果、重定向、文件大小、超时和 MIME 类型校验，再以本地资源交给浏览器；不得让 Chromium 直接访问任意 URL。
- 增加自动化测试，至少证明环回地址、私网地址、云元数据地址和重定向目标不会收到请求，同时正常纯文本、表格和本地可信资源仍能导出 PDF。
- 修复后同步更新 `docs/architecture/adr/0006-handout-pdf-rendering.md`、Study Mode 领域文档和本条状态。

## 更新规则

- 新增、关闭或拆分技术债时更新本表。
- 技术债影响产品范围、模块边界或数据契约时，同步更新对应正式文档分区。
- 关闭技术债时记录关闭方式，不只删除条目。
