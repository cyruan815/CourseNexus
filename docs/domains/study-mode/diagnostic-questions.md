# Study Mode 学前诊断题 v2

## 状态

- 日期：2026-07-13
- 状态：后端接口、模型 purpose 和文档契约已更新；`confirmed_config` 已明确为自然语言解析后经开始前设置补齐/确认的有效配置。V1 发布验收已使用真实 Provider 完成计划预览与保存，诊断题的专项语义质量继续按真实课程材料抽查，不再作为“任务七”占位项。
- 范围：`study-plan-diagnostic-questions` 题目生成、`study-plan-diagnostic-profiles` 诊断归纳、模型配置、前端接入边界和失败补偿。
- 非范围：开始前设置页 UI、配置补问 UI、计划 preview 生成、讲义/测试题正文生成、诊断 session 持久化。

## 产品边界

前端可以把配置补问、学前诊断、薄弱方向和可选补充放在同一个“开始前设置”页面里，但后端职责保持拆分：

- `study-plan-config-parses` 只负责自然语言配置回填和缺失字段提示，不生成诊断题。
- 前端在“开始前设置”页顶部用 `unresolved_field_prompts`、`needs_confirmation_field_prompts` 和 `field_options` 让用户补齐或确认关键配置字段。
- `study-plan-diagnostic-questions` 只根据补齐后的有效配置和资料内容生成诊断题，不补问学习设置。
- `study-plan-diagnostic-profiles` 只把诊断答案归纳为 preview 可使用的 profile，不调用模型。
- `study-plans/preview` 接收补齐后的有效配置和 `diagnostic_profile`，再生成计划任务。

v2 不再提供“讲课风格”用户选择项。用户只回答“你最担心哪类内容？”即 `weak_area`。后端仍可为了兼容现有 planner 从 `weak_area` 派生内部 `explanation_style`，但前端不需要把它展示成讲课风格控件。

## 接口入口

### 生成诊断题

`POST /api/v1/courses/{course_id}/study-plan-diagnostic-questions`

请求体。`confirmed_config` 是后端 API 字段名，表示“自然语言配置解析结果 + 用户在开始前设置页补齐/确认后的有效配置”，不是独立配置确认页产物：

```json
{
  "goal_text": "我想三天深度掌握物理层",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  },
  "confirmed_config": {
    "start_date": "2026-07-13",
    "duration_days": 3,
    "preference": "mastery",
    "daily_available_minutes": null,
    "daily_minutes_source": null
  }
}
```

响应固定为 5 个问题：

- 3 个 required `topic_mastery`。
- 1 个 required `weak_area`。
- 1 个 optional `diagnostic_note`。

所有用户可见问题、选项、问题类型标签和输入占位文案都必须是中文。`question_type`、`topic_id`、`mastery_level`、`weak_area` 等字段仅作为机器契约使用；前端展示时使用 `question_text`、`question_type_label`、`options[].label` 和 `placeholder`。

`question_version` 固定为 `study_plan_diagnostic_v2`。`generation_metadata.diagnostic_questions.source` 表示 `model` 或 `fallback`，`fallback_reason` 记录模型失败、输出不足、输出越界或补足原因。

### 归纳诊断 profile

`POST /api/v1/courses/{course_id}/study-plan-diagnostic-profiles`

请求体必须提交 exactly 3 个 `topic_mastery` 答案，且 `topic_id` 不得重复。后端重新基于当前 `material_scope` 和题目中的 `topic_title` 计算合法 topic id；版本过期或 topic 不再匹配时返回 `409 DIAGNOSTIC_STALE`。

归纳规则：

- `none` / `heard` 计为弱掌握。
- 弱掌握超过一半时 `foundation_needed=true`。
- `weak_topics` 保留弱掌握 topic id。
- `weak_area=calculation` 内部派生 `step_by_step`，`application` 派生 `example_first`，`memorization` 派生 `exam_focused`，其余为 `plain_language`。

## 模型配置

新增模型 purpose：`study_plan_diagnostic`。

对应环境变量：

```env
STUDY_PLAN_DIAGNOSTIC_API_KEY=
STUDY_PLAN_DIAGNOSTIC_BASE_URL=
STUDY_PLAN_DIAGNOSTIC_MODEL=deepseek-flash
```

配置读取沿用 `Settings.model_endpoint(purpose)` 和 `ModelProvider.generate_structured()`，不得复用 planner、parser 或 task-test 的密钥配置。

## Prompt 职责

诊断 prompt 的职责是选择资料内主题候选，不生成最终前端问题列表。

固定职责：

```text
你是 CourseNexus 的学前诊断题生成器。
你的任务是根据用户学习目标和选定课程资料，生成用于了解学生当前基础的诊断问题。
你不生成学习计划，不问学习偏好，不估算学习时间，不生成考试题。
```

输入包含：

- `goal_text`
- `confirmed_config`：自然语言解析后经开始前设置补齐/确认的有效配置
- `material_scope`
- 当前资料范围内的 chunk excerpts、heading、material name、page 信息

模型结构化输出只包含 topic 候选：

```json
{
  "topics": [
    {
      "topic_title": "Nyquist / Shannon 公式",
      "diagnostic_value": "能区分是否理解公式适用条件和计算场景",
      "question_text": "你对「Nyquist / Shannon 公式」了解多少？",
      "source_chunk_id": "chunk_xxx"
    }
  ]
}
```

规则：

- 必须生成 3 个 topic 候选。
- 优先选择对计划生成有诊断价值的核心主题，不机械取前 3 个 heading。
- 不出知识测验题，不问“公式是什么”。
- 不问学习方式、每日时间、资料范围。
- topic 必须来自资料内容，不得编造资料外主题。
- 题目文案统一由后端组装为“你对「topic」了解多少？”。
- 资料较少时，允许从同一 chunk 拆出 3 个偏泛但仍然资料内的主题。
- 后端固定补 `weak_area` 和 `diagnostic_note`，模型不负责这两题。

## 后端算法

```text
validate course/user/material_scope
  -> receive goal_text + confirmed_config(effective config from setup)
  -> iter_material_context_batches()
  -> call study_plan_diagnostic model for topic candidates
  -> normalize titles and map each topic back to current chunks
  -> dedupe by topic_id/title
  -> if fewer than 3, fallback from model seeds + headings + excerpts + first chunk split
  -> build 3 topic_mastery + weak_area + diagnostic_note
```

不变量：

- 返回给前端的 `topic_mastery` 永远是 3 道。
- `topic_id` 由后端基于 `material_id + chunk_id + topic_title` 确定性生成，模型不能指定最终 id。
- 题目生成和 profile 归纳不写数据库，不新增诊断 session 表。
- profile 阶段不再次调用模型，只校验当前资料范围是否仍能匹配答案 topic。

复杂度与资源预算：

- 题目生成正常路径调用 1 次结构化模型。
- chunk 读取沿用 `material_batch_max_tokens` 控制输入规模，每个 prompt excerpt 截取到有限长度。
- topic 校验和 fallback 为 O(chunks + fragments)，最多返回 3 个 topic。
- 不写数据库，因此失败不会产生部分状态，需要前端重试即可。

## 失败与补偿

| 场景 | 行为 |
| --- | --- |
| 当前资料范围没有 parsed chunk | 返回 `NO_PARSED_MATERIAL`。 |
| 资料范围越权或不存在 | 沿用 material-context 的权限/范围错误。 |
| 模型调用失败 | 使用 fallback 补足 3 道 topic，metadata 记录 `source=fallback`。 |
| 模型输出不足 3 个 topic | 保留可映射 topic，并用 fallback 补足 3 道。 |
| 模型输出资料外 topic | 丢弃越界 topic；不足 3 道时 fallback。 |
| profile 版本或 topic 不匹配 | 返回 `DIAGNOSTIC_STALE`，前端重新获取诊断题。 |

## 测试入口

手动全流程脚本：`backend/scripts/run_study_mode_manual_plan_flow.py`。默认使用 `D:\大二下课程\计算机网络\课件\Chap7 物理层.pdf`，在隔离 DB 中按“上传资料 -> 解析 -> 配置回填 -> 确认配置 -> 诊断题 -> 诊断 profile -> preview -> 可选保存”的顺序运行，并在每个关键节点写出可编辑 JSON。

任务七自动化测试仍待补充。密钥配置后建议补充：

- schema/API 测试：exactly 3 topic、重复 topic_id 拒绝、v2 版本、metadata fallback。
- service 测试：模型正常输出、输出不足、输出越界、模型失败 fallback。
- profile 测试：合法 topic 通过，资料范围变化返回 `DIAGNOSTIC_STALE`。
- 真实模型验证：使用物理层资料确认题目来自资料且不机械取前 3 个 heading。
