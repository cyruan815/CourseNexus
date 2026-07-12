# Study Mode 未完成优先级清单

## 读法

- 本文是给后续开窗口派活用的，不是 PRD 重述。
- 这里的编号是**新排序**，不沿用旧清单里的 P0/P1/P2 语义。
- 旧清单里的 P0 `diagnostic_profile -> planner`、P2 `capacity / warning` 已经不再排队。
- 新排序里的 P1 `学习方式 preference 派生配置落地` 已完成，未完成项暂不整体重排，避免后续窗口引用漂移。
- `handout / task_test` 的“最近一次 success 复用 + `force_regenerate=true` 重建”已经是现有默认行为；如果后面还要加显式 `Idempotency-Key`，应单独算增强项，不要和当前默认幂等混成一件事。
- 凡是会改 API、schema、数据契约、migration 或长期文档的任务，都要同步更新 `docs/`，必要时先确认 owner。

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

状态：POC 展示层任务，偏前端执行页接入。

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

状态：穿插做，但要保持口径一致。

目标：

- 校正 Study Mode 相关文档里的 `/api/v1` 路径。
- 把“诊断接口待验证”改成“已验证”。
- 把“测试题内容生成未完成”改成“轻量只读展示未完成 / 作答反馈后续做”。
- 把旧文档里残留的 capacity “待补强”口径改成“诊断后 capacity 闭环已实施”；如果还缺前端 warning 展示，单独写成前端展示缺口。
- 确认 P1 已完成文档不再漂移，并把 P0 / P2 的最终实现同步写进 `docs/domains/study-mode/`。

限制：

- 文档改动最好跟对应功能同一批提交，避免再次漂移。

### P5：资料解析诊断接入 Study Mode warning / 阻断策略

状态：后续接入。

目标：

- 计划生成时识别资料解析质量问题。
- 对低质量资料返回 warning。
- 必要时阻止计划生成或提示重新上传。
- 将 `parse_diagnostics_json` 映射到 Study Mode warning。
- 明确哪些问题是 warning，哪些问题是 block。

限制：

- 这是 materials/parser 和 Study Mode 的跨域能力，不要插进 P0-P3 的主链路里一起做。

### P6：保存请求强制 tasks 的新向导口径收紧

状态：可等前端更稳定后再收。

目标：

- 区分旧客户端和新向导请求。
- 新向导强制提交 preview tasks。
- 缺少 tasks 时返回 `PREVIEW_TASKS_REQUIRED`。
- 旧客户端可以继续兼容，或者明确宣布废弃窗口。

限制：

- 当前兼容行为不是 bug，别把它和 P0 的正确性问题混在一起。

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
- `P5：资料解析诊断接入 Study Mode warning / 阻断策略` 可后续并行调研，但不要插进 P0-P3 的主链路。

P2 依赖 P0 的生成正确性，不建议和 P0 同时作为正式展示任务并行；最多可先做静态 renderer / mock 数据验证。
