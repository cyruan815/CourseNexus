# Study Mode 计划生成向导设计

## 状态

- 日期：2026-07-12
- 状态：设计已确认，待实施。
- 范围：从用户点进学习计划生成开始，到生成学习计划 preview 为止的前端页面流、配置字段、学前诊断和后端契约调整。

## 目标

计划生成向导要把“用户想怎么学”和“用户现在会多少”分开处理。

- 配置确认回答“用户想怎么学”。
- 学前诊断回答“用户现在会多少”。
- 计划 preview 基于配置和诊断共同生成。

## 非目标

- 不在本任务中实现资料解析漏页、OCR 降级或 material diagnostics。
- 不在本任务中实现正式任务讲义、测试题或 review 内容生成，只为后续生成提供配置和诊断输入。
- 不把讲义详细程度、例题数量、测试数量作为前端主界面独立选项。

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
| `start_date` / `end_date` / `duration_days` | 是 | 用户可改日期或学习天数。 |
| `daily_available_minutes` | 是 | 每日学习时间永远展示且可改。 |
| `preference` | 是 | 学习方式：快速、均衡、深入、冲刺。 |
| `material_scope` | 是 | 可重新选择资料；修改后触发重新解析和重新估算。 |

### 每日学习时间规则

如果用户自然语言中明确说了每天学多久：

```text
daily_available_minutes = 用户输入的分钟数
daily_minutes_source = user_text
```

如果用户没有说明每天学多久：

```text
daily_available_minutes = max(30, ceil(资料总预计学习分钟数 / 学习天数))
daily_minutes_source = system_estimated
```

用户在前端手动修改后：

```text
daily_minutes_source = user_modified
```

最低每日学习时间为 30 分钟。该值是系统底线，不作为前端主配置项展示。

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

当前后端已有 `advanced` 枚举值。实施时应把用户侧“冲刺”映射到新值 `sprint`，或在过渡期兼容旧值 `advanced`，避免历史数据读写失败。

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

## Step 3：学前诊断

学前诊断每次生成计划都要做，不需要 `diagnostic_required` 字段。

学前诊断只问用户当前掌握程度，不问学习偏好、资料范围、是否全量讲解，也不问资料知识小题。

页面标题建议：

```text
开始前，先了解一下你的基础
```

### 诊断问题结构

第一版固定为：

```text
3 个知识点掌握问题
1 个薄弱方向问题
1 个可选补充输入
```

知识点掌握问题来自资料分析得到的核心知识点，不是考试题。

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
B. 公式计算
C. 做题应用
D. 记忆重点
```

可选补充：

```text
还有什么想特别补的地方？
```

### 前端诊断输出

```json
{
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
  "weak_area": "formula",
  "diagnostic_note": "希望多讲公式怎么用"
}
```

### 诊断归纳结果

诊断答案归纳为计划生成使用的 profile：

```json
{
  "prior_knowledge_level": "little",
  "foundation_needed": true,
  "weak_topics": ["nyquist_shannon"],
  "weak_area": "formula",
  "explanation_style": "step_by_step"
}
```

诊断结果影响：

- 第一个任务是否需要补基础；
- 讲义详细程度；
- 例题数量；
- 测试题数量；
- 后续生成内容的解释风格。

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
- 资料覆盖 warning。

用户可执行：

```text
返回修改配置
返回修改诊断
重新生成
确认保存计划
```

## 后端请求契约草案

计划 preview 请求需要包含配置和诊断。

```json
{
  "goal_text": "我要两天学完计网第七章",
  "start_date": "2026-07-12",
  "end_date": "2026-07-13",
  "duration_days": 2,
  "daily_available_minutes": 90,
  "daily_minutes_source": "system_estimated",
  "preference": "balanced",
  "material_scope": {
    "include_all_parsed_materials": false,
    "material_ids": ["mat_xxx"]
  },
  "diagnostic_profile": {
    "prior_knowledge_level": "little",
    "foundation_needed": true,
    "weak_topics": ["nyquist_shannon"],
    "weak_area": "formula",
    "explanation_style": "step_by_step"
  }
}
```

保存计划时，应把用户确认后的配置、诊断 profile、coverage 和任务来源一起写入 `StudyPlan.parsed_config_json`，便于后续讲义、测试、review 和重生成继续使用同一学习画像。

## 后端算法调整

### 配置解析

自然语言配置解析仍负责抽取：

- 学习目标；
- 日期范围或学习天数；
- 用户明确给出的每日学习时间；
- 学习方式偏好；
- unresolved fields。

如果用户未给每日学习时间，配置解析不再随便补固定默认值，而是等待材料分析后的系统估算。

### 每日时间估算

系统估算需要依赖资料内容量。

伪代码：

```text
units = map material chunks into learning units
total_minutes = sum(unit.estimated_minutes)
duration_days = date_range_days
estimated_daily_minutes = ceil(total_minutes / duration_days)
daily_available_minutes = max(30, estimated_daily_minutes)
```

### 计划生成

reduce prompt 需要区分：

- 用户明确时间或手动修改时间：尽量贴近日学习时间；
- 系统估算时间：按估算值生成，但不强行塞满不必要任务；
- `foundation_needed = true`：第一天增加补基础任务；
- `weak_topics`：相关主题更靠前、更细；
- `preference`：决定讲义、例题、测试和 review 强度。

## 错误处理

- 没有已解析资料：阻止进入配置确认，提示先上传并解析资料。
- 资料范围变化：配置和诊断都标记为 stale，必须重新解析配置并重新生成诊断问题。
- 用户手动改过每日时间后资料范围变化：保留用户值，同时显示新系统建议。
- 学前诊断未完成：不能生成 preview。
- preview 生成失败：返回结构化错误，前端显示失败原因并允许返回修改配置。

## 测试重点

- 自然语言无每日时间时，系统按资料总预计分钟数和学习天数估算，最低 30 分钟。
- 用户自然语言给出每日时间时，解析为 `user_text`。
- 用户前端修改每日时间后，保存为 `user_modified`。
- 资料范围变化会重新解析配置，并使诊断问题失效。
- 学前诊断只包含掌握程度和薄弱方向，不包含学习方式或资料范围问题。
- `fast_track`、`balanced`、`mastery`、`sprint` 映射到正确的底层生成 profile。
- preview 页展示核心配置和学习方式说明文案。