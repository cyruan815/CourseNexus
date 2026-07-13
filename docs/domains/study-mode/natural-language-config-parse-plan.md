# Study Mode 自然语言配置回填优化计划

## 状态

- 日期：2026-07-13
- 状态：后端自然语言回填契约已收紧，待最小测试和真实模型验证。
- 范围：`POST /api/v1/courses/{course_id}/study-plan-config-parses` 的自然语言字段回填、模型 prompt、字段规则、后处理兜底和验证口径。
- 非范围：学前诊断题的大模型生成、preview 任务生成、保存 exact tasks、讲义和任务测试题生成。学前诊断题应单独设计，本计划只借鉴其“模型主路径 + 后端校验 + 可追踪兜底”方法。


## 当前后端契约（2026-07-13 收尾）

- 配置回填接口仍为 `POST /api/v1/courses/{course_id}/study-plan-config-parses`，请求只接收 `goal_text` 和 `material_scope`。
- 大模型结构化输出改为内部抽取 schema `StudyPlanConfigExtraction`，只允许抽取 `start_date`、`end_date`、`duration_days`、`daily_available_minutes`、`preference`、`preference_overrides` 和 `ambiguous_fields`。
- `goal_text` 和 `material_scope` 由后端按请求原文回填；`recommended_daily_minutes`、`diagnostic_profile`、`material_snapshot`、`coverage`、`capacity` 等系统字段不由模型输出。
- `daily_available_minutes` 在回填阶段允许抽取正整数；如果存在，后端补 `daily_minutes_source="user_text"`。低于执行阶段最小值 30 分钟的校验仍留给 preview/save 阶段。
- `preference` 输出枚举为 `fast_track`、`balanced`、`mastery`、`sprint` 或 `null`；`advanced` 只保留为旧输入兼容，不作为新解析输出。
- `preference_overrides` 只表达隐藏策略偏好：`content_depth`、`example_intensity`、`assessment_intensity`、`review_intensity`，不新增前端主控件。
- `unresolved_fields` 由后端装配，只包含需要补充且阻塞的配置字段，例如缺少 `start_date`、缺少日期范围或模型标记 `preference` 冲突；系统估算字段不得进入该列表。
- `needs_confirmation_fields` 目前固定包含 `preference`，用于新向导在 preview 前显式确认学习方式；如果每日时间表达歧义，也可包含 `daily_available_minutes`。
- `generation_metadata.config_parse.preference_resolution` 记录 `model`、`rule_guardrail` 或 `unresolved`，便于追踪 prompt 是否稳定。
## 背景与问题

真实 E2E `real-e2e-physical-layer-20260713-151256` 证明自然语言配置回填已经调用大模型：应用日志中同一 `request_id=req_b7a0730b8c684b4c8d7510de36984847` 先记录 `model.generate`，`schema=StudyPlanParsedConfig`，`model=deepseek-chat`，随后 `study-plan-config-parses` 返回 200。

本次失败不是“没有调用大模型”，而是配置解析 prompt 和字段契约太弱。用户输入包含“2 天深度学习”“讲义详细一点”“多给公式适用条件和例题”，但模型返回 `preference=null` 并把 `preference` 放入 `unresolved_fields`。后续 preview 请求省略 `preference`，`StudyPlanBuildRequest` 默认回落为 `balanced`，导致用户的“深入掌握”意图被静默降级为“均衡学习”。

同时，`recommended_daily_minutes` 是系统估算字段，不应作为用户未填写字段进入 `unresolved_fields`。每日学习时间未明确时，配置回填应保留空值，让后续资料规模估算负责生成推荐值。

## 可借鉴的学前诊断方案设计点

用户提供的学前诊断方案对本计划有四个可复用原则：

1. **专门模型职责**：诊断方案建议新增 `study_plan_diagnostic` purpose；配置回填也应明确保留 `study_plan_parser` 的独立职责，不把 planner、diagnostic 或 task-test 的职责混进 parser。
2. **结构化输出 + 后端校验**：模型负责理解自然语言，后端负责校验枚举、日期一致性、系统字段边界和不可静默降级。
3. **可追踪兜底**：fallback 可以存在，但必须能追踪是否触发，不能让规则悄悄替代模型主路径。
4. **真实样本验收**：用 `Chap7 物理层.pdf` 的真实输入做验收，不能只靠 stub 测试。

不直接复用的点：配置回填是一次性字段解析，不需要 `diagnostic_session_id`。诊断题需要 session 是因为题目和答案之间存在多步状态；配置回填只需要在 `generation_metadata.config_parse` 中记录模型解析来源、兜底来源和 warning。

## 目标

- 配置回填继续使用大模型作为主路径，而不是用规则替代模型理解。
- prompt 明确声明可回填字段、枚举值、中文意图映射、冲突优先级和不可编造边界。
- `preference` 能从高置信自然语言中解析出来，例如“深度学习 / 详细讲义 / 多例题 / 真正掌握”映射为 `mastery`。
- 兜底规则只作为可追踪安全网，避免主路径依赖硬编码规则。
- `unresolved_fields` 只表达需要用户确认或补充的可编辑字段，不混入系统估算字段。
- 后续 preview 不应在新向导流程中静默把未确认的 `preference` 当成 `balanced`。

## 当前流程

```text
前端提交 goal_text + material_scope
  -> router.parse_study_plan_config_endpoint
  -> service.parse_study_plan_config
  -> ModelProvider.generate_structured(output_schema=StudyPlanParsedConfig)
  -> _resolve_config_dates 做相对日期和显式今天 + N 天的确定性补全
  -> 如 daily_available_minutes 有值但 source 为空，补 daily_minutes_source=user_text
  -> 回显 material_scope
```

当前后处理只解决相对日期，不会从中文目标里补 `preference`，也不会阻止后续默认 `balanced`。

## 字段规则

| 字段 | 回填来源 | 规则 | 不确定时 |
| --- | --- | --- | --- |
| `goal_text` | 大模型 | 清理“今天是...”这类日期锚点可以，但必须保留学习范围、学习方式、题量、重点主题等语义。 | 不得返回空；无法清理时保留原文。 |
| `start_date` | 大模型 + 日期后处理 | 用户给绝对日期或“今天是 YYYY 年 M 月 D 日”时解析为该日期。 | `null`，加入 `unresolved_fields`。 |
| `duration_days` | 大模型 + 日期后处理 | “2 天 / 两天 / N 天学完”解析为正整数。 | `null`，加入 `unresolved_fields`。 |
| `end_date` | 大模型 + 日期后处理 | 若有 `start_date + duration_days`，按 `start_date + duration_days - 1` 派生。若用户给日期范围，需与天数一致。 | 缺少起始日期或天数时为 `null`。 |
| `daily_available_minutes` | 大模型 | 只在用户明确说“每天/每日/一天学 X 分钟/小时”时填写。总学习时长不能当成每日时长。 | `null`；不阻塞后续系统估算。 |
| `recommended_daily_minutes` | 非自然语言回填 | 配置回填阶段不估算；由 preview 根据资料规模、天数和任务结果计算。 | 固定为 `null`，不加入 `unresolved_fields`。 |
| `daily_minutes_source` | 大模型 + 后处理 | 用户明确每日时间时为 `user_text`。配置回填阶段不得返回 `system_estimated`。 | `null`。 |
| `preference` | 大模型主路径 | 从中文学习方式意图解析为英文枚举。详见下方映射。 | `null`，加入 `unresolved_fields`，新向导必须让用户确认后再 preview。 |
| `material_scope` | 请求回显 | 原样回显请求中的资料范围，不在配置回填中扩大或缩小范围。 | 使用请求默认值。 |
| `diagnostic_profile` | 非自然语言回填 | 学前诊断后生成，配置回填阶段为空对象。 | `{}`。 |
| `material_snapshot` | 非自然语言回填 | preview/save 阶段生成，配置回填阶段为空对象。 | `{}`。 |
| `coverage` | 非自然语言回填 | preview 阶段生成，配置回填阶段为空对象。 | `{}`。 |
| `capacity` | 非自然语言回填 | preview/save 阶段生成，配置回填阶段为空对象。 | `{}`。 |
| `generation_metadata` | 后端追踪 | 可记录 `config_parse.model_provider`、`preference_resolution`、warning 等追踪信息。 | `{}`。 |
| `unresolved_fields` | 大模型 + 后处理 | 只包含用户可补充或确认的字段：`goal_text`、`start_date`、`duration_days`、`end_date`、`daily_available_minutes`、`preference`。 | 不得包含 `recommended_daily_minutes`、`capacity`、`coverage` 等系统字段。 |

## `preference` 映射规则

API 始终使用英文枚举：`fast_track`、`balanced`、`mastery`、`sprint`。`advanced` 只作为历史兼容输入，配置回填新输出不得使用。

| 输出值 | 用户表达 | 解释 |
| --- | --- | --- |
| `fast_track` | 快速过一遍、快速通关、时间紧、先建立框架、少讲一点、抓重点即可 | 减少展开讲义、例题、测试和复习。 |
| `balanced` | 正常学、按正常节奏、均衡、日常学习、没有明显强度偏好 | 默认均衡节奏，但只有在用户意图确实中性时由模型输出。 |
| `mastery` | 深度学习、深入掌握、深度掌握、系统掌握、真正掌握、讲透整个章节 | 表示整体学习方式偏深入；讲义详细、公式适用条件、多给例题等局部要求进入 `preference_overrides`，不单独提升整体 preference。 |
| `sprint` | 冲刺、考前复习、查漏补缺、强化测试、重点回顾、易错点、最后检验 | 面向复习和验收，强调重点回顾和测试。 |

冲突处理：

- 用户同时说“快速”和“详细掌握”时，优先保留用户显式时间约束，再按句子主目标判断。如果无法判断，`preference=null` 并加入 `unresolved_fields`。
- 用户只是要求“最后安排测试题”，不等于 `sprint`；只有出现冲刺、考前、查漏补缺、强化等复习语义时才输出 `sprint`。
- 用户说“深度学习”即使没有说“掌握”，也可倾向 `mastery`；但“讲义详细一点、多给例题、多讲公式适用条件”只表示局部覆盖，不应单独把整体 `preference` 提升为 `mastery`。
- 用户没有学习方式表达时，不在配置回填阶段默认 `balanced`；由配置确认页展示默认建议并让用户确认。

## Prompt 设计要求

`_build_config_parse_prompt()` 应从“只给日期规则”升级为“字段抽取说明 + 枚举映射 + 示例 + 输出纪律”。

prompt 必须包含：

```text
你是 CourseNexus 的学习计划配置解析器。
你的任务是把用户自然语言回填为可编辑配置字段，不生成计划。

preference 只能输出 fast_track、balanced、mastery、sprint 或 null：
- 深度学习、深入掌握、真正掌握、讲透整个章节 -> mastery
- 快速过一遍、快速通关、时间紧、少讲 -> fast_track
- 冲刺、考前、查漏补缺、强化测试、易错点 -> sprint
- 正常节奏、均衡、日常学习 -> balanced

如果用户没有每日学习时间，不要猜 daily_available_minutes。
recommended_daily_minutes 不是用户输入字段，保持 null。
如果用户给“今天是 YYYY年M月D日”和“N天”，解析 start_date、duration_days、end_date。
无法可靠确定的用户可编辑字段填 null，并加入 unresolved_fields。
```

prompt 示例至少覆盖：

- “今天是 2026 年 7 月 13 日，我想用 2 天深度学习物理层，讲义详细一点，多给公式和例题” -> `preference=mastery`，并提取 `preference_overrides.content_depth=detailed`、`example_intensity=high`。`讲义详细一点，多给例题` 若没有整体学习方式，应保持 `preference=null`，只填局部覆盖。
- “我想明天快速过一遍第七章” -> `preference=fast_track`。
- “考前冲刺，帮我查漏补缺并多安排测试” -> `preference=sprint`。
- “两周正常学习传输层，每天 60 分钟” -> `preference=balanced`、`daily_available_minutes=60`、`daily_minutes_source=user_text`。

## 后处理与兜底

后处理分三层，不能让规则替代大模型主路径。

1. 必须执行的确定性归一：
   - `advanced` 归一为 `sprint`。
   - 显式“今天是 YYYY 年 M 月 D 日 + N 天”补齐 `start_date`、`duration_days`、`end_date`。
   - `daily_available_minutes` 有值但 `daily_minutes_source` 为空时补 `user_text`。
   - 删除 `unresolved_fields` 中的系统字段，例如 `recommended_daily_minutes`、`coverage`、`capacity`。

2. 模型输出一致性校验：
   - `daily_minutes_source=system_estimated` 出现在配置回填响应时改为 `null`，因为该阶段不做系统估算。
   - `recommended_daily_minutes` 非空时清空，并记录追踪 warning。
   - `preference` 非法时拒绝结构化结果或触发一次模型重试。

3. 极窄兜底安全网：
   - 仅当模型返回 `preference=null`，且用户文本出现强信号词时才触发。
   - 整体 preference 兜底只识别整体学习方式强信号，例如 `深度学习`、`深入掌握`、`系统掌握` -> `mastery`；`快速过一遍`、`快速通关` -> `fast_track`；`考前冲刺`、`查漏补缺` -> `sprint`。`讲义详细`、`多给例题`、`多给公式` 等由单独的 `preference_overrides` 兜底补入 `content_depth` 或 `example_intensity`，不得借此修改整体 preference。
   - 整体 preference 兜底触发时必须写入 `generation_metadata.config_parse.preference_resolution="rule_guardrail"`；局部覆盖兜底触发时写入 `preference_overrides_resolution="rule_guardrail"`，便于后续统计 prompt 是否仍不稳定。
   - 正常模型识别时写入 `preference_resolution="model"`；仍无法确定时写入 `preference_resolution="unresolved"`。

## 前端与 preview 衔接

配置确认页必须展示 5 个字段：学习目标、学习日期/天数、每日学习时间、学习方式、资料范围。

新向导流程中：

- 如果 `preference` 非空，学习方式控件按该值预选，用户可修改。
- 如果 `preference=null`，学习方式控件展示默认建议，但应标记为需要确认；进入 preview 前必须提交用户确认后的值。
- 如果用户没有每日学习时间，配置确认页展示“将根据资料量估算”，进入 preview 后由后端返回 `recommended_daily_minutes` 和最终 `daily_available_minutes`。
- preview 请求不得因为配置回填缺失 `preference` 而静默省略该字段；wizard 应显式传用户确认值。

旧客户端可继续使用 `StudyPlanBuildRequest.preference="balanced"` 的兼容默认，但新向导和 E2E 脚本必须显式传值，避免回归。

## 错误与重试

- 模型结构化输出不符合 schema：按现有 `ModelProvider.generate_structured()` 策略失败或重试。
- 日期字段冲突，例如 `start_date + duration_days` 与 `end_date` 不一致：返回 `VALIDATION_ERROR`，前端停留在配置确认页。
- 每日时间低于 30 分钟：返回 `DAILY_MINUTES_TOO_LOW` 或现有等价校验错误。
- 模型返回非法 `preference`：重试一次；仍非法则返回 `VALIDATION_ERROR`，不得静默变成 `balanced`。
- 大模型调用失败：配置回填接口返回生成失败错误；只有产品确认后才允许降级到纯规则解析。

## 测试计划

### 单元测试

- prompt 测试：断言 `_build_config_parse_prompt()` 包含 preference 枚举、局部 `preference_overrides` 映射、`recommended_daily_minutes` 不由用户输入推断、每日时间不猜测。
- 日期归一测试：`今天是2026年7月13日 + 2天` 返回 `start_date=2026-07-13`、`end_date=2026-07-14`、`duration_days=2`。
- unresolved 测试：`recommended_daily_minutes` 不出现在 `unresolved_fields`。
- preference 后处理测试：`advanced` 归一为 `sprint`，非法值触发错误或重试。
- 兜底追踪测试：模型返回 `preference=null` 且文本含“深度学习”时，兜底输出 `mastery`；文本仅含“讲义详细一点、多给例题”时保持 `preference=null`，补 `preference_overrides` 并写入 `preference_overrides_resolution="rule_guardrail"`。

### API 测试

- `POST /study-plan-config-parses` 使用 stub 模型返回 `mastery`，响应保持 `mastery`。
- stub 模型返回 `null`，但用户文本无强信号时，响应保留 `preference=null` 且 `unresolved_fields` 包含 `preference`。
- stub 模型错误返回 `recommended_daily_minutes`，后处理清空系统估算字段。

### 真实模型验证

使用物理层真实 E2E 输入：

```text
今天是2026年7月13日。我想用2天深度学习物理层，重点补Nyquist/Shannon、编码调制和传输介质。我希望讲义详细一点，多给公式适用条件和例题。最后请安排10道选择题和3道计算题检验Nyquist/Shannon公式、编码调制和传输介质。
```

期望：

- `start_date=2026-07-13`
- `duration_days=2`
- `end_date=2026-07-14`
- `daily_available_minutes=null`
- `recommended_daily_minutes=null`
- `daily_minutes_source=null`
- `preference=mastery`
- `unresolved_fields` 不包含 `recommended_daily_minutes`

## 实施拆分

1. 更新配置解析 prompt，并添加 prompt 单元测试。
2. 调整配置回填后处理，清理系统字段和追踪 `preference_resolution`。
3. 添加 preference 极窄兜底及测试，确保正常模型识别路径不依赖兜底。
4. 调整 E2E 脚本或前端新向导请求组装：preview 前必须显式传确认后的 `preference`。
5. 更新 API / 前端集成文档中的字段说明。
6. 用真实物理层输入跑一次配置回填验证，保存响应摘要到 `docs/domains/study-mode/validation/`。

## 与学前诊断的边界

学前诊断题已由 [diagnostic-questions.md](diagnostic-questions.md) 单独承接。当前边界是：配置回填仍只解析学习设置和缺失字段；学前诊断题使用独立 `study_plan_diagnostic` purpose，根据 `goal_text + confirmed_config + material_scope + chunk excerpts` 选择资料内 topic，后端固定输出 3 道 `topic_mastery` 并用 fallback 补足。配置解析不得补问或生成诊断题，诊断模型也不得补问 `start_date`、`duration_days`、`preference` 或每日时间。
