# 模型运行模式

## 1. 目标与边界

本领域负责把 CourseNexus 的模型配置解析、Provider 创建、显式 Mock、运行状态展示和凭据日志脱敏收敛为同一套规则。它不负责各业务 prompt、输出 schema、材料范围或生成结果持久化。

核心不变量：

- 真实 Provider 只能读取当前逻辑用途自己的端点配置。
- 缺少配置不会产生模拟结果，而是返回 `503 MODEL_PROVIDER_NOT_CONFIGURED`。
- Mock 必须显式开启，且只允许 `development` / `test`。
- `production` 在错误配置下拒绝启动。
- 运行状态可以公开，凭据和模型端点不得通过 Health、前端或日志泄露。

## 2. 实现入口

| 职责 | 入口 |
| --- | --- |
| 环境、Secret、模型用途与 Mock 校验 | `backend/app/core/config.py` |
| Provider 统一创建和稳定缺配置错误 | `backend/app/integrations/model_provider/factory.py` |
| OpenAI-compatible 适配 | `backend/app/integrations/model_provider/openai.py` |
| Deterministic Mock | `backend/app/integrations/model_provider/mock.py` |
| Health 运行状态 | `backend/app/api/router.py` |
| 凭据脱敏 | `backend/app/core/redaction.py`、`backend/app/core/logging.py` |
| 前端运行状态读取 | `frontend/src/api/system.ts` |
| 前端全局提示 | `frontend/src/components/RuntimeModeBanner.tsx` |

业务 Router 只能依赖统一工厂，不直接实例化真实或 Mock Provider。测试可以通过 FastAPI dependency override 或直接向 service 注入 fake / mock provider。

## 3. 运行流程

```mermaid
flowchart LR
    A[业务请求] --> B[用途级 Provider dependency]
    B --> C[统一 Provider Factory]
    C -->|用途 API Key 存在| D[OpenAIModelProvider]
    C -->|无 Key 且显式 Mock| E[MockModelProvider]
    C -->|无 Key 且 Mock 关闭| F[503 MODEL_PROVIDER_NOT_CONFIGURED]
    G[GET /api/v1/health] --> H[前端 RuntimeModeBanner]
    H -->|Mock=true| I[全局模拟模式提示]
    H -->|Mock=false 或请求失败| J[不显示且不阻塞页面]
```

学习计划 `study_plan_map` 是唯一的派生端点：没有 map 覆盖项时复用已创建的 generator Provider；存在 map 模型、地址、Key 或 API style 覆盖时，以 map 显式值优先，缺项才从 generator 继承。其他用途不允许类似回退。

## 4. 配置与状态规则

- `APP_ENV=development|test|production`，其他值由 Settings 校验拒绝。
- `ENABLE_MOCK_MODEL_PROVIDER=false` 为默认值。
- production 的 `SECRET_KEY` 去除首尾空白后必须非空、不同于开发默认值且长度至少 32。
- production 必须为 `MODEL_PURPOSES` 中所有当前 V1 用途配置非空 API Key；学习计划 map 不单独要求 Key，因为它按上述显式规则复用 generator。
- Health 只返回 `status`、`environment` 和 `mock_model_provider_enabled`。

## 5. 脱敏、失败与资源预算

`SensitiveDataRedactor` 在统一 Formatter 输出完成后处理最终字符串，因此同时覆盖日志正文、`%s` 参数、异常摘要和文件 traceback。它屏蔽当前 Settings 中的签名密钥、全部用途 API Key、兼容 Key、Bearer Token，以及 `api_key=`、`secret_key=`、`authorization=` 形式的带标签凭据。

Provider Factory 只做常数次配置读取和对象选择，时间与空间复杂度均为 `O(1)`；日志脱敏对文本长度和已配置凭据数近似为 `O(text_length * credential_count)`。当前用途数量固定且较小，不设置额外缓存，避免配置切换与测试隔离复杂化。

Health 失败只隐藏前端提示，不影响应用壳。真实 Provider 的上游调用失败继续按业务链路映射为 `GENERATION_FAILED`；只有“没有可调用 Provider”使用 `MODEL_PROVIDER_NOT_CONFIGURED`，两者不得混用。

## 6. 测试与验收入口

- 配置：`backend/tests/core/test_runtime_config.py`、`backend/tests/core/test_env_example.py`
- Factory：`backend/tests/integrations/test_model_provider_factory.py`
- Router 接入：各业务模块的 `test_*model_provider*` / `test_provider_config.py`
- Health：`backend/tests/test_health.py`
- 脱敏：`backend/tests/core/test_redaction.py`、`backend/tests/core/test_logging.py`
- 前端：`frontend/tests/api/system.test.ts`、`frontend/tests/components/runtime-mode-banner.test.tsx`

视觉验收需同时检查桌面与窄屏：Mock 开启时提示清晰且不遮挡主操作，关闭或 Health 失败时不出现。真实模型发布验收不能用 Mock 结果替代。
