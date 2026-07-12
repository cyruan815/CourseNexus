# Study Mode 未完成优先级清单

## 读法

- 本文是给后续开窗口派活用的，不是 PRD 重述。
- 这里的编号是**新排序**，不沿用旧清单里的 P0/P1/P2 语义。
- 旧清单里的 P0 `diagnostic_profile -> planner`、P2 `capacity / warning` 已经不再排队。
- 新排序里的 P1 `学习方式 preference 派生配置落地` 已完成，未完成项暂不整体重排，避免后续窗口引用漂移。
- `handout / task_test` 的“最近一次 success 复用 + `force_regenerate=true` 重建”已经是现有默认行为；如果后面还要加显式 `Idempotency-Key`，应单独算增强项，不要和当前默认幂等混成一件事。
- 凡是会改 API、schema、数据契约、migration 或长期文档的任务，都要同步更新 `docs/`，必要时先确认 owner。

## 协作必做规则

- 每完成一个需求、优先级项或可验证子任务，必须同步更新本文对应条目的状态，写清“已完成 / 部分完成 / 剩余事项”、完成日期、验证命令和关键 commit。
- 如果只是完成了其中一部分，不得把整项标成已完成；应在该条目下新增“已完成”和“仍待处理”两段，避免后续窗口误判。
- 如果调整下一步、拆分任务、改变优先级或变更 owner，必须同步更新本文的状态、限制和并行建议；不要只把决策留在聊天记录里。
- 如果任务涉及 API、schema、数据契约、migration、模块边界或长期实现口径，除本文外，还必须同步更新 `docs/api-data/`、`docs/architecture/` 或 `docs/domains/study-mode/` 中的对应文档。
- 提交前必须确认没有带入其他窗口的未跟踪文件或未完成改动；当前已知 P0 窗口产物和 `backend/uv.lock` 不应被无关任务顺手提交。

## 2026-07-13 派活 / owner 审计

- 当前用户窗口定位为后端 API、接口契约、测试和文档同步；不承担前端页面、前端组件或前端样式实现。
- `P0：S06 任务测试题生成闭环` 仍归正在运行的 P0 窗口收尾；未拿到最终完成报告前，其他窗口不要修改 `task_test` generator、`learning_execution` 主链路或相关测试。
- `P2：任务测试题轻量只读版` 的 UI / renderer 属于前端 owner；当前用户最多只补后端接口、API 契约和文档，不做前端实现。
- `P6：保存请求强制 tasks 的新向导口径收紧` 已完成；当前用户窗口仍定位为后端 API、接口契约、测试和文档同步，不接前端 UI / renderer。
- `P3：讲义 / task_test 请求级幂等增强` 等 P0 完成后再评估；它会触达 handout/task_test 生成入口，当前不作为第二窗口首选。
- `P5：资料解析诊断接入 Study Mode warning / 阻断策略` 可后续做后端调研或接口设计，但它跨 materials/parser 和 Study Mode，范围大于 P6。
- `P10：重生成 preview 配置合并修复` 是后端 plan lifecycle 小修复，可由当前后端窗口优先处理；不触碰 P0/P2/P3 的生成和展示链路，优先级高于 P7/P8/P9。
- `P7`、`P8`、`P9` 都需要单独评审；其中 P7 涉及 schema / migration，P9 涉及新作答数据结构，不应作为当前最小下一步。

## 已完成，不再排队

### P1：学习方式 preference 派生配置落地

状态：已完成。

已落地：

- 把 `fast_track / balanced / mastery / sprint` 派生成 planner 可用的底层策略。
- 明确 `content_depth / example_intensity / assessment_intensity / review_intensity` 的映射。
- 与 `diagnostic_profile` 合并后，真正影响计划的详细程度、例题强度、测试强度和 review 强度。
- 继续保留“基础薄弱时，即使 fast_track 也要补基础”的规则。
- 已补测试，证明不同 preference 的计划强度不同。

后续只保留文档校正：

- 若发现 `plan-builder-wizard.md`、API 契约或 current-state 仍有旧口径，归入 P4 文档校正，不再作为功能任务排队。

### P6：保存请求强制 tasks 的新向导口径收紧

状态：已完成。

完成日期：2026-07-13。

关键 commit：`ca9697038111e2f1356e19da4222f2775647b663`（`feat(study-mode): 收紧新向导保存 tasks 契约`）。

复核补丁：`0c84bf942190cfcff1646f64598f9aecfdfb1434`（`fix(study-mode): 兼容 legacy 保存幂等 hash`），处理新增默认 `client_flow = "legacy"` 后旧版幂等 `request_hash` 重放可能误判冲突的问题。

验证：

- `uv run python -m pytest tests/modules/study_plans/test_study_plan_quality.py tests/modules/study_plans/test_study_plan_lifecycle_api.py -q`：`37 passed in 15.48s`。
- `uv run python -m pytest tests/modules/study_plans/test_study_plan_quality.py tests/modules/study_plans/test_study_plan_lifecycle_api.py tests/modules/study_plans/test_study_plan_lifecycle.py -q`：`72 passed in 17.14s`，额外覆盖 legacy idempotency hash 兼容。

已落地：

- `StudyPlanSaveRequest.client_flow` 增加稳定枚举字段，默认 `legacy`，支持 `wizard_v1`。
- 旧客户端不传 `client_flow` 且不传 `tasks` 时继续走保存前生成 preview 的兼容路径。
- 新向导传 `client_flow = "wizard_v1"` 时必须提交 preview 中确认后的非空 `tasks`；缺失或空数组返回 `422 PREVIEW_TASKS_REQUIRED`，不会进入兼容 preview 生成。
- 新向导提交合法 exact tasks 时正常保存，`parsed_config_json.tasks_source = "confirmed"`。
- 已同步 `docs/api-data/contracts.md`、`docs/api-data/frontend-integration.md` 和 `docs/domains/study-mode/plan-lifecycle.md`。

限制确认：

- 未改数据库，未新增 migration，未做前端页面、组件或样式。
- 未触碰 P0 的 `task_test` generator、`learning_execution` 主链路或相关测试。


### 轻量化 T2：今日讲义 PDF 导出

状态：已完成。

完成日期：2026-07-13。

关键 commit：本次 T2 提交（`feat(study-mode): 支持今日讲义 PDF 导出`）。

验证：

- `uv run python -m pytest tests/modules/exports tests/modules/learning_execution/test_task_content_api.py -q`：`32 passed in 6.50s`。

已落地：

- 新增 `GET /api/v1/generated-contents/{generated_content_id}/exports/pdf`，只支持当前用户自己的成功 `handout`，返回 `application/pdf` 文件流。
- PDF 文件名为 `handout-{generated_content_id}.pdf`，不保存导出历史，不新增 `export_records`。
- `task_test` 调用 PDF 返回 `EXPORT_UNSUPPORTED_CONTENT_TYPE`；测试题轻量阶段继续使用 Markdown 导出。
- 已覆盖成功导出、跨用户不可导出、`task_test` 不支持、非 success 不可导出、畸形 handout 不导出、renderer 失败返回 `EXPORT_FAILED`。

限制确认：

- 未新增 migration，未新增业务表，未引入新依赖。
- 导出不修改二级任务完成状态，不写 `checkin_records`。

## 新的未完成优先级

### P0：S06 任务测试题生成闭环

状态：最高优先级。

目标：

- `question_count` 必须变成最终硬约束，不是 prompt 建议。
- 多材料批次时，必须先汇总候选知识点，再统一生成固定 `N` 道题，不能每个 batch 都各出一套完整题再直接拼接。
- 最终题目总数必须严格等于请求值，不能多、不能少。
- `question_types` 只能来自请求白名单。
- 题目 `id`、`sort_order` 必须连续且唯一。
- 题型内部结构必须自洽：选择题 options id 唯一且答案命中选项，多选答案格式稳定，判断题答案格式稳定，简答题不要求 options。
- 要做重复题 / 高相似题的去重或拒绝。
- 所有题目的引用必须落在**当天 / 当前二级任务**允许的内容范围内，不能把后续材料内容混进来。
- 如果无法同时满足题量、题型、覆盖或引用要求，必须返回明确错误，不能悄悄截断。
- 如果业务口径确认要求“每天最后一个二级任务必须是测试”，planner 也要补这个日内约束，不要只保证“最后一天有综合自测”；未确认前不要把它当硬规则实现。

限制：

- 现在只保存 `related_material_ids_json`，不足以锁定测试范围；如果要保留 chunk 级范围，可能需要补字段、补追溯 JSON，甚至补 migration，先确认再开工。
- `learning_execution`、`task_test` generator、相关测试要一起改，但不要和 P1 共用同一个窗口。

### P2：任务测试题轻量只读版

状态：部分完成。后端 Markdown 导出已完成；前端执行页只读展示仍待前端 owner 接入。

后端已完成：

- 完成日期：2026-07-13。
- 新增 `GET /api/v1/generated-contents/{generated_content_id}/exports/markdown`，只支持当前用户自己的成功 `task_test`，返回 `text/markdown; charset=utf-8` 文件流。
- Markdown 输出包含标题、instructions、题目、选项、正确答案、解析和引用来源；引用只匹配 `source_citations[].id`，缺失时写 `Sources: unavailable`，不伪造来源。
- 已覆盖成功导出、跨用户不可导出、非 `task_test` 不支持、非 success 不可导出、畸形 `content_json` 不导出、引用缺失兜底。
- 验证：`uv run python -m pytest tests/modules/exports tests/modules/generated_content tests/modules/learning_execution/test_task_content_api.py -q`。
- 关键 commit：本次 T1 提交（`feat(study-mode): 支持任务测试题 Markdown 导出`）。

目标：

- 直接复用现有 `task_test.content_json` 展示题干、选项、正确答案、解析和引用来源。
- 只读展示，不保存学生作答，不改完成状态，不做判分。
- 刷新后通过 `GET /api/v1/study-subtasks/{subtask_id}/execution-context` 拿最近一次成功生成的 `task_test_content_id`。
- 再用 `GET /api/v1/generated-contents/{generated_content_id}` 读取 `GeneratedContentRead` 详情并渲染。
- 如果当前没有 `task_test_content_id`，可提供轻量生成入口，调用现有 `POST /api/v1/study-subtasks/{subtask_id}/task-tests`；生成成功后直接渲染返回内容。
- `source_citation_ids` 只和响应里的 `source_citations` 做匹配展示，找不到时显示引用缺失兜底，不伪造来源。
- 对未知题型、畸形 `content_json`、空 questions、failed record 和 loading/error 状态做防御性展示，不让执行页白屏。

限制：

- 这个任务依赖 P0 的生成正确性先稳定，否则展示层会把错误内容“放大”给前端。
- UI / renderer 属于前端 owner；当前用户窗口不实现前端组件，只能在需要时补后端接口、API 契约和文档。
- 不新增后端 API、schema、migration 或新的业务表。
- 不新增 `task_test_attempts / task_test_answers`。
- 不引入“提交答案”“隐藏正确答案”“得分统计”“历史 attempts”等作答反馈语义；这些都归 P9。

### P3：讲义 / task_test 请求级幂等增强

状态：可选增强，不是当前默认行为的主 bug。

目标：

- 如果团队决定要显式防重复提交，就让 `handout / task_test` 读取并使用 `Idempotency-Key`。
- 同 key 同请求返回同一结果，同 key 不同请求返回明确冲突。
- 失败记录不阻止重试。

说明：

- 现有“最近一次 success 复用”已经够 POC 用；这条是为了把 review 里提到的“没有 request-level 防重”收口干净。
- 如果短期不做，应该在文档里明确写成已知增强项，不要让后来的人误判成 bug。

### P4：docs / API 契约校正

状态：穿插做，但要保持口径一致。2026-07-12 已先校正稳定 API 前缀、诊断/capacity/S06 当前状态和 P2/P9 未完成边界；P0 / P2 的最终实现细节仍等对应任务完成后再同步。

目标：

- 校正 Study Mode 相关文档里的 `/api/v1` 路径。
- 把“诊断接口待验证”改成“已验证”。
- 把“测试题内容生成未完成”改成“轻量只读展示未完成 / 作答反馈后续做”。
- 把旧文档里残留的 capacity “待补强”口径改成“诊断后 capacity 闭环已实施”；如果还缺前端 warning 展示，单独写成前端展示缺口。
- 确认 P1 已完成文档不再漂移，并把 P0 / P2 的最终实现同步写进 `docs/domains/study-mode/`。

限制：

- 文档改动最好跟对应功能同一批提交，避免再次漂移。

### P5：资料解析诊断接入 Study Mode warning / 阻断策略

状态：部分完成。P5a（preview warning）已落地；阻断策略仍待后续拆分。

完成日期：2026-07-13。

关键 commit：本次 P5a 提交（`feat(study-mode): 接入资料解析质量 warning`）。

验证：

- `uv run python -m compileall app/modules/material_context app/modules/study_plans/service.py`：通过，覆盖 touched 后端模块语法检查。
- `uv run python -m pytest tests/modules/material_context/test_material_context_batches.py tests/modules/study_plans/test_study_plan_foundation.py -q`：`10 passed in 2.00s`，覆盖 material-context 解析质量摘要、Study Mode preview metadata 接入，以及解析 warning 不进入 `capacity.warnings`。

P5a 已落地：

- `material-context` 增加当前 `MaterialScope` 内 parsed 资料的解析质量摘要读取能力。
- Study Mode preview 将 `parse_quality = partial / unknown` 和 `parse_diagnostics_json.warnings[].severity = warning` 映射到 `generation_metadata.material_quality.warnings`。
- `severity = info` 的 parser 诊断不升级为 warning。
- 不新增 migration，不改变公开请求字段，不做前端。
- 保留现有 `NO_PARSED_MATERIAL` / `MATERIAL_COVERAGE_INCOMPLETE` 阻断语义；P5a 不收紧显式非 parsed 资料行为。

仍待处理：

- 低质量资料是否阻止 plan preview、哪些诊断需要 block、是否需要前端交互提示，另拆 P5b 评审。
- 若后续 block 策略需要新错误码、API schema 或数据库字段，需单独确认 owner 和 migration/API 契约。

限制：

- 这是 materials/parser 和 Study Mode 的跨域能力，不要插进 P0-P3 的主链路里一起做。

### P10：重生成 preview 配置合并修复

状态：已完成。

完成日期：2026-07-13。

关键 commit：`e06314c87d2e5feba64fa9b50ef2dd2ce0684958`（`fix(study-mode): 修复重生成 preview 配置合并`）。

验证：

- `uv run python -m pytest tests/modules/study_plans/test_study_plan_lifecycle.py tests/modules/study_plans/test_study_plan_lifecycle_api.py -q`：`50 passed in 19.26s`。

已落地：

- `POST /api/v1/study-plans/{plan_id}/regeneration-previews` 现在先合并已保存配置，再应用请求覆盖项。
- 请求未传 `diagnostic_profile` 时继承保存计划中的诊断 profile；显式传入新 profile 时覆盖，避免诊断后的补基础、弱项和解释风格在重生成时失效。
- 请求只传 `duration_days` 时，后端基于保存的 `start_date` 或请求覆盖后的 `start_date` 重新推导 `end_date`，不再复用旧 `end_date` 造成范围冲突。
- 已补 service 和 API 覆盖，证明 profile 继承、profile 覆盖、只改学习天数和 preview 不写数据库。
- 已同步 `docs/domains/study-mode/plan-lifecycle.md`、`docs/api-data/contracts.md` 和 `docs/api-data/frontend-integration.md`。

限制确认：

- 未触碰 `task_test` generator、`learning_execution` 主链路或 P0 相关测试。
- 未改数据库，未新增 migration。

### P7：version 乐观锁改造

状态：工程增强。

目标：

- 增加独立 `version` 字段。
- 每次替换递增 version。
- 用 `expected_version` 做并发控制。
- 更新 API 和 docs。

限制：

- `expected_updated_at` 现在能顶住第一阶段冲突控制，但 SQLite 的时间精度确实让它不够稳，version 是更扎实的解法。

### P8：异步 preview / preview_id / wizard draft

状态：后置。

目标：

- 异步生成 preview。
- 持久化 preview 草稿。
- 返回 `preview_id`。
- 保存时引用 preview。
- 支持 stale 状态和跨设备恢复。

限制：

- 同步 preview 第一版先够用，只有模型调用变慢或需要跨设备恢复时再上。

### P9：任务测试题作答、判分和反馈闭环

状态：后续增强。

目标：

- 学生提交答案。
- 客观题自动判分。
- 简答题保存答案并标记待 review。
- 保存 attempt 历史。
- 查询最近一次 attempt 和历史 attempts。
- 返回得分、正确数、解析和引用。

限制：

- 这条明显需要新数据结构和单独评审，不要和 P2 的只读展示混着做。

## 并行建议

当前不再推荐 `P0 + P1` 并行，因为 P1 已完成。后续派活建议：

- `P0：S06 任务测试题生成闭环` 先独立推进，稳定后再接 `P2：任务测试题轻量只读版`。
- 如果要开第二个窗口，可单独做 `P4：docs / API 契约校正`，但要提前锁定具体文档 owner，避免和 P0/P2 同时改同一份 `docs/domains/study-mode/*.md`。
- `P10：重生成 preview 配置合并修复` 可作为当前后端窗口的合并前小修复优先处理，文件范围应限定在 study plan lifecycle 后端、测试和必要文档。
- `P5：资料解析诊断接入 Study Mode warning / 阻断策略` 可后续并行调研，但不要插进 P0-P3 的主链路。

P2 依赖 P0 的生成正确性，不建议和 P0 同时作为正式展示任务并行；最多可先做静态 renderer / mock 数据验证。
