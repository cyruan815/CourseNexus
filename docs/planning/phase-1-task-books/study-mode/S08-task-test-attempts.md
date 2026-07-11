# S08 任务测试题作答记录与客观题判分

## 0. 业务功能说明

- **业务场景**：学生进入计划学习执行页后，S06 已经为测试类二级任务生成任务测试题；学生需要完成作答、提交答案，并在提交后看到得分、正确情况、解析和历史记录。
- **用户能力**：对一份已成功生成的 `task_test` 一次性提交答案；系统保存本次作答记录，自动判定客观题，并允许学生查看最近一次和历史作答结果。
- **业务结果**：计划学习模式补齐“生成测试题 -> 学生作答 -> 结果反馈 -> 历史复盘”的学习反馈链路。
- **业务边界**：本任务只处理 S06 生成的 `task_test` 作答记录和客观题判分，不重新生成题目，不保存讲义阅读记录，不做错题本、排行榜或 AI 简答判分。

## 1. 任务信息

- 编号与名称：`S08` 任务测试题作答记录与客观题判分。
- 负责人角色：计划学习模式后端开发者。
- 目标：为 `ai_generated_contents.content_type = task_test` 的生成内容新增作答提交、判分和历史查询能力。
- 前置依赖：S06 已合并并稳定 `TaskTestContent` schema；S04 执行上下文可以定位当前二级任务；S01 的“第一阶段不新增表”结论需要因本扩展任务重新评审。
- 范围外：不生成 `task_test`；不修改 handout；不做 AI 判简答题；不做草稿保存；不做错题本、统计看板、排行、奖励系统或前端页面。

## 2. 实现范围

### 2.1 作答提交与判分

- 第一版只支持一次性提交答案，不支持边做边保存草稿。
- 每次提交创建一条新的作答记录；允许同一学生对同一份 `task_test` 多次提交，历史记录全部保留。
- 提交对象必须是：
  - `content_type = task_test`
  - `generation_status = success`
  - 未软删除
  - 属于当前用户
  - 绑定的 `study_subtask_id` 仍属于当前用户和课程
- 提交前必须用 S06 的 `TaskTestContent` schema 二次校验 `content_json`；schema 无效返回 `GENERATION_SCHEMA_INVALID`。
- 自动判分范围：
  - `single_choice`：学生答案与标准答案完全一致为正确。
  - `multiple_choice`：学生答案集合与标准答案集合完全一致为正确，忽略顺序但不忽略多选/少选。
  - `true_false`：布尔值或规范化后的 true/false 文本完全一致为正确。
  - `short_answer`：只保存学生答案，不自动判分，结果标记为 `needs_review`。
- 总分第一版按题均分：每道客观题 `1` 分，简答题 `0` 分且不计入自动正确率分母；若后续需要主观题评分，单独新增 AI 评分任务。
- 提交后返回：
  - attempt 基本信息
  - 总题数、客观题数、正确数、得分、满分
  - 每题作答、正确性、标准答案、解析、引用
  - 简答题的 `needs_review = true`

### 2.2 历史查看

- 提供按 `generated_content_id` 查询当前用户历史 attempts 的接口，默认按 `submitted_at desc` 排序。
- 提供最近一次 attempt 查询接口，供执行页刷新后展示“上次作答结果”。
- 提供 attempt 详情查询接口；必须校验 attempt 属于当前用户。
- 历史记录只是查看，不提供“回档”“设为当前版本”或覆盖旧结果。

### 2.3 数据持久化

本任务需要新增 migration。数据库变更必须由项目负责人确认后执行，不得混入 S06 或 S07。

建议新增两张表：

`task_test_attempts`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 主键。 |
| `user_id` | string | FK -> `users.id`。 |
| `course_id` | string | FK -> `courses.id`。 |
| `generated_content_id` | string | FK -> `ai_generated_contents.id`，指向 S06 生成的 task_test。 |
| `study_subtask_id` | string | FK -> `study_subtasks.id`，冗余保存便于权限和执行页查询。 |
| `status` | string | 第一版固定 `submitted`，预留后续 `in_progress`。 |
| `question_count` | integer | 题目总数。 |
| `auto_graded_count` | integer | 自动判分题目数，不含简答题。 |
| `correct_count` | integer | 自动判分正确数。 |
| `score` | numeric | 自动得分。 |
| `max_score` | numeric | 自动满分。 |
| `submitted_at` | datetime | 提交时间，UTC。 |
| `created_at` | datetime | 创建时间。 |
| `updated_at` | datetime | 更新时间。 |
| `deleted_at` | datetime null | 预留软删除。 |

`task_test_answers`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 主键。 |
| `attempt_id` | string | FK -> `task_test_attempts.id`。 |
| `question_id` | string | 对应 `content_json.questions[].id`。 |
| `question_type` | string | `single_choice`、`multiple_choice`、`true_false`、`short_answer`。 |
| `student_answer_json` | JSON/text | 学生答案，按题型保存字符串、布尔或字符串数组。 |
| `correct_answer_json` | JSON/text | 题目提交时的标准答案快照。 |
| `is_correct` | boolean null | 客观题 true/false；简答题为 null。 |
| `needs_review` | boolean | 简答题为 true。 |
| `score` | numeric | 本题得分。 |
| `max_score` | numeric | 本题满分。 |
| `feedback` | text null | 第一版可保存题目解析或系统反馈。 |
| `created_at` | datetime | 创建时间。 |
| `updated_at` | datetime | 更新时间。 |

建议索引：
- `task_test_attempts(user_id, generated_content_id, submitted_at)`
- `task_test_attempts(user_id, study_subtask_id, submitted_at)`
- `task_test_answers(attempt_id, question_id)`

唯一约束第一版不限制同一用户重复提交；每次提交都是一次新的 attempt。

### 2.4 精确文件边界

创建：
- `backend/app/modules/task_test_attempts/__init__.py`
- `backend/app/modules/task_test_attempts/models.py`
- `backend/app/modules/task_test_attempts/schemas.py`
- `backend/app/modules/task_test_attempts/service.py`
- `backend/app/modules/task_test_attempts/router.py`
- `backend/tests/modules/task_test_attempts/test_task_test_attempts_service.py`
- `backend/tests/modules/task_test_attempts/test_task_test_attempts_api.py`
- `backend/tests/integration/test_task_test_attempt_flow.py`
- 新 Alembic migration：新增 `task_test_attempts` 和 `task_test_answers`

修改：
- `backend/app/api/router.py`
- `backend/app/db/models.py` 或模块模型聚合入口
- `docs/api-data/table-schema.md`
- `docs/api-data/data-model.md`
- `docs/api-data/contracts.md`
- `docs/architecture/module-boundaries.md`
- `docs/architecture/runtime-flows.md`
- `docs/planning/current-state.md`

禁止修改：
- S06 generator prompt/schema 的语义
- 五类独立生成器
- `ai_generated_contents` 既有字段语义
- 任务完成、打卡和 PDF 导出状态
- 前端页面

## 3. 字段与接口

### 3.1 新增 API

`POST /api/v1/generated-contents/{generated_content_id}/task-test-attempts`

请求：

```json
{
  "answers": [
    {"question_id": "q_1", "answer": "A"},
    {"question_id": "q_2", "answer": ["A", "C"]},
    {"question_id": "q_3", "answer": true},
    {"question_id": "q_4", "answer": "我的简答内容"}
  ]
}
```

响应：

```json
{
  "id": "attempt_...",
  "generated_content_id": "gen_...",
  "study_subtask_id": "subtask_...",
  "status": "submitted",
  "question_count": 4,
  "auto_graded_count": 3,
  "correct_count": 2,
  "score": 2,
  "max_score": 3,
  "submitted_at": "2026-07-11T12:00:00Z",
  "answers": [
    {
      "question_id": "q_1",
      "question_type": "single_choice",
      "student_answer": "A",
      "correct_answer": "A",
      "is_correct": true,
      "needs_review": false,
      "score": 1,
      "max_score": 1,
      "explanation": "解析",
      "source_citation_ids": ["cit_1"]
    }
  ]
}
```

`GET /api/v1/generated-contents/{generated_content_id}/task-test-attempts`

- 查询当前用户对该 `task_test` 的历史作答，按 `submitted_at desc` 排序。

`GET /api/v1/generated-contents/{generated_content_id}/task-test-attempts/latest`

- 查询当前用户最近一次作答；没有记录返回 `data: null` 或 404，需在实现计划中固定。

`GET /api/v1/task-test-attempts/{attempt_id}`

- 查询一次作答详情。

### 3.2 错误码

- 401 `UNAUTHORIZED`
- 404 `NOT_FOUND`
- 409 `STATE_CONFLICT`：内容不是 `task_test`、生成未成功、内容已删除、二级任务归属不一致。
- 422 `VALIDATION_ERROR`：答案格式不符合题型、缺少必答题、出现未知 `question_id`。
- 500 `GENERATION_SCHEMA_INVALID`：`task_test.content_json` 不符合 S06 schema。

## 4. 测试计划

### 4.1 Service 测试

- 成功提交包含四类题型的答案。
- `single_choice` 判分正确和错误。
- `multiple_choice` 忽略顺序但不允许多选/少选。
- `true_false` 支持布尔规范化。
- `short_answer` 只保存，`needs_review = true`，不计入自动判分满分。
- 缺少题目答案、未知 question_id、答案类型错误返回 `VALIDATION_ERROR`。
- 同一用户同一 `task_test` 多次提交创建多条 attempts。
- 跨用户、软删除、非 success、非 task_test 返回稳定错误。
- 提交失败不创建半截 attempt 或 answer。

### 4.2 API 测试

- 提交接口返回 attempt 结果和逐题反馈。
- 历史列表按提交时间倒序。
- latest 返回最近一次作答。
- attempt detail 校验用户权限。
- 401/404/409/422/500 envelope 一致。

### 4.3 集成测试

- S06 生成 `task_test` 后，S08 提交答案并保存历史。
- S08 不修改 `study_subtasks.status`、`study_tasks.status`、`study_plans.status` 或 `checkin_records`。
- S04 completion 仍由完成按钮触发；提交测试题不自动完成二级任务，除非后续产品口径单独确认。
- 删除计划或内容软删除后，历史记录不物理删除，但新提交被拒绝。

### 4.4 命令与预期

```powershell
cd backend
conda run -n course-nexus python -m alembic upgrade head
conda run -n course-nexus python -m pytest tests/modules/task_test_attempts -q
conda run -n course-nexus python -m pytest tests/integration/test_task_test_attempt_flow.py tests/modules/learning_execution tests/modules/checkins -q
```

预期：全部退出码 0；无 live OpenAI；失败路径不产生半截数据；提交测试题不改变任务完成和打卡。

## 5. 验收标准

### 自动化

- [ ] migration 能从空库升级到 head。
- [ ] task_test attempt 和 answer 字段、索引、外键测试通过。
- [ ] 四类题型作答保存和客观题判分通过。
- [ ] 多次提交保留历史，latest 稳定返回最新提交。
- [ ] 权限、状态、schema 和答案格式错误均有稳定错误码。
- [ ] 提交作答不改变任务完成状态、计划状态或打卡记录。

### 人工

- [ ] 学生完成一份 5 题测试后能看到分数、正确题数、答案解析。
- [ ] 简答题能保存学生输入，但界面不声称已自动判分。
- [ ] 刷新后可以看到最近一次作答结果。
- [ ] 再次提交会新增一条历史记录，旧记录仍可查看。
- [ ] 第二个用户不能查看或提交别人的测试题。

## 6. 交付物

- task-test-attempts 后端模块、migration、API 和三组测试。
- API、数据模型、表结构、模块边界、运行流程和当前状态文档。
- `docs/domains/study-mode/task-test-attempts.md` 中文领域实现文档。
- `docs/planning/phase-1-validation/S08-task-test-attempts.md` 中文验收记录。
- 建议提交：
  - `feat(task-test-attempts): 新增作答记录表`
  - `feat(task-test-attempts): 支持客观题提交与判分`
  - `test(task-test-attempts): 覆盖作答历史和权限`
  - `docs(study-mode): 同步任务测试题作答文档`

## 7. 文档同步

- 新建 `docs/domains/study-mode/task-test-attempts.md`：记录模块分层、代码入口、数据流、判分算法、事务边界、复杂度、失败回滚和测试证据。
- 更新 `docs/api-data/contracts.md`：新增提交、历史、latest 和详情接口契约。
- 更新 `docs/api-data/table-schema.md` 与 `data-model.md`：记录新增两张表和字段语义。
- 更新 `docs/architecture/module-boundaries.md`：明确 `task-test-attempts` 只消费 S06 生成内容，不调用生成器。
- 更新 `docs/architecture/runtime-flows.md`：补充“生成测试题 -> 提交作答 -> 查看结果”的流程。
- 更新 `docs/planning/current-state.md` 和阶段验收记录。

## 8. 冲突与注意事项

### 严格遵循

- S08 只消费成功的 `task_test` 内容，不重新生成题目。
- 作答记录必须绑定当前用户、课程、生成内容和二级任务。
- 客观题判分必须基于提交时的题目快照，避免后续重新生成影响旧记录。
- 简答题第一版只保存，不调用模型评分。
- 新增 migration 前必须确认数据库表名、字段和索引，避免和 S01/S07 的“不新增表”口径混淆。

### 一定不能做

- 不能把学生答案写回 `ai_generated_contents.content_json`。
- 不能把提交作答自动等同于完成二级任务或打卡。
- 不能为简答题伪造自动分数。
- 不能新增前端页面或 PDF 导出逻辑。
- 不能调用 live 大模型完成自动化测试。

## 9. 完成检查表

- [ ] 产品口径确认：一次性提交、多次历史、客观题自动判分、简答题仅保存。
- [ ] migration、模型、API、service、测试和 docs 全部完成。
- [ ] 与 S06/S07 的边界清楚：S06 生成，S08 作答，S07 导出。
- [ ] Alembic、模块测试、集成测试和 `git diff --check` 通过。
- [ ] 未提交 `backend/uv.lock` 或其他本地临时文件。
