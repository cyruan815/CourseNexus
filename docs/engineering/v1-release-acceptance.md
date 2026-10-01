# V1 发布验收

## 验收分层

V1 发布门槛由两类互补验证组成：

- 确定性回归使用显式测试 Provider，证明注册登录、课程、上传解析、问答引用、内容生成、学习计划、失败重解析回退、删除和只读对账的状态流转。该层可进入 CI，但不能证明真实模型可用。
- 真实模型验收使用当前环境显式配置的 Provider 和真实嵌入索引，覆盖 TXT、PDF、DOCX、PPTX 四种样本的上传解析，并完成课程问答、复习提纲、学习计划和跨存储对账。该层禁止 Mock，必须在发布前单独通过。

历史数据库升级由 `tests/fixtures/legacy-v1-release.sql` 构造旧版本业务数据，验证材料、chunks、引用、学习计划、任务和二级任务升级到 Alembic head 后仍保持关联。

## 无隐私真实格式样本

样本位于 `backend/tests/fixtures/release_samples/`，包括同一知识主题的 TXT、PDF、DOCX 和 PPTX。`manifest.json` 记录受控锚点，自动测试同时检查：

- 文件签名和 OOXML 包结构真实有效；
- Office 包不含宏和外部关系；
- 生产解析器能从每种格式提取受控锚点；
- 样本不包含个人信息、密钥或真实课程资料。

前端开发环境提供 `/dev/file-preview`，可一次选择多份本地文件并直接交给 `UniversalFilePreview`。该入口不上传文件，且不会挂载到生产构建路由。发布验收应至少在 Chromium 中实际查看 PDF、DOCX 和 PPTX，并检查预览内容、原版式特征、下载入口和控制台异常；截图只放入 `tmp/`。

## 确定性验收

从 `backend/` 执行：

```powershell
python -m pytest tests/integration/test_v1_release_acceptance.py -q
python -m pytest tests/integrations/test_release_format_samples.py -q
python -m pytest tests/migrations/test_release_legacy_database_migration.py -q
```

闭环测试使用 pytest 临时目录中的文件 SQLite、上传目录和 Fake RAG，不读取日常数据。它会验证跨账号资源不可见、引用保存材料版本、生成与计划保存输入版本快照、失败候选不替换旧生效版本，以及删除材料后历史结果仍可审计。

## 真实模型验收

从 `backend/` 执行：

```powershell
python scripts/run_v1_release_acceptance.py
```

运行前必须显式配置：

- `EMBEDDING_API_KEY`
- `COURSE_QA_API_KEY`
- `OUTLINE_API_KEY`
- `STUDY_PLAN_GENERATOR_API_KEY`

`STUDY_PLAN_MAP_API_KEY` 可按正式运行规则省略并复用 generator 配置。脚本强制 `ENABLE_MOCK_MODEL_PROVIDER=false`；缺少任一必需配置时以退出码 `2` 结束，并记录 `MODEL_PROVIDER_NOT_CONFIGURED`，不得以 Mock 结果替代。

每次运行创建独立的 `tmp/v1-release-validation-<timestamp>-<suffix>/`，其中包含：

- 从空库升级到 Alembic head 的 SQLite；
- 独立上传目录和 Chroma collection；
- 仅含步骤、状态、耗时、资源 ID 和错误码的 `events.jsonl`；
- 仅含最终状态、资源 ID、对账状态和错误码的 `result.json`。

脚本不会把 Token、密码、API Key、模型地址、Prompt、资料正文或模型回答写入验收报告。成功退出码为 `0`；缺配置或业务验收失败为 `2`；未分类运行错误为 `1`。任何非零退出码都表示真实模型发布门槛未通过。

## 最终命令

发布候选至少执行：

```powershell
pnpm test
pnpm frontend:build
```

同时验证空库升级到 Alembic head、带历史数据的旧库升级、真实格式前端预览及真实模型脚本。临时数据库、日志、截图和报告由负责人确认后再删除，不进入 Git。

## 2026-10-01 发布候选证据

PR #40 的候选提交 `2d9f1a8` 完成并通过以下门槛：后端 726 passed / 1 skipped，前端 247 passed，前端生产构建成功；CI 的后端测试、空库迁移、旧库升级、前端测试和构建全部成功。真实模型脚本在禁用 Mock 的独立环境中完成 17 个步骤，覆盖四种真实格式、问答引用、复习提纲、学习计划保存和只读对账，对账结果为 clean。

本地原始报告保留在被 Git 忽略的 `tmp/v1-release-validation-*` 中，不作为仓库长期契约；可复现脚本、无隐私样本、CI 结果和 PR 记录构成长期证据。模型输出正文、Prompt、Token、密钥和服务地址均未写入报告。
