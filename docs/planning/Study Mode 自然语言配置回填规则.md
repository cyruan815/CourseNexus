# Study Mode 自然语言配置回填规则

下面这版可以直接替换原文中的“字段规则、Prompt 设计、后处理、前端与 preview 衔接、测试计划”等部分。重点修正了：

- `unresolved_fields` 和“需要确认”混在一起；
- 模型直接输出完整 `StudyPlanParsedConfig`；
- 单一 `preference` 无法表达“详细讲义但少测试”；
- 关键词兜底误判、否定和冲突问题；
- “明天、下周”等相对日期缺少参考日期和时区；
- 新向导漏传 `preference` 时仍会静默回落 `balanced`。

这些修改是在原优化计划基础上的进一步收紧。



## 1. 设计原则

自然语言配置回填只负责从用户输入中提取**用户可编辑的计划配置**，不负责：

- 生成学习任务；
- 估算每日推荐学习时间；
- 生成诊断题；
- 计算资料覆盖率；
- 生成 capacity；
- 生成讲义或测试题。

整体流程调整为：

```text
用户 goal_text
    ↓
模型输出 StudyPlanConfigExtraction
    ↓
后端执行日期归一、枚举校验、冲突检查
    ↓
后端执行极窄规则兜底
    ↓
后端组装 StudyPlanParsedConfig
    ↓
前端配置确认
    ↓
前端显式提交确认后的配置进入 preview
```

模型是自然语言理解的主路径，后端负责：

- 限制模型可输出字段；
- 校验字段合法性；
- 派生确定性字段；
- 识别冲突；
- 防止静默默认；
- 记录字段来源。

------

# 2. 模型抽取 Schema

不再让模型直接输出完整的 `StudyPlanParsedConfig`。

新增仅供模型结构化输出使用的 Schema：

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


StudyPreference = Literal[
    "fast_track",
    "balanced",
    "mastery",
    "sprint",
]

ContentDepth = Literal[
    "concise",
    "standard",
    "detailed",
]

IntensityLevel = Literal[
    "low",
    "standard",
    "high",
]


class StudyPreferenceOverrides(BaseModel):
    content_depth: ContentDepth | None = None
    example_intensity: IntensityLevel | None = None
    assessment_intensity: IntensityLevel | None = None
    review_intensity: IntensityLevel | None = None


class StudyPlanConfigExtraction(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1)

    daily_available_minutes: int | None = Field(
        default=None,
        ge=1,
    )

    preference: StudyPreference | None = None

    preference_overrides: StudyPreferenceOverrides = Field(
        default_factory=StudyPreferenceOverrides
    )

    ambiguous_fields: list[
        Literal[
            "start_date",
            "end_date",
            "duration_days",
            "daily_available_minutes",
            "preference",
        ]
    ] = Field(default_factory=list)
```

模型不得输出：

```text
recommended_daily_minutes
daily_minutes_source
material_scope
diagnostic_profile
material_snapshot
coverage
capacity
generation_metadata
unresolved_fields
needs_confirmation_fields
```

这些字段全部由后端组装。

这样可以从结构上避免模型错误填写：

```json
{
  "recommended_daily_minutes": 120,
  "daily_minutes_source": "system_estimated"
}
```

而不是先允许模型输出，再由后端清空。

------

# 3. API 回填响应结构

最终配置回填接口仍然返回完整的配置对象，但增加：

```python
class StudyPlanParsedConfig(BaseModel):
    goal_text: str

    start_date: date | None
    end_date: date | None
    duration_days: int | None

    daily_available_minutes: int | None
    recommended_daily_minutes: int | None
    daily_minutes_source: str | None

    preference: StudyPreference | None
    preference_overrides: StudyPreferenceOverrides

    material_scope: MaterialScope

    diagnostic_profile: dict
    material_snapshot: dict
    coverage: dict
    capacity: dict
    generation_metadata: dict

    unresolved_fields: list[str]
    needs_confirmation_fields: list[str]
```

其中两个字段必须区分：

## `unresolved_fields`

表示：

> 缺少该字段后，当前配置不能可靠进入下一阶段。

只允许包含：

```text
start_date
duration_days
preference
```

具体规则：

- `start_date` 无法从用户文本或参考日期中确定时加入；
- `duration_days` 和 `end_date` 都无法确定时，加入 `duration_days`；
- `preference` 存在明确冲突且无法确定时加入。

通常不加入：

```text
end_date
```

因为只要有：

```text
start_date + duration_days
```

就可以派生 `end_date`。

也不加入：

```text
daily_available_minutes
```

因为用户未填写每日时间时，可以由 preview 后续估算，不阻塞流程。

绝对不得加入：

```text
recommended_daily_minutes
daily_minutes_source
material_snapshot
coverage
capacity
generation_metadata
```

## `needs_confirmation_fields`

表示：

> 系统已经得到一个结果或建议，但新向导仍要求用户确认。

例如：

```json
{
  "preference": "mastery",
  "unresolved_fields": [],
  "needs_confirmation_fields": ["preference"]
}
```

对于 `wizard_v1`，学习方式始终需要在确认页展示并确认。

每日学习时间未填写时：

```json
{
  "daily_available_minutes": null,
  "recommended_daily_minutes": null,
  "unresolved_fields": [],
  "needs_confirmation_fields": []
}
```

前端只展示：

```text
每日学习时间：将根据资料量和计划内容自动估算
```

不要求用户必须补填。

------

# 4. 字段回填规则

| 字段                        | 解析主体   | 规则                                                |
| --------------------------- | ---------- | --------------------------------------------------- |
| `goal_text`                 | 后端       | 使用请求中的原始目标文本，不由抽取模型生成系统字段  |
| `start_date`                | 模型＋后端 | 支持绝对日期及“今天、明天、下周一”等相对日期        |
| `duration_days`             | 模型＋后端 | “两天、两周、14 天内”等转为正整数天数               |
| `end_date`                  | 模型＋后端 | 优先根据另外两个日期字段确定性派生                  |
| `daily_available_minutes`   | 模型       | 仅在用户明确表达“每天/每日/一天 X 分钟或小时”时填写 |
| `recommended_daily_minutes` | preview    | 配置回填阶段固定为 `null`                           |
| `daily_minutes_source`      | 后端       | 用户明确填写每日时间时为 `user_text`，否则为 `null` |
| `preference`                | 模型主路径 | 表达整体学习模式                                    |
| `preference_overrides`      | 模型主路径 | 表达讲义、例题、测试、复习的局部要求                |
| `material_scope`            | 后端       | 原样回显请求值                                      |
| 其他系统字段                | 后端       | 配置回填阶段为空对象或空值                          |

------

# 5. `preference` 与局部覆盖规则

## 5.1 整体学习方式

`preference` 表示整体计划模式：

| 值           | 典型用户表达                             | 整体策略           |
| ------------ | ---------------------------------------- | ------------------ |
| `fast_track` | 快速过一遍、时间紧、先抓框架、少讲一点   | 减少展开和复习     |
| `balanced`   | 正常节奏、均衡学习、日常学习             | 使用标准强度       |
| `mastery`    | 深入掌握、讲透、真正理解、系统学习       | 提高讲解和掌握要求 |
| `sprint`     | 考前冲刺、查漏补缺、强化复习、易错点回顾 | 强调复习和测试     |

用户没有明确表达整体模式时：

```json
{
  "preference": null
}
```

配置解析阶段不得自动返回 `balanced`。

## 5.2 局部偏好覆盖

不能把所有局部要求都压缩到一个 `preference` 中。

以下表达分别映射为：

| 用户表达               | 字段                        |
| ---------------------- | --------------------------- |
| 讲义详细一点、讲细一些 | `content_depth=detailed`    |
| 简洁一点、少讲一些     | `content_depth=concise`     |
| 多给例题、多举例       | `example_intensity=high`    |
| 少一点例题             | `example_intensity=low`     |
| 多安排测试、加强练习   | `assessment_intensity=high` |
| 不要太多测试           | `assessment_intensity=low`  |
| 多安排复习和回顾       | `review_intensity=high`     |
| 不用重复复习           | `review_intensity=low`      |

例如：

```text
我时间比较紧，想快速过一遍，但公式部分要详细讲，多给两个例题，不要太多测试。
```

应输出：

```json
{
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": "high",
    "assessment_intensity": "low",
    "review_intensity": null
  }
}
```

而不是因为出现“详细”和“多例题”就整体返回 `mastery`。

------

# 6. 日期解析规则

调用 `_build_config_parse_prompt()` 时，必须传入：

```text
reference_date
timezone
```

例如：

```text
reference_date = 2026-07-13
timezone = Asia/Shanghai
```

Prompt 不得依赖模型自己猜测当前日期。

## 6.1 支持的日期组合

### 已有开始日期和持续天数

```text
2026 年 7 月 13 日开始，学习 2 天
```

得到：

```text
start_date = 2026-07-13
duration_days = 2
end_date = 2026-07-14
```

日期范围首尾均包含。

### 已有开始日期和结束日期

```text
7 月 13 日到 7 月 15 日
```

得到：

```text
start_date = 2026-07-13
end_date = 2026-07-15
duration_days = 3
```

### 已有结束日期和持续天数

```text
7 月 15 日前用 3 天完成
```

在语义明确时得到：

```text
start_date = 2026-07-13
end_date = 2026-07-15
duration_days = 3
```

### 相对日期

```text
明天开始学两天
```

如果：

```text
reference_date = 2026-07-13
```

则得到：

```text
start_date = 2026-07-14
end_date = 2026-07-15
duration_days = 2
```

## 6.2 日期冲突

用户明确给出的日期互相矛盾时，不应静默修改。

例如：

```text
7 月 13 日开始，学习 2 天，7 月 16 日结束
```

因为：

```text
7 月 13 日 + 2 天 = 7 月 14 日
```

应返回：

```text
VALIDATION_ERROR
field = date_range
```

或者停留在确认页让用户修正。

------

# 7. 每日学习时间规则

只在出现明确的“每日”语义时解析：

```text
每天学习 60 分钟
每日学习 1.5 小时
一天可以学两个小时
```

对应：

```text
60
90
120
```

以下表达不能解析为每日学习时间：

```text
两天一共学习 3 小时
这个章节预计学 180 分钟
总共安排 4 个小时
```

它们表达的是总时间，而不是每日时间。

用户没有提供每日学习时间时：

```json
{
  "daily_available_minutes": null,
  "recommended_daily_minutes": null,
  "daily_minutes_source": null
}
```

`recommended_daily_minutes` 留给 preview，根据以下信息计算：

```text
资料规模
计划持续天数
任务预计总时长
计划强度
```

------

# 8. 新版配置解析 Prompt

下面可以作为 `_build_config_parse_prompt()` 的核心模板。

```text
你是 CourseNexus 的学习计划配置解析器。

你的唯一任务是从用户的自然语言学习目标中提取可编辑配置。
你不生成学习计划、学习任务、讲义、测试题或推荐学习时间。

当前日期上下文：
- reference_date: {reference_date}
- timezone: {timezone}

用户原始输入：
{goal_text}

请输出符合 StudyPlanConfigExtraction Schema 的 JSON。

你只能提取以下字段：

1. start_date
2. end_date
3. duration_days
4. daily_available_minutes
5. preference
6. preference_overrides
7. ambiguous_fields

不要输出或推断以下系统字段：

- recommended_daily_minutes
- daily_minutes_source
- material_scope
- diagnostic_profile
- material_snapshot
- coverage
- capacity
- generation_metadata
- unresolved_fields
- needs_confirmation_fields

日期规则：

- “今天、明天、后天、下周”等相对日期必须以 reference_date 和 timezone 为基准。
- 持续 N 天时，开始日算第 1 天。
- “一周、1周、一个星期、一星期、一个礼拜”表示 `duration_days=7`；N 周/星期/礼拜表示 `N*7` 天。
- 如果已知 start_date 和 duration_days，请计算 end_date。
- 如果已知 start_date 和 end_date，请计算 duration_days。
- 如果用户明确给出的日期互相冲突，不要自行覆盖，把相关字段加入 ambiguous_fields。
- 无法可靠确定时返回 null，不要猜测。

每日学习时间规则：

- 只有用户明确表达“每天、每日、一天学习 X 分钟或小时”时，才填写 daily_available_minutes。
- “两天总共学习三小时”不是每日学习时间，不得填写 daily_available_minutes。
- 用户没有说明每日学习时间时返回 null。
- 不得计算推荐每日学习时间。

preference 只能是：

- fast_track
- balanced
- mastery
- sprint
- null

整体学习方式映射：

- “速通、快速过一遍、时间紧、先建立框架、少讲一点、抓重点”
  -> fast_track

- “正常节奏、均衡学习、日常学习”
  -> balanced

- “深入掌握、系统掌握、真正理解、讲透、扎实掌握”
  -> mastery

- “考前冲刺、查漏补缺、强化复习、重点回顾、易错点复盘”
  -> sprint

注意：

- 用户只是要求最后安排测试题，不等于 sprint。
- 用户没有明确整体学习方式时，preference 返回 null。
- 不得因为缺少学习方式就默认 balanced。
- “深度学习”可能是学习方式，也可能是课程主题，必须结合句子语义判断。
- “快速学习深度学习基础”中的“深度学习”是课程主题，整体方式应为 fast_track。
- “用两天深度学习物理层”中的“深度学习”表示深入学习方式，可倾向 mastery。
- 出现否定表达时，不得使用被否定的偏好，例如：
  - “不需要详细讲”
  - “不要多给例题”
  - “不是考前冲刺”
- 如果两个整体模式明确冲突且无法通过局部覆盖表达，将 preference 返回 null，并把 preference 加入 ambiguous_fields。

preference_overrides 用于提取局部要求：

content_depth:
- “讲义详细、讲细、展开讲解” -> detailed
- “简洁一点、少讲、只讲重点” -> concise
- 没有明确表达 -> null

example_intensity:
- “多给例题、多举例、多做示范” -> high
- “少一点例题、不需要太多例题” -> low
- 没有明确表达 -> null

assessment_intensity:
- “多安排测试、加强练习、强化检测” -> high
- “不要太多测试、少做题” -> low
- 没有明确表达 -> null

review_intensity:
- “多复习、多回顾、重复巩固” -> high
- “不用重复复习、少安排回顾” -> low
- 没有明确表达 -> null

局部覆盖和整体 preference 可以同时存在。

示例一：

输入：
今天是 2026 年 7 月 13 日。我想用 2 天深入掌握物理层，讲义详细一点，多给公式例题。

输出：
{
  "start_date": "2026-07-13",
  "end_date": "2026-07-14",
  "duration_days": 2,
  "daily_available_minutes": null,
  "preference": "mastery",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": "high",
    "assessment_intensity": null,
    "review_intensity": null
  },
  "ambiguous_fields": []
}

示例二：

输入：
我想明天快速过一遍第七章，公式部分详细讲，不要太多测试。

输出：
{
  "start_date": "{tomorrow_date}",
  "end_date": null,
  "duration_days": null,
  "daily_available_minutes": null,
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": null,
    "assessment_intensity": "low",
    "review_intensity": null
  },
  "ambiguous_fields": []
}

示例三：

输入：
考前冲刺两天，每天学习 90 分钟，重点查漏补缺并多安排测试。

输出：
{
  "start_date": null,
  "end_date": null,
  "duration_days": 2,
  "daily_available_minutes": 90,
  "preference": "sprint",
  "preference_overrides": {
    "content_depth": null,
    "example_intensity": null,
    "assessment_intensity": "high",
    "review_intensity": "high"
  },
  "ambiguous_fields": []
}

示例四：

输入：
我想快速学习深度学习基础。

输出：
{
  "start_date": null,
  "end_date": null,
  "duration_days": null,
  "daily_available_minutes": null,
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": null,
    "example_intensity": null,
    "assessment_intensity": null,
    "review_intensity": null
  },
  "ambiguous_fields": []
}
```

------

# 9. 后端归一和校验规则

模型返回后，后端依次执行以下步骤。

## 9.1 日期确定性归一

```text
有 start_date + duration_days
→ 派生 end_date

有 start_date + end_date
→ 派生 duration_days

有 end_date + duration_days
→ 在语义明确时派生 start_date
```

派生公式：

```python
end_date = start_date + timedelta(days=duration_days - 1)
duration_days = (end_date - start_date).days + 1
start_date = end_date - timedelta(days=duration_days - 1)
```

如果三个字段同时存在但不一致：

```text
返回日期冲突错误
```

不得静默覆盖用户明确日期。

## 9.2 每日时间归一

如果：

```text
daily_available_minutes is not None
```

则后端设置：

```text
daily_minutes_source = user_text
```

否则：

```text
daily_minutes_source = null
```

配置解析阶段始终：

```text
recommended_daily_minutes = null
```

## 9.3 字段状态计算

后端根据最终字段计算：

```python
unresolved_fields = []
needs_confirmation_fields = []
```

规则示例：

```python
if start_date is None:
    unresolved_fields.append("start_date")

if duration_days is None and end_date is None:
    unresolved_fields.append("duration_days")

if preference is None:
    needs_confirmation_fields.append("preference")
```

新向导中，即便模型识别出 preference，也可以统一要求确认：

```python
if client_flow == "wizard_v1":
    needs_confirmation_fields.append("preference")
```

去重后返回。

------

# 10. 极窄规则兜底

规则兜底只在以下条件同时成立时执行：

```text
模型 preference = null
模型没有把 preference 标为 ambiguous
用户文本包含明确、非否定、非课程主题的强语义模式
```

不能仅凭单个关键词判断。

## 10.1 推荐使用短语模式

### `mastery`

可以考虑：

```text
深入掌握
系统掌握
真正掌握
讲透
扎实掌握
用 N 天深度学习某个非“深度学习”主题
```

不能简单使用：

```text
包含“深度学习”
```

### `fast_track`

```text
快速过一遍
快速通关
先抓框架
时间紧先学重点
少讲一点
```

### `sprint`

```text
考前冲刺
查漏补缺
强化复习
易错点复盘
```

## 10.2 否定检查

命中强短语前，必须检查附近是否存在：

```text
不
不要
不用
无需
别
不想
不是
```

例如：

```text
不需要详细讲
```

不能触发：

```text
content_depth=detailed
mastery
不是考前冲刺
```

不能触发：

```text
sprint
```

## 10.3 主题与学习方式区分

以下表达：

```text
快速学习深度学习基础
```

“深度学习”是课程主题，不能触发 `mastery`。

以下表达：

```text
用两天深度学习物理层
```

“深度学习”是学习方式，可以触发 `mastery`。

规则兜底无法可靠区分时：

```text
preference 保持 null
needs_confirmation_fields 加入 preference
```

## 10.4 冲突处理

可以通过局部覆盖表达的冲突不算真正冲突。

例如：

```text
快速过一遍，但公式详细讲
```

可以得到：

```json
{
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": "detailed"
  }
}
```

真正无法判断的表达：

```text
既要快速过一遍，又要全面深入掌握所有内容。
```

应得到：

```json
{
  "preference": null,
  "ambiguous_fields": ["preference"]
}
```

后端加入：

```text
unresolved_fields 或 needs_confirmation_fields
```

由确认页让用户选择。

## 10.5 来源记录

```json
{
  "generation_metadata": {
    "config_parse": {
      "preference_resolution": "model"
    }
  }
}
```

允许值：

```text
model
rule_guardrail
unresolved
```

如果局部覆盖由模型抽取，也可记录：

```json
{
  "preference_overrides_resolution": "model"
}
```

------

# 11. 新向导与 preview 的强制衔接

新向导必须在请求中带：

```json
{
  "client_flow": "wizard_v1"
}
```

配置确认页必须展示：

```text
学习目标
学习日期和天数
每日学习时间
整体学习方式
讲义详细度
例题强度
测试强度
复习强度
资料范围
```

进入 preview 时，新向导必须显式提交确认后的：

```json
{
  "client_flow": "wizard_v1",
  "preference": "mastery",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": "high",
    "assessment_intensity": "standard",
    "review_intensity": "standard"
  }
}
```

后端规则：

```text
client_flow = wizard_v1
且 preference 缺失或为 null
→ 返回 422 PREFERENCE_CONFIRMATION_REQUIRED
```

不得执行：

```text
preference 缺失
→ 自动使用 balanced
```

旧客户端兼容规则：

```text
未传 client_flow
→ 可以暂时使用历史 balanced 默认
```

但需要记录：

```json
{
  "preference_source": "legacy_default"
}
```

新向导保存时应记录：

```text
user_confirmed
user_modified
```

至少应区分：

```text
模型识别结果
用户最终确认结果
```

------

# 12. 测试用例

## Prompt 和模型抽取测试

| 输入                                 | 预期                                 |
| ------------------------------------ | ------------------------------------ |
| 两天深入掌握物理层，详细讲，多给例题 | `mastery + detailed + high examples` |
| 快速过一遍，但公式详细讲             | `fast_track + detailed`              |
| 考前冲刺，查漏补缺                   | `sprint`                             |
| 正常节奏学习                         | `balanced`                           |
| 未表达学习方式                       | `preference=null`                    |
| 快速学习深度学习基础                 | `fast_track`，不能判为 `mastery`     |
| 不需要详细讲                         | 不能输出 `detailed`                  |
| 不要多给例题                         | `example_intensity=low`              |
| 不是考前冲刺                         | 不能输出 `sprint`                    |
| 既要快速又要全面深入掌握             | `preference=null`，标记歧义          |

## 日期测试

```text
reference_date=2026-07-13
```

| 输入                                  | 预期                    |
| ------------------------------------- | ----------------------- |
| 明天开始学两天                        | 7 月 14 日至 7 月 15 日 |
| 今天开始学 2 天                       | 7 月 13 日至 7 月 14 日 |
| 7 月 30 日开始学 5 天                 | 正确跨月                |
| 12 月 31 日开始学 2 天                | 正确跨年                |
| 2028 年 2 月 28 日开始学 2 天         | 正确处理闰年            |
| 7 月 13 日开始学 2 天，7 月 16 日结束 | 返回日期冲突            |

## 每日时间测试

| 输入                | 预期                      |
| ------------------- | ------------------------- |
| 每天 60 分钟        | `60`                      |
| 每日 1.5 小时       | `90`                      |
| 两天总共学习 3 小时 | `null`                    |
| 总共安排 180 分钟   | `null`                    |
| 未说明每日时间      | `null`，不加入 unresolved |

## 新向导 API 测试

```text
client_flow=wizard_v1 + preference 缺失
→ PREFERENCE_CONFIRMATION_REQUIRED
client_flow=wizard_v1 + preference=mastery
→ 正常进入 preview
旧请求不带 client_flow 和 preference
→ 暂时兼容 balanced
→ preference_source=legacy_default
```

------

## 最终真实样本期望

输入：

```text
今天是2026年7月13日。我想用2天深度学习物理层，重点补Nyquist/Shannon、编码调制和传输介质。我希望讲义详细一点，多给公式适用条件和例题。最后请安排10道选择题和3道计算题检验Nyquist/Shannon公式、编码调制和传输介质。
```

期望配置解析结果：

```json
{
  "goal_text": "今天是2026年7月13日。我想用2天深度学习物理层，重点补Nyquist/Shannon、编码调制和传输介质。我希望讲义详细一点，多给公式适用条件和例题。最后请安排10道选择题和3道计算题检验Nyquist/Shannon公式、编码调制和传输介质。",
  "start_date": "2026-07-13",
  "end_date": "2026-07-14",
  "duration_days": 2,
  "daily_available_minutes": null,
  "recommended_daily_minutes": null,
  "daily_minutes_source": null,
  "preference": "mastery",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": "high",
    "assessment_intensity": "high",
    "review_intensity": null
  },
  "unresolved_fields": [],
  "needs_confirmation_fields": [
    "preference"
  ],
  "generation_metadata": {
    "config_parse": {
      "preference_resolution": "model"
    }
  }
}
```

这里的：

```text
10 道选择题 + 3 道计算题
```

虽然会使：

```text
assessment_intensity=high
```

但具体的题型和题量仍应保留在 `goal_text` 中，由后续 planner 或单独的 assessment 配置解析处理，不能只依靠 `assessment_intensity` 表达。
