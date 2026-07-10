# G05 复习提纲生成器

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：将全部选定资料归并为有序章节、重点说明、复习建议和章节级真实引用，保存为 `content_type=outline`。
- **前置依赖**：G01 公共 contracts、registry、coverage、引用和 fixtures。
- **范围外**：学习计划、每日任务、讲义、富文本编辑、PDF、独立 outline 表和其他 generator。
- **当前已实现 API**：通用 generation POST、历史、详情。
- **本任务新增 API**：无新路径；实现 `content_type=outline` 的真实生成。
- **后端未实现仅占位**：提纲编辑 / 导出 / 转学习计划，不得返回假入口或 plan ID。

## 2. 实现范围
### 2.1 文件边界
- 创建 / 修改 `backend/app/modules/generation/generators/outline/{__init__,schemas,prompts,generator}.py`。
- 创建 `backend/tests/modules/generation/generators/outline/test_{outline_schemas,outline_generator,outline_api}.py`。
- 只读 G01、material-context、ModelProvider、generated-content、table-schema。
- 禁止修改 registry、contracts、其他 generator、study_plans / handout / task_test、DB model、migration、前端。

### 2.2 参数与 schema
```python
class OutlineParameters(BaseModel):
    organization: Literal["source_order","topic","review_path"] = "review_path"
    section_count: int = Field(default=12, ge=1, le=30)
    review_goal: str | None = Field(default=None, min_length=1, max_length=300)
    detail_level: Literal["concise","standard","detailed"] = "standard"
```
- map schema：`OutlineCandidate(title, summary, review_suggestion, source_order_key, source_chunk_ids)` 和 `OutlineMapResult(candidates,citation_chunk_ids)`。
- title 1-160 字；summary 1-2000 字；review suggestion 1-800 字；每个候选至少一个真实 chunk。
- source order key 仅供排序，不写 `content_json`；同次 title trim + casefold 后唯一。

最终严格服从 table-schema：
```json
{"sections":[{"id":"sec_001","title":"1. 特征值与特征向量","summary":"重点说明","review_suggestion":"先复习定义，再完成例题。","source_citation_ids":["cit_1"],"sort_order":1}]}
```
- 不新增 parent / level 等未约定字段；层级用 title 中稳定的 `1.`、`1.1` 编号表达。
- ID `sec_001..sec_N`、sort order 连续；`content=null`；标题 `复习提纲（N 节）`。

### 2.3 Prompt / map / reduce / 持久化
- map prompt 按 chunk ID、资料名、定位、heading、正文提取章节候选、关键结论和可执行复习建议。
- 每个 batch 均调用 `ModelProvider.generate_structured(..., OutlineMapResult)`；不能在达到 section_count 时停止后续 batch。
- source_order 需保留 material / chunk 原顺序；topic 按主题聚合；review_path 按先修到综合的学习顺序组织。
- reduce 只使用 map 候选，去重并合并跨资料同主题 summary / 引用；不得读原文或引入计划任务。
- detail level 控制 summary 长度：concise <=300、standard <=800、detailed <=2000 字。
- 本地代码复核唯一性、长度、连续编号和 citation binding；1..section_count 节可成功，0 节 schema invalid。
- `run_material_coverage()` 在 reduce 前核对全部 batches；最终只保存保留 sections 引用。
- `build_generator(model_provider)` 返回 OutlineGenerator，由 G01 自动发现；不调用 Knowledge List 或 Study Plans。

## 3. 字段与接口
请求：
```json
{"content_type":"outline","material_scope":{"include_all_parsed_materials":false,"folder_ids":[],"material_ids":["mat_1","mat_2"]},"parameters":{"organization":"review_path","section_count":10,"review_goal":"两周内完成期末复习","detail_level":"standard"}}
```
- 成功 HTTP 200：sections 非空、结构固定，每节 citation 可在顶层 citations 解析，scope 原样持久化。
- 参数非法 422 且不落库；无资料 400；他人资源 404。
- 模型 / schema / coverage 失败保存对应 failed 记录，无部分 sections / citations。

## 4. 测试计划
- `test_outline_schemas.py`：organization / detail 枚举；section count 1/30、0/31；空 / 超长字段；空引用；未知 final 字段拒绝。
- `test_outline_generator.py`：两资料多 batch；三种组织策略；跨 batch 同主题合并引用；detail 长度；稳定 ID；最终引用；三类失败；import 独立。
- `test_outline_api.py`：401、404、400、422、成功 POST / 历史 / 详情、非法参数不落库、failed 可重读、重复请求不同 ID。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation/generators/outline -q
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context -q
```
- 预期全部 PASS；registry 创建 OutlineGenerator；无 live network。

## 5. 验收标准
### 自动化验收
- [ ] 所有资料 batches 均 map，未用 Top-K。
- [ ] sections 数量、字段、ID、sort order 和 detail 长度符合参数 / table-schema。
- [ ] 每节有真实范围内引用；未保留候选引用不落库。
- [ ] 权限、参数、空材料和三类生成失败全部覆盖。
### 人工验收
- [ ] 两份章节不同资料生成 review_path 提纲，章节能覆盖两份资料。
- [ ] 每节同时有重点说明、可执行复习建议和可追溯引用。
- [ ] source_order 重生成后顺序与资料 / chunk 原顺序一致。
- [ ] section_count=31 返回 422，历史不变；响应无 plan / task 字段。

## 6. 交付物
- Outline 参数、map / reduce / final schema、prompt、generator、factory。
- schema / generator / API 测试和中文验收记录。
- 建议提交：`feat(outline): 实现全材料复习提纲生成`、`test(outline): 覆盖章节引用和失败路径`。

## 7. 文档同步
- 更新 `docs/api-data/contracts.md` 的参数和 sections 示例。
- 核对 table-schema，严格使用既有字段；字段不变不修改。
- 更新 `runtime-flows.md`、`current-state.md`，只标 Outline 完成。
- 不修改 Study Plan 或 PRD 产品行为。

## 8. 冲突与注意事项
- **冲突点**：G01 文件只读；Outline 与 Study Plan / Handout 名称相近但数据和职责独立；table-schema 变更交唯一负责人。
- **严格遵循**：全材料 batch + coverage、ModelProvider、章节级真实引用、统一内容表。
- **一定不能做**：新增 outline 表 / migration；创建或修改计划任务；调用其他 generator；直接访问 chunk / Chroma / OpenAI；单段文本或空 sections 标 success。

## 9. 完成检查表
- [ ] 实现、测试、人工验收、docs 全部完成。
- [ ] G01、generated-content、material-context 回归通过。
- [ ] `git diff --check` 通过，测试无网络，修改未越权。
- [ ] 未新增表、migration、依赖；小功能已独立提交。
