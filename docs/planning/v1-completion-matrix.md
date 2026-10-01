# V1 Completion Matrix

## 1. 口径

本矩阵是 CourseNexus “可靠的单机 V1”完成状态的正式入口。编号 P/S/R/M 指 2026-09～10 V1 收口审计中的产品、安全、可靠性和维护事项，不等同于 Study Mode 早期任务编号。

状态定义：

- `完成`：目标行为已合并到 `dev`，有自动化、迁移、浏览器或真实模型证据。
- `V1 接受延期`：当前限制已明确且不计作实现；只在本地单机边界内接受。
- `后续`：不是本轮 V1 承诺，保留触发条件和目标。

`tmp/v1-closeout-plan-review.md` 是历史评审输入，不再决定状态。发生冲突时，以产品 PRD、API/数据契约、架构/领域文档、合并代码和本矩阵为准。

## 2. 产品收口 P01～P10

| 项目 | 当前状态 | 达成结果或当前限制 | PR / 证据 |
| --- | --- | --- | --- |
| P01 URL 资料入口 | 完成 | 新增入口移除；旧创建接口返回 410；历史 URL 记录只读、可删除、不进入学习上下文。 | [PR #30](https://github.com/cyruan815/CourseNexus/pull/30) |
| P02 修改密码 | 完成 | 校验当前密码、更新密码并递增 `token_epoch`，既有 Token 整体失效。单会话撤销仍属 S02。 | [PR #30](https://github.com/cyruan815/CourseNexus/pull/30) |
| P03 任务测试题 PDF | V1 接受延期 | 任务测试题只导出 Markdown；任务讲义继续支持 PDF。 | [PR #30](https://github.com/cyruan815/CourseNexus/pull/30)、导出契约测试 |
| P04 引用能力口径 | 完成 | 课程/任务问答和任务测试题保存结构化引用；Handout/五类生成展示真实资料范围，不伪造逐条引用。 | [PR #32](https://github.com/cyruan815/CourseNexus/pull/32) |
| P05 建课后上传 | 完成 | 建课只提交课程信息；成功后进入详情并展示可关闭的一次性上传引导。 | [PR #32](https://github.com/cyruan815/CourseNexus/pull/32) |
| P06 引用定位 | 完成 | PDF 可靠页码定位；其他来源展示片段；未知页码不跳第一页；失效来源保留快照。 | [PR #32](https://github.com/cyruan815/CourseNexus/pull/32) |
| P07 非 PDF / Office 预览 | 完成 | 统一预览器只读渲染 PDF、DOCX、PPTX、图片和文本；Office 原文件在浏览器内解析，失败保留下载。 | [PR #33](https://github.com/cyruan815/CourseNexus/pull/33)、PR #40 浏览器验收 |
| P08 计划资料选择 | 完成 | 课程详情的显式 ID / 名称快照贯穿配置、诊断、预览、保存和 v2 草稿；空范围及失效范围不静默扩张。 | [PR #34](https://github.com/cyruan815/CourseNexus/pull/34) |
| P09 计划命名 | 完成 | 默认名包含目标和开始日期；保存前可编辑；空白/长度校验；同名允许，历史标题不改写。 | [PR #34](https://github.com/cyruan815/CourseNexus/pull/34) |
| P10 作答与学习反馈扩展 | 后续 | 作答历史、服务端判分、错题本、笔记和更完整掌握度反馈未实现。 | [技术债](tech-debt-tracker.md) |

## 3. 必须项建设

| 项目 | 当前状态 | 达成结果 | PR / 证据 |
| --- | --- | --- | --- |
| S03 受信 API 目标 | 完成 | 鉴权 JSON/Blob 请求只接受受信 `/api/v1/...`；Base URL 只允许 HTTP(S) Origin；拒绝绝对外部 URL、协议相对、反斜杠、穿越和 fragment。 | [PR #35](https://github.com/cyruan815/CourseNexus/pull/35) |
| S01 显式配置与 Mock | 完成 | 环境枚举、production 启动校验、用途级 Provider Factory、503 缺配置、Health 运行模式、全局 Mock 提示和日志脱敏。 | [PR #36](https://github.com/cyruan815/CourseNexus/pull/36) |
| M04 本地存储运行基线 | 完成 | 统一绝对路径、旧位置冲突保护、SQLite 外键/WAL/busy timeout/pre-ping、进程级 Chroma 生命周期和维护命令一致性。 | [PR #37](https://github.com/cyruan815/CourseNexus/pull/37) |
| R02 材料版本化重解析 | 完成 | 候选版本构建、版本化 chunk/vector、完整性校验、原子切换、失败回退、active-only 消费和输入版本快照。 | [PR #38](https://github.com/cyruan815/CourseNexus/pull/38) |
| R04 跨存储补偿与对账 | 完成 | 上传失败文件补偿、补偿稳定错误、发布前材料/版本复核、只读文件/DB/Chroma/版本对账。 | [PR #39](https://github.com/cyruan815/CourseNexus/pull/39) |
| V1 对抗性发布验收 | 完成 | 真实四格式、历史库升级、确定性闭环、跨用户、重解析故障、浏览器预览和真实模型 17 步闭环通过。 | [PR #40](https://github.com/cyruan815/CourseNexus/pull/40)、[验收规则](../engineering/v1-release-acceptance.md) |
| M07 文档与契约收口 | 完成（随 PR 合并生效） | 产品、API、架构、领域、配置、当前状态、路线图、技术债和本矩阵与最终实现一致。 | [PR #41](https://github.com/cyruan815/CourseNexus/pull/41)；合并后以 `dev` 记录为准 |

## 4. 公共契约现状

| 类别 | 当前正式契约 |
| --- | --- |
| 运行配置 | `APP_ENV=development|test|production`；`ENABLE_MOCK_MODEL_PROVIDER=false`；各模型用途独立 Key/Base URL/Model；学习计划 map 可按规则复用 generator。 |
| Health | 返回 `status`、`environment`、`mock_model_provider_enabled`，不返回密钥、端点或模型名。 |
| 材料 | `active_parse_version_id` 指向当前生效解析版本；`is_learning_ready` 是学习范围权威字段。 |
| 引用 | `material_version_id` 保存生成引用时实际读取的解析版本；资料删除后外键可空，名称/位置/片段快照保留。 |
| 输入范围 | 生成内容 `material_scope_json.material_versions` 与计划 `material_snapshot.material_versions` 保存实际 `{material_id, version_id}`。 |
| 维护 | `rebuild_rag_index` 只处理生效版本；`reconcile_storage` 默认只读，支持人类摘要/JSON 和稳定退出码，不自动修复。 |
| 主要错误 | `MODEL_PROVIDER_NOT_CONFIGURED`、`PARSE_ALREADY_IN_PROGRESS`、`PARSE_VERSION_SWITCH_FAILED`、`MATERIAL_SCOPE_STALE`、`UPLOAD_COMPENSATION_FAILED`、预览与导出错误等见 [API 约定](../api-data/api-conventions.md)。 |

## 5. 发布证据

PR #40 候选提交 `2d9f1a8`：

- `pnpm test`：后端 726 passed / 1 skipped；前端 247 passed。
- `pnpm frontend:build`：通过。
- GitHub Actions run `36845949491`：后端测试、空库迁移、旧库升级、前端测试和构建全部成功。
- 真实模型验收：Mock 关闭；TXT/PDF/DOCX/PPTX 上传解析、课程问答引用、复习提纲、学习计划保存与对账共 17 步通过。
- 对账：`clean`，0 个不一致。
- 报告脱敏：不保存 Token、密码、API Key、端点、Prompt、资料正文或模型回答。

M07 仅改变文档、非敏感示例配置和对应契约测试；最终以该 PR 的 CI 结果补足本矩阵的文档收口证据。

## 6. 明确延期项目

| 项目 | 单机 V1 当前行为 | 重新纳入的主要触发条件 |
| --- | --- | --- |
| R01 持久化 Job | 长任务仍以同步请求为主。 | 请求超时、并发排队、进程恢复成为真实问题。 |
| R03 完整任务化与质量升级 | 已有发布前资源复核、版本快照和失败记录，但没有统一持久化任务状态机；高级解析/检索质量仍按样本演进。 | 后台 Job 建立或真实质量样本证明需要。 |
| S02 服务端会话 | Bearer Token + `token_epoch` 整体撤销。 | 共享/公网部署、要求单会话注销或 Cookie 安全。 |
| S04 资源预算 | 存在分散的文件、token 和并发限制，没有统一用户/全局总预算。 | 共享部署或资源争抢出现。 |
| S05 PDF 网络隔离 | 仅接受可信本地环境。 | 后端可访问敏感网络或开放给不可信用户前。 |
| M01 大型模块拆分 | 保留现有模块，只做必要局部修改。 | 修改成本/回归频率证明结构已阻碍交付。 |
| M02 Query 状态统一 | 页面按现有 adapter/state 工作。 | 缓存一致性、请求去重或跨账号状态问题出现。 |
| M03 全面懒加载 | Office 适配器已按需加载，尚无全站首屏预算。 | 首屏资源和性能测量超出目标。 |
| M05 分页 | 列表继续使用当前规模契约。 | 数据量或响应内存达到明确阈值。 |
| M06 完整可观测性 | 有结构日志、request ID、阶段耗时和脱敏。 | 共享运行、成本管理或任务积压需要指标。 |
| P03 测试题 PDF | 只导出 Markdown。 | 完成题目分页/版式设计并重新评审。 |
| P10 产品扩展 | 不提供完整作答反馈系统。 | 进入下一产品阶段。 |

这些条目不是“已完成”，也不应从技术债或路线图中删除。
