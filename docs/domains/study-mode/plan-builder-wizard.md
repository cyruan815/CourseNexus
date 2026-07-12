# Study Mode 计划生成向导设计

## 状态

- 日期：2026-07-12
- 状态：设计已确认，待实施。
- 范围：从用户点进学习计划生成开始，到配置确认、学前诊断、计划 preview、确认保存和进入计划详情为止的前端页面流、配置字段、学前诊断、后端契约和状态失效规则。

## 目标

计划生成向导要把“用户想怎么学”和“用户现在会多少”分开处理。

- 配置确认回答“用户想怎么学”。
- 学前诊断回答“用户现在会多少”。
- 计划 preview 基于配置和诊断共同生成。
- 确认保存时，保存用户实际看到并确认的 preview 任务，不重新生成另一份计划。

## 非目标

- 不在本任务中实现资料解析漏页、OCR 降级或 material diagnostics。
- 不在本任务中实现正式任务讲义、测试题或 review 内容生成，只为后续生成提供配置和诊断输入。
- 不把讲义详细程度、例题数量、测试数量作为前端主界面独立选项。
- 第一版不实现异步 preview 任务队列，也不引入独立持久化的 `preview_id`。

## 总体方案

第一版采用方案 A：

- preview 不单独入库，也不返回长期有效的 `preview_id`。
- 前端在保存时提交“用户刚刚看到的任务列表 + 确认后的配置 + 诊断 profile + 资料快照标识”。
- 后端保存新流程提交的 exact preview tasks，不在保存接口里重新调用大模型生成计划。
- 旧客户端如果没有提交 tasks，可以保留原有保存时生成的兼容路径；新向导必须提交 tasks。
- 保存接口需要幂等保护，避免用户连续点击导致重复计划。

## 页面流

推荐使用同一页面内的轻量步骤状态，而不是多个孤立页面或重弹窗。

```text
/courses/:courseId/study-plans/new

goal_input
  -> config_review
  -> diagnostic
  -> preview
  -> saved plan detail
```

前端可展示轻量步骤条：

```text
输入目标 / 确认配置 / 学前诊断 / 计划预览
```

这里的 stepper 是页面内的进度提示和状态机，不是独立路由。用户能看到当前处在哪一步，但页面主体仍是同一个计划生成工作流。

## Step 1：输入目标和选择资料

用户在第一步完成自然语言输入、资料勾选或资料上传。

页面职责：

- 输入学习目标。
- 选择参与计划生成的资料范围。
- 上传新资料后，等待资料解析状态满足计划生成要求。

前端提交：

```json
{
  "goal_text": "我要两天学完计网第七章，今天是2026年7月12日",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  }
}
```

后端调用：

```text
POST /courses/{course_id}/study-plan-config-parses
```

资料范围约束：

- 只能使用当前课程、当前用户有权限访问且解析完成的资料。
- `material_ids` 需要去重，且不能为空。
- `include_all_parsed_materials=true` 表示使用当前课程下“此刻已解析完成”的资料集合，后续新上传资料不会自动改变已生成计划的范围。
- 资料处于 parsing、failed 或不属于当前课程时，不能进入下一步，需要给出明确提示。

## Step 2：配置确认

配置确认页展示 5 个字段：

```text
学习目标
学习日期 / 学习天数
每日学习时间
学习方式
资料范围
```

资料范围可以修改，但它不是普通本地字段。资料范围变化后必须重新解析配置并重新估算学习时间，因为资料范围影响知识点数量、预计总学习时长、学前诊断题目和最终计划内容。

### 前端展示字段

| 字段 | 是否可编辑 | 说明 |
| --- | --- | --- |
| `goal_text` | 是 | 用户学习目标，可保留自然语言解析后的目标。 |
| `start_date` / `duration_days` | 是 | 用户可改开始日期或学习天数。后端按本地日期计算 `end_date`。 |
| `daily_available_minutes` | 是 | 每日学习时间永远展示且可改。 |
| `preference` | 是 | 学习方式：快速、均衡、深入、冲刺。 |
| `material_scope` | 是 | 可重新选择资料；修改后触发重新解析和重新估算。 |

日期来源规则：

- 请求中以 `start_date + duration_days` 作为唯一可编辑来源。
- `end_date = start_date + duration_days - 1` 由后端按用户本地日期计算。
- 响应可以同时返回 `start_date`、`duration_days` 和 `end_date`，供前端展示。

### 每日学习时间规则

每日学习时间需要区分“系统建议值”和“最终采用值”。

```json
{
  "recommended_daily_minutes": 90,
  "daily_available_minutes": 60,
  "daily_minutes_source": "user_modified",
  "estimated_total_minutes": 180,
  "available_total_minutes": 120,
  "feasibility_status": "tight"
}
```

字段含义：

| 字段 | 说明 |
| --- | --- |
| `recommended_daily_minutes` | 系统根据资料内容量、学习天数和最低时长估算出的建议每日分钟数。 |
| `daily_available_minutes` | 最终采用的每日学习时间，前端始终展示且允许用户修改。 |
| `daily_minutes_source` | `user_text`、`system_estimated` 或 `user_modified`。 |
| `estimated_total_minutes` | 当前资料范围和学习方式下的预计总学习分钟数。 |
| `available_total_minutes` | `daily_available_minutes * duration_days`。 |
| `feasibility_status` | `ok`、`tight` 或 `over_capacity`，用于提示时间是否充足。 |

如果用户自然语言中明确说了每天学多久：

```text
daily_available_minutes = 用户输入的分钟数
recommended_daily_minutes = 系统根据资料估算出的建议值
daily_minutes_source = user_text
```

如果用户没有说明每天学多久：

```text
recommended_daily_minutes = max(30, ceil(资料总预计学习分钟数 / 学习天数))
daily_available_minutes = recommended_daily_minutes
daily_minutes_source = system_estimated
```

用户在前端手动修改后：

```text
daily_available_minutes = 用户修改值
daily_minutes_source = user_modified
```

最低每日学习时间为 30 分钟。该值是系统底线，不作为前端主配置项展示；低于 30 分钟时前端应阻止提交，后端也要校验。

### 资料范围变化后的字段保留规则

资料范围变化后，前端重新调用配置解析 / 估算接口。字段合并规则：

```text
用户手动修改过的学习目标、日期、学习方式、每日学习时间优先保留。
系统估算字段可以被新结果覆盖。
如果每日学习时间是 user_modified，则保留用户值，同时展示新的系统建议值。
```

示例提示：

```text
资料范围已变化。根据新资料，系统建议每日学习 90 分钟；你当前保留的是 60 分钟。
```

## 学习方式

前端只展示 4 个用户可理解的学习方式：

| 前端文案 | 后端值 | 说明 |
| --- | --- | --- |
| 快速 | `fast_track` | 快速过一遍，轻讲义、少测试。 |
| 均衡 | `balanced` | 默认学习方式，讲义、例题、测试适中。 |
| 深入 | `mastery` | 更详细讲义，更多例题、review 和阶段测试。 |
| 冲刺 | `sprint` | 面向复习/备考，强调重点回顾、易错点和测试。 |

`sprint` 是新写入值。当前后端已有 `advanced` 枚举值，实施时需要兼容读取历史 `advanced`，并在展示和新写入时映射为 `sprint`。历史数据迁移可后续单独处理。

### 学习方式说明文案

配置确认页和 preview 页都要展示一段自然语言说明。

快速：

```text
会优先提炼核心概念和重点结论，减少长讲义和复杂测试，适合快速建立框架。
```

均衡：

```text
会按正常节奏安排讲义、例题、复习和小测，适合日常学习。
```

深入：

```text
会安排更完整的讲义、更充分的例题、更频繁的 review 和阶段测试，适合真正掌握这一章。
```

冲刺：

```text
会压缩铺垫，增加重点回顾、易错点整理和测试任务，适合考前复习或查漏补缺。
```

### 底层派生配置

这些字段不作为前端主配置暴露，而是由 `preference` 和学前诊断派生。

| preference | content_depth | example_intensity | assessment_intensity | review_intensity |
| --- | --- | --- | --- | --- |
| `fast_track` | `concise` | `low` | `low` | `low` |
| `balanced` | `standard` | `standard` | `standard` | `standard` |
| `mastery` | `detailed` | `high` | `high` | `high` |
| `sprint` | `focused` | `standard` | `high` | `high` |

诊断结果可以在此基础上做微调。例如用户选择快速但诊断显示基础薄弱，计划可以保留快速节奏，但第一个任务仍要补基础，并减少后续扩展内容。

冲突优先级：

```text
用户时间约束
  > 诊断得出的必要补基础
  > 学习方式 preference
  > 额外例题、测试、review
```

如果容量不足，后端应返回 warning 或 over-capacity 状态，不能静默突破用户每日时间。

## Step 3：学前诊断

学前诊断每次新建计划都要做，不需要 `diagnostic_required` 字段。

学前诊断只问用户当前掌握程度，不问学习偏好、资料范围、是否全量讲解，也不问资料知识小题。

页面标题建议：

```text
开始前，先了解一下你的基础
```

### 诊断问题结构

第一版使用：

```text
1 到 3 个核心知识点掌握问题
1 个薄弱方向问题
1 个可选补充输入
```

知识点掌握问题来自资料分析得到的核心知识点，不是考试题。默认选 3 个核心知识点；如果当前资料范围只能稳定提取 1 到 2 个核心知识点，则允许只问 1 到 2 个，不要凑无意义问题。

示例：

```text
你对「物理层的基本功能」了解多少？
A. 完全不了解
B. 听说过，但不清楚
C. 了解一些
D. 比较熟悉
```

薄弱方向问题：

```text
你最担心哪类内容？
A. 概念理解
B. 计算推导
C. 做题应用
D. 记忆重点
E. 其他
```

可选补充：

```text
还有什么想特别补的地方？
```

### 前端诊断输出

```json
{
  "question_version": "study_plan_diagnostic_v1",
  "topic_mastery": [
    {
      "topic_id": "physical_layer_basics",
      "topic_title": "物理层的基本功能",
      "mastery_level": "heard"
    },
    {
      "topic_id": "nyquist_shannon",
      "topic_title": "Nyquist / Shannon 公式",
      "mastery_level": "none"
    }
  ],
  "weak_area": "calculation",
  "diagnostic_note": "希望多讲公式怎么用"
}
```

枚举值：

| 字段 | 可选值 |
| --- | --- |
| `mastery_level` | `none`、`heard`、`some`、`familiar` |
| `weak_area` | `concept`、`calculation`、`application`、`memorization`、`other` |

### 诊断归纳结果

诊断答案归纳为计划生成使用的 profile：

```json
{
  "question_version": "study_plan_diagnostic_v1",
  "prior_knowledge_level": "little",
  "foundation_needed": true,
  "weak_topics": ["nyquist_shannon"],
  "weak_area": "calculation",
  "explanation_style": "step_by_step"
}
```

诊断结果影响：

- 第一个任务是否需要补基础；
- 讲义详细程度；
- 例题数量；
- 测试题数量；
- 后续生成内容的解释风格。

### 诊断复用和失效

同一次新建计划流程内，诊断答案可以复用，不需要每次点击“重新生成”都重新问。

以下变化会使诊断失效：

- `material_scope` 变化；
- `goal_text` 或目标知识点变化；
- 后端诊断问题版本 `question_version` 变化；
- 后端检测到诊断答案里的 `topic_id` 不属于当前资料快照。

日期、学习天数、每日学习时间和学习方式变化时，诊断答案默认保留，但 preview 需要重新生成。

## Step 4：计划预览

Preview 页展示同一组核心配置：

```text
学习目标
学习日期 / 学习天数
每日学习时间
学习方式
资料范围
```

其下展示学习方式说明文案。例如用户选择深入：

```text
本计划会偏深入：每天会安排较完整的讲义学习，穿插例题讲解和复习任务；关键知识点会有小测，最后会有综合测试，帮助你确认是否真的掌握。
```

Preview 页还展示：

- 每日任务列表；
- 每个任务预计分钟数；
- 是否有补基础任务；
- 是否有 review；
- 是否有测试任务；
- 资料覆盖 warning；
- 容量 warning，例如时间偏紧或超出每日学习时间。

用户可执行：

```text
返回修改配置
返回修改诊断
重新生成
确认保存计划
```

## 后端接口契约草案

尽量保留现有端点，只扩展请求和响应字段。

```text
POST /courses/{course_id}/study-plan-config-parses
POST /courses/{course_id}/study-plan-diagnostic-questions
POST /courses/{course_id}/study-plan-diagnostic-profiles
POST /courses/{course_id}/study-plans/preview
POST /courses/{course_id}/study-plans
```

诊断问题和诊断 profile 可以拆成两个端点，也可以先合并实现；对前端而言，需要能拿到问题列表，并能把答案归纳成 `diagnostic_profile`。

### Preview 请求

计划 preview 请求需要包含确认后的配置和诊断 profile。

```json
{
  "goal_text": "我要两天学完计网第七章",
  "start_date": "2026-07-12",
  "duration_days": 2,
  "daily_available_minutes": 90,
  "recommended_daily_minutes": 90,
  "daily_minutes_source": "system_estimated",
  "preference": "balanced",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  },
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v1",
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["nyquist_shannon"],
    "weak_area": "calculation",
    "explanation_style": "step_by_step"
  }
}
```

Preview 响应返回：

```json
{
  "config": {
    "start_date": "2026-07-12",
    "duration_days": 2,
    "end_date": "2026-07-13",
    "daily_available_minutes": 90,
    "recommended_daily_minutes": 90,
    "daily_minutes_source": "system_estimated",
    "preference": "balanced"
  },
  "tasks": [
    {
      "date": "2026-07-12",
      "title": "补基础：物理层的作用和基本概念",
      "estimated_minutes": 30,
      "task_type": "foundation",
      "source_topic_ids": ["physical_layer_basics"]
    }
  ],
  "material_snapshot": {
    "mode": "selected",
    "material_ids": ["mat_xxx"],
    "snapshot_hash": "sha256:..."
  },
  "coverage": {
    "covered_topic_ids": ["physical_layer_basics"],
    "missing_topic_ids": [],
    "warnings": []
  },
  "capacity": {
    "estimated_total_minutes": 180,
    "available_total_minutes": 180,
    "feasibility_status": "ok",
    "warnings": []
  },
  "generation_metadata": {
    "schema_version": 1,
    "model_provider": "openai-compatible",
    "generated_at": "2026-07-12T10:00:00+08:00"
  }
}
```

### 保存请求

方案 A 下，保存请求必须提交 preview 中展示过的任务。后端保存这些任务，不再生成新任务。

```json
{
  "idempotency_key": "uuid-from-frontend",
  "config": {
    "goal_text": "我要两天学完计网第七章",
    "start_date": "2026-07-12",
    "duration_days": 2,
    "end_date": "2026-07-13",
    "daily_available_minutes": 90,
    "recommended_daily_minutes": 90,
    "daily_minutes_source": "system_estimated",
    "preference": "balanced"
  },
  "material_snapshot": {
    "mode": "selected",
    "material_ids": ["mat_xxx"],
    "snapshot_hash": "sha256:..."
  },
  "diagnostic_profile": {
    "question_version": "study_plan_diagnostic_v1",
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["nyquist_shannon"],
    "weak_area": "calculation",
    "explanation_style": "step_by_step"
  },
  "tasks": [
    {
      "date": "2026-07-12",
      "title": "补基础：物理层的作用和基本概念",
      "estimated_minutes": 30,
      "task_type": "foundation",
      "source_topic_ids": ["physical_layer_basics"]
    }
  ],
  "coverage": {
    "covered_topic_ids": ["physical_layer_basics"],
    "missing_topic_ids": [],
    "warnings": []
  },
  "generation_metadata": {
    "schema_version": 1,
    "model_provider": "openai-compatible",
    "generated_at": "2026-07-12T10:00:00+08:00"
  }
}
```

保存成功后，写入 `StudyPlan.parsed_config_json` 的结构建议为：

```json
{
  "schema_version": 1,
  "confirmed_config": {},
  "diagnostic_profile": {},
  "material_snapshot": {},
  "coverage": {},
  "capacity": {},
  "generation_metadata": {}
}
```

`tasks` 应写入正式计划任务表或现有等价结构；`parsed_config_json` 只保留生成上下文和追溯信息。后续讲义、测试、review 生成使用 `confirmed_config`、`diagnostic_profile`、任务类型和来源 topic。

## 状态失效矩阵

| 用户动作 | 配置估算 | 诊断问题 / 答案 | preview |
| --- | --- | --- | --- |
| 修改资料范围 | 重新解析并重新估算 | 失效 | 失效 |
| 修改学习目标或目标知识点 | 重新解析并重新估算 | 可能失效；目标 topic 变化时失效 | 失效 |
| 修改开始日期或学习天数 | 重新估算 | 保留 | 失效 |
| 修改每日学习时间 | 保留配置，重算容量 | 保留 | 失效 |
| 修改学习方式 | 重算派生配置和容量 | 保留 | 失效 |
| 修改诊断答案 | 保留 | 更新 profile | 失效 |
| 点击重新生成 preview | 保留 | 保留 | 重新生成 |

第一版可以由前端状态机管理 stale 状态，并由后端做一致性校验；后续如果需要跨设备恢复，再引入服务端 wizard draft。

## 后端算法调整

### 配置解析

自然语言配置解析仍负责抽取：

- 学习目标；
- 开始日期和学习天数；
- 用户明确给出的每日学习时间；
- 学习方式偏好；
- unresolved fields。

如果用户未给每日学习时间，配置解析不再随便补固定默认值，而是等待资料分析后的系统估算。

### 每日时间估算

系统估算需要依赖资料内容量。

伪代码：

```text
units = map material chunks into learning units
estimated_total_minutes = sum(unit.estimated_minutes)
recommended_daily_minutes = max(30, ceil(estimated_total_minutes / duration_days))
daily_available_minutes = user_time or recommended_daily_minutes
available_total_minutes = daily_available_minutes * duration_days
```

### 计划生成

reduce prompt 需要区分：

- 用户明确时间或手动修改时间：尽量贴近日学习时间；
- 系统估算时间：按估算值生成，但不强行塞满不必要任务；
- `foundation_needed = true`：第一天增加补基础任务；
- `weak_topics`：相关主题更靠前、更细；
- `preference`：决定讲义、例题、测试和 review 强度。

模型输出后需要做结构化校验。若出现每日任务时长低于最低要求、枚举值非法、任务日期越界或缺少核心字段，后端可以把校验失败原因反馈给 generator 重试 1 次。

### 诊断后的容量校验

诊断可能新增补基础、更多例题、更多测试或更细解释，因此需要在诊断 profile 生成后和 preview 生成后都做容量检查。

```text
if required_minutes > available_total_minutes:
  feasibility_status = over_capacity
  warnings += PLAN_OVER_CAPACITY
```

前端提示应给出可操作建议：

- 增加每日学习时间；
- 增加学习天数；
- 改成快速模式；
- 保留当前时间，但减少额外例题、测试或 review。

## 错误处理

| 场景 | 建议错误码 | 前端处理 |
| --- | --- | --- |
| 日期或学习天数非法 | `INVALID_DATE_RANGE` | 停在配置确认页，提示修改日期或天数。 |
| 每日学习时间低于 30 分钟 | `DAILY_MINUTES_TOO_LOW` | 阻止继续，提示最低 30 分钟。 |
| 没有可用资料 | `NO_PARSED_MATERIALS` | 提示先上传并等待解析完成。 |
| 资料不属于当前课程或用户 | `MATERIAL_FORBIDDEN` | 移除非法资料并提示重新选择。 |
| 资料还在解析 | `MATERIAL_STILL_PARSING` | 显示等待解析完成。 |
| 资料解析失败 | `MATERIAL_PARSE_FAILED` | 提示该资料不可用于生成计划。 |
| 诊断答案和当前资料快照不匹配 | `DIAGNOSTIC_STALE` | 返回学前诊断重新回答。 |
| preview 容量超出 | `PLAN_OVER_CAPACITY` | 展示 warning 和调整建议，可以允许用户修改后重试。 |
| 模型输出枚举或结构非法 | `INVALID_MODEL_OUTPUT` | 后端重试 1 次，仍失败则展示生成失败。 |
| 保存请求未提交 tasks | `PREVIEW_TASKS_REQUIRED` | 新向导阻止保存；旧客户端走兼容路径。 |
| 保存请求幂等键重复 | `IDEMPOTENT_REPLAY` | 返回第一次保存的计划。 |

## 测试重点

- 自然语言无每日时间时，系统按资料总预计分钟数和学习天数估算，最低 30 分钟。
- 用户自然语言给出每日时间时，解析为 `user_text`，但仍返回 `recommended_daily_minutes`。
- 用户前端修改每日时间后，保存为 `user_modified`。
- 请求只提交 `start_date + duration_days`，后端正确计算 `end_date`。
- 资料范围变化会重新解析配置，并使诊断问题和 preview 失效。
- `include_all_parsed_materials=true` 使用当前已解析资料快照，后续上传资料不改变旧计划。
- 非当前课程资料、解析中资料和解析失败资料不能进入生成流程。
- 学前诊断允许 1 到 2 个 topic 问题，不强行凑满 3 个。
- 学前诊断只包含掌握程度和薄弱方向，不包含学习方式或资料范围问题。
- `fast_track`、`balanced`、`mastery`、`sprint` 映射到正确的底层生成 profile。
- 历史 `advanced` 能被读取并展示为冲刺，新写入使用 `sprint`。
- 诊断显示基础薄弱时，即使选择快速模式，第一个任务仍能补基础。
- 诊断增加补基础、例题或测试后，如果总时长超出容量，返回 `PLAN_OVER_CAPACITY`。
- preview 保存时提交 exact tasks，后端不重新生成任务。
- 同一个 `idempotency_key` 重复保存不会创建重复计划。
- 生成出的每日任务分钟数尊重 `daily_available_minutes`，不足或超出时返回结构化 warning。
