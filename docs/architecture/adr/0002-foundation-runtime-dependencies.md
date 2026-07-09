# ADR 0002: Foundation Runtime Dependencies

## Status

Accepted.

## Context

CourseNexus v0.1 的基础设施阶段需要补齐课程资料上传、前端页面路由和真实 LLM 调用的统一接入方式。项目仍保持本地 POC、前后端分离、FastAPI 单体后端和 React/Vite 前端。

当前已有技术栈 ADR 只记录了大类选择，没有记录这些基础运行依赖的边界：

- 文件上传接口需要处理 `multipart/form-data`。
- 前端需要稳定 URL 路由承载登录、首页、课程详情页和后续计划执行页。
- 后端后续所有真实 LLM 调用需要统一接入 OpenAI SDK，避免业务模块直接依赖外部模型 SDK。
- 前端构建工具在 POC 阶段需要锁定一个主版本，避免主版本升级影响小团队开发节奏。

## Options

1. 在基础设施阶段引入 `python-multipart`、`react-router-dom` 和 `openai`，并明确使用边界。
2. 暂不引入这些依赖，等到具体功能实现时各模块自行补充。
3. 后端不使用 OpenAI SDK，直接用 HTTP client 调 OpenAI API。
4. 前端暂不使用路由库，用组件状态模拟页面跳转。

## Decision

v0.1 基础设施阶段选择：

- 后端文件上传依赖：`python-multipart`。
- 前端路由依赖：`react-router-dom`。
- 真实 LLM 调用依赖：官方 `openai` Python SDK。
- 前端构建工具：POC 阶段锁定 Vite 7 主版本。

真实 LLM 调用只能通过 `backend/app/integrations/model_provider/` 下的 provider 适配层完成。业务 service、generator、planner 和 router 不直接 import `openai`，也不直接拼 HTTP 请求调用模型。

本地测试和无 API key 场景默认使用 deterministic mock provider，不依赖外部网络或真实 OpenAI API key。

## Reasons

- `python-multipart` 是 FastAPI 处理 `multipart/form-data` 文件上传的基础依赖，资料上传是后续问答和计划模式的共同入口。
- `react-router-dom` 能让登录页、首页、课程详情页和后续计划执行页拥有稳定 URL，便于前端状态恢复和页面间跳转。
- 使用官方 OpenAI SDK 可以减少手写 HTTP 调用和响应解析的不一致风险，也便于后续统一处理模型配置、超时、错误映射和重试策略。
- 将 OpenAI SDK 限定在 provider 适配层，可以保持生成模块、课程问答和计划模块的边界清晰。
- Vite 7 已经是当前项目骨架使用的大版本，基础设施阶段先锁定主版本，后续升级主版本必须单独验证并更新工程文档。

## Consequences

- `backend/pyproject.toml` 必须声明 `python-multipart` 和 `openai`。
- `frontend/package.json` 必须声明 `react-router-dom`，并保持 Vite 7 兼容范围。
- 根目录 `.env.example` 必须声明后端专用的 `OPENAI_MODEL`，并继续禁止把 API key 暴露为 `VITE_` 变量。
- 新增真实模型能力时，应复用 `OpenAIModelProvider` 或扩展 provider 协议，不应在业务模块中直接创建 OpenAI client。
- 单元测试应优先使用 mock provider；需要真实 OpenAI API 的验证必须作为单独的集成验证，并显式依赖本地环境变量。
- 如果后续升级 Vite 主版本、替换模型 SDK、引入非 OpenAI 模型供应商或增加后台任务队列，必须新增或更新 ADR。
