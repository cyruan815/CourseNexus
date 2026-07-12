# Study Mode 轻量化优先任务执行指南

更新时间：2026-07-13

本文用于指导后续 Codex 窗口实现 Study Mode 轻量化收口任务。它不是 PRD 重述，而是把当前最高优先级的后端缺口拆成可执行、可验证、可提交的小任务。

## 当前口径

原始 PRD 要求测试题页面支持作答、解析、PDF 导出和完整练习体验。当前轻量化口径调整为：

- 测试题只需要能生成并输出一个可读的 Markdown 文件。
- 不做学生作答。
- 不做自动判分。
- 不做 attempt 历史。
- 不做错题本。
- 不做任务测试题 PDF 导出。

Study Mode 当前优先补三件事：

1. 任务测试题 Markdown 输出。
2. 今日讲义 PDF 导出。
3. 计划执行页任务级 Agent 问答。

开始这些任务前，先确认 P5a 资料解析 warning 的本地改动已经完成验证、review、commit 或隔离；不要在脏工作区里混入不相关改动。

## 全局约束

- 当前分支：`feature/study-mode`。
- 后端 owner 可以做 API、契约、测试、文档；不做前端页面、组件或样式。
- 不新增 migration，除非项目负责人明确批准。
- 不新增 `task_test_attempts`、`task_test_answers`、`export_records`、`handouts` 或 `task_tests` 独立业务表。
- 测试题 Markdown 输出应复用已有 `ai_generated_contents.content_type = task_test` 和 `content_json`。
- 今日讲义 PDF 输出应复用已有 `ai_generated_contents.content_type = handout`。
- 不触碰 P0 的 task_test generator 质量修复，除非 P0 owner 已完成并明确交接。
- 不提交已知无关未跟踪文件：
  - `P0：让 diagnostic_profile 真正影响 planner.md`
  - `backend/uv.lock`
- 每完成一个可验证小任务，单独验证、单独 commit，并同步更新相关 docs 和 `docs/planning/study-mode-priority-list.md`。

## 推荐顺序

### T0：工作区收口检查

目标：

- 确认当前工作区没有混杂未完成任务。
- 如果 P5a 已在本地完成，先让 P5a 独立验证、review、commit、push 后，再开始本文任务。

建议命令：

```powershell
git status --short --branch
git diff --stat
```

停止条件：

- 如果 `backend/app/modules/material_context/*`、`backend/app/modules/study_plans/service.py` 或 `docs/planning/study-mode-priority-list.md` 仍有 P5a 未提交改动，先不要开始 T1/T2/T3。
- 如果 P0 窗口仍在修改 `task_test` generator 或 `learning_execution` 主链路，T1 只做 renderer/export 设计，不改 generator。

### T1：任务测试题 Markdown 输出

目标：

- 基于已成功生成的 `task_test.content_json` 输出 Markdown。
- 如果没有成功生成内容，前端仍通过现有 `POST /api/v1/study-subtasks/{subtask_id}/task-tests` 先生成。
- Markdown 应包含题目、选项、正确答案、解析和引用来源。

推荐 API：

```http
GET /api/v1/generated-contents/{generated_content_id}/exports/markdown
```

支持范围：

- `content_type = task_test`
- `generation_status = success`
- 当前登录用户必须拥有该 generated content 所属课程和二级任务。

响应建议：

- `media_type = text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="task-test-{generated_content_id}.md"`
- 返回 Markdown 文件内容。

Markdown 最小结构：

```md
# {title}

## Instructions

{instructions}

## Questions

### 1. {question_text}

- A. ...
- B. ...

Answer: A

Explanation: ...

Sources:

- {material_name}, p.{page_or_page_index}: {hit_text}
```

边界规则：

- 非 `task_test` 内容返回稳定错误，例如 `EXPORT_UNSUPPORTED_CONTENT_TYPE`。
- `generation_status != success` 返回稳定错误，例如 `EXPORT_CONTENT_NOT_READY`。
- `content_json.questions` 缺失、为空或结构畸形时返回 `EXPORT_CONTENT_INVALID`，不要生成半坏文件。
- `source_citation_ids` 只和 `GeneratedContentRead.source_citations` 匹配；找不到时写 `Sources: unavailable`，不要伪造引用。
- 不修改任务完成状态。
- 不写 `checkin_records`。
- 不生成 PDF。

建议修改文件：

- `backend/app/modules/exports/`
- `backend/app/modules/generated_content/service.py`
- `backend/app/api/router.py`
- `backend/tests/modules/exports/`
- `docs/api-data/contracts.md`
- `docs/api-data/frontend-integration.md`
- `docs/domains/study-mode/task-content.md`
- `docs/planning/study-mode-priority-list.md`

建议测试：

- 成功导出 `task_test` Markdown。
- 非本人 generated content 返回无权限或不存在。
- `content_type != task_test` 返回不支持。
- failed / generating 内容返回 not ready。
- 畸形 `content_json` 返回 invalid。
- 引用缺失时不伪造来源。

建议验证命令：

```powershell
uv run python -m pytest tests/modules/exports tests/modules/generated_content tests/modules/learning_execution/test_task_content_api.py -q
```

### T2：今日讲义 PDF 导出

目标：

- 为已成功生成的今日讲义提供 PDF 导出。
- 轻量化阶段只要求 `content_type = handout`。
- 任务测试题 PDF 不做，已由 T1 Markdown 输出替代。

推荐 API：

```http
GET /api/v1/generated-contents/{generated_content_id}/exports/pdf
```

支持范围：

- `content_type = handout`
- `generation_status = success`
- 当前登录用户必须拥有该 generated content 所属课程和二级任务。

响应建议：

- `media_type = application/pdf`
- `Content-Disposition: attachment; filename="handout-{generated_content_id}.pdf"`
- 不保存导出历史，不新增 `export_records`。

边界规则：

- `task_test` 调用 PDF 导出返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`，并在 docs 写明轻量化阶段测试题使用 Markdown 导出。
- failed / generating 内容返回 `EXPORT_CONTENT_NOT_READY`。
- handout `content_json` 畸形返回 `EXPORT_CONTENT_INVALID`。
- PDF 生成失败返回 `EXPORT_FAILED`，不影响原 generated content。

实现建议：

- 新建 `exports` 模块 router/service/renderer。
- renderer 只做保守排版：标题、overview、learning objectives、sections、summary、引用来源。
- 优先使用项目已有依赖；如果需要引入新 PDF 依赖，先确认是否已有依赖和是否需要 ADR。
- 不需要做复杂样式、分页目录或图片嵌入。

建议修改文件：

- `backend/app/modules/exports/`
- `backend/app/api/router.py`
- `backend/tests/modules/exports/`
- `docs/api-data/contracts.md`
- `docs/api-data/frontend-integration.md`
- `docs/domains/study-mode/task-content.md`
- `docs/planning/study-mode-priority-list.md`

建议测试：

- 成功导出 handout PDF，响应头和 media type 正确。
- 非本人 generated content 不可导出。
- `task_test` PDF 导出返回不支持。
- failed / generating 内容不可导出。
- 畸形 handout 内容返回 invalid。

建议验证命令：

```powershell
uv run python -m pytest tests/modules/exports tests/modules/learning_execution/test_task_content_api.py -q
```

### T3：计划执行页任务级 Agent 问答

目标：

- 支持用户在计划执行页围绕当前二级任务提问。
- 问答上下文优先使用当前二级任务的 `related_material_ids_json`。
- 当前二级任务没有可用资料时，再按既有课程问答策略兜底或返回无资料提示。

推荐 API：

```http
POST /api/v1/study-subtasks/{subtask_id}/qa/questions
```

请求体建议复用课程问答字段：

```json
{
  "conversation_id": null,
  "question": "这一节的关键公式是什么？"
}
```

响应体建议复用课程问答响应 DTO，至少包含：

- `answer_text`
- `answer_type`
- `conversation_id`
- `message_id`
- `source_citations`
- `used_material_ids`

数据流：

1. 通过 `subtask_id` 查询二级任务、父一级任务、计划和课程。
2. 校验当前用户拥有该课程和计划。
3. 构造任务上下文：
   - 当前二级任务标题、描述、类型。
   - 父一级任务标题和任务日期。
   - 计划标题和目标。
   - 当前二级任务关联资料。
4. 调用已有课程问答检索/生成能力，但资料范围限定为当前任务关联资料。
5. 保存 `Conversation.source_page = "task_execution"`。
6. 在用户消息的 `material_scope_json` 中记录 `subtask_id`、`task_id` 和实际使用的资料范围。

边界规则：

- 不新增数据库表。
- 不新增 task conversation 表。
- 不跨课程复用 conversation。
- 传入的 `conversation_id` 必须属于当前用户、当前课程，且 source_page 可兼容任务执行页。
- 当前任务关联资料中没有 parsed chunk 时，返回明确无资料提示，不伪造引用。
- 引用来源必须来自实际检索命中的课程资料。
- 该问答不修改二级任务完成状态。
- 该问答不写 `checkin_records`。

建议修改文件：

- `backend/app/modules/learning_execution/router.py`
- `backend/app/modules/learning_execution/service.py`
- `backend/app/modules/course_qa/schemas.py`
- `backend/app/modules/course_qa/service.py`
- `backend/tests/modules/learning_execution/`
- `backend/tests/modules/course_qa/`
- `docs/api-data/contracts.md`
- `docs/api-data/frontend-integration.md`
- `docs/domains/study-mode/learning-execution.md`
- `docs/planning/study-mode-priority-list.md`

建议测试：

- 当前二级任务可发起任务级问答，并返回引用。
- 任务级问答只使用当前二级任务允许的资料。
- 跨用户 subtask 返回无权限或不存在。
- 跨课程 conversation 复用被拒绝。
- 当前任务没有 parsed 资料时返回 no_source / 无资料提示。
- 问答不会改变任务完成状态或打卡记录。

建议验证命令：

```powershell
uv run python -m pytest tests/modules/learning_execution tests/modules/course_qa -q
```

## 文档同步要求

每完成 T1/T2/T3 任一项，都必须同步：

- `docs/planning/study-mode-priority-list.md`
- `docs/api-data/contracts.md`
- `docs/api-data/frontend-integration.md`
- `docs/domains/study-mode/task-content.md`
- `docs/domains/study-mode/learning-execution.md`

如果实现中新增或改变错误码，还要同步 API 契约中的错误说明。

## 完成标准

每个任务完成时必须满足：

- 有后端测试覆盖成功路径、权限、状态错误和畸形内容。
- 验证命令通过。
- docs 已更新。
- priority list 写明完成日期、验证命令和 commit。
- commit message 使用 Conventional Commits，例如：
  - `feat(study-mode): 支持任务测试题 Markdown 导出`
  - `feat(study-mode): 支持今日讲义 PDF 导出`
  - `feat(study-mode): 接入执行页任务级问答`

## 给 Codex 的开工提示词

```text
我要做 CourseNexus Study Mode 轻量化优先任务，请先阅读：

1. AGENTS.md
2. docs/index.md
3. docs/planning/study-mode-lightweight-priority-guide.md
4. docs/planning/study-mode-priority-list.md
5. docs/api-data/contracts.md
6. docs/api-data/frontend-integration.md
7. docs/domains/study-mode/task-content.md
8. docs/domains/study-mode/learning-execution.md

请严格遵守：

- 当前分支 feature/study-mode。
- 后端 API / 契约 / 测试 / 文档同步为主，不做前端页面、组件或样式。
- 不新增 migration。
- 不新增 task_test_attempts、task_test_answers、export_records、handouts、task_tests 独立业务表。
- 不提交未跟踪的 P0 文档或 backend/uv.lock。
- 不触碰 P0 task_test generator 质量修复，除非已明确完成交接。
- 每完成一个可验证小任务，运行匹配测试、更新 docs 和 priority list、单独 commit。

请按顺序执行：

1. 先检查工作区；如果 P5a 或 P0 仍有未提交/冲突改动，先停下报告。
2. 实现 T1：任务测试题 Markdown 输出。
3. 验证、docs、commit。
4. 实现 T2：今日讲义 PDF 导出。
5. 验证、docs、commit。
6. 实现 T3：计划执行页任务级 Agent 问答。
7. 验证、docs、commit。

如果发现任一任务需要 migration、新依赖、前端实现或触碰 P0 owner 文件，请停下说明，不要顺手扩大范围。
```