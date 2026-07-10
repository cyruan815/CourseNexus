# G06 知识点清单生成器

## 1. 任务信息
- **负责人**：独立生成功能后端开发者。
- **目标**：从全部选定资料提取去重的知识点、定义、重要度、关联章节和逐项真实引用，保存为 `content_type=knowledge_list`。
- **前置依赖**：G01 公共 contracts、registry、coverage、引用和 fixtures。
- **范围外**：掌握度、知识图谱、自动考频、错题、计划任务、独立知识点表和其他 generator。
- **当前已实现 API**：通用 generation POST、历史、详情。
- **本任务新增 API**：无新路径；实现 `content_type=knowledge_list` 的真实生成。
- **后端未实现仅占位**：知识点编辑、掌握状态、筛选写回、转计划接口；不得返回假 ID 或状态。

## 2. 实现范围
### 2.1 文件边界
- 创建 / 修改 `backend/app/modules/generation/generators/knowledge_list/{__init__,schemas,prompts,generator}.py`。
- 创建 `backend/tests/modules/generation/generators/knowledge_list/test_{knowledge_list_schemas,knowledge_list_generator,knowledge_list_api}.py`。
- 只读 G01、material-context、ModelProvider、generated-content、table-schema。
- 禁止修改 registry、contracts、其他 generator、study_plans / checkins、DB model、migration、前端。

### 2.2 参数与 schema
```python
class KnowledgeListParameters(BaseModel):
    item_count: int = Field(default=50, ge=1, le=200)
    extraction_focus: Literal["balanced","definitions","formulas","pitfalls"] = "balanced"
    minimum_importance: Literal["low","medium","high"] = "low"
    focus: str | None = Field(default=None, min_length=1, max_length=200)
```
- map schema：`KnowledgeCandidate(name,definition,importance,related_section,source_chunk_ids)` 和 `KnowledgeMapResult(candidates,citation_chunk_ids)`。
- name 1-160 字；definition 1-1200 字；related section 1-200 字；importance 仅 high / medium / low。
- 每项至少一个真实 chunk；同次 name trim + casefold 唯一；同义候选 reduce 合并定义和引用。
- importance 依据资料中的定义地位、重复出现、章节核心性和明确强调；模型不得虚构考试频率。

最终严格服从 table-schema：
```json
{"items":[{"id":"kp_001","name":"特征值","definition":"定义说明","importance":"high","related_section":"第三章 矩阵","source_citation_ids":["cit_1"],"sort_order":1}]}
```
- 不新增 exam_hint / mastery 等未约定字段；ID `kp_001..kp_N`，sort order 连续。
- 排序先 importance high/medium/low，再首次资料顺序；`content=null`；标题 `知识点清单（N 项）`。

### 2.3 Prompt / map / reduce / 持久化
- map prompt 标注 chunk ID、资料名、定位、heading、正文，按 focus 提取概念、定义、公式含义或易错点。
- 每个 batch 均调用一次 `ModelProvider.generate_structured(..., KnowledgeMapResult)`；item_count / importance 过滤不得跳过 batch。
- map 的 source chunk 必须来自当前 batch；related section 优先使用 heading，缺失时用资料名 + chunk 序号生成可读位置。
- reduce 只使用 map 候选，做同义归并、定义压缩、importance 统一、minimum importance 过滤和数量裁剪。
- 同义项重要度取最高；引用取并集；definition 保留互补信息但不超过 1200 字。
- 本地代码复核枚举、唯一性、排序、稳定 ID 和 citation binding；1..item_count 项可成功，0 项 schema invalid。
- `run_material_coverage()` 在 reduce 前核对全部 batches；最终只保存保留 items 引用。
- `build_generator(model_provider)` 返回 KnowledgeListGenerator，由 G01 自动发现；不调用 Outline / Plan / Checkins。

## 3. 字段与接口
请求：
```json
{"content_type":"knowledge_list","material_scope":{"include_all_parsed_materials":false,"folder_ids":["folder_1"],"material_ids":[]},"parameters":{"item_count":80,"extraction_focus":"pitfalls","minimum_importance":"medium","focus":"期末范围"}}
```
- 成功 HTTP 200：items 非空、字段固定、importance 合法、逐项 citation 可在顶层 citations 解析。
- 参数非法 422 且不落库；无资料 400；他人资源 404。
- 模型 / schema / coverage 失败保存对应 failed 记录，无部分 items / citations。
- minimum importance 过滤后为空必须 schema invalid，不能返回 success 空列表。

## 4. 测试计划
- `test_knowledge_list_schemas.py`：item count 1/200、0/201；四 focus；importance 枚举；空 / 超长字段；空引用；未知 final 字段拒绝。
- `test_knowledge_list_generator.py`：两资料多 batch；同义合并 / 引用并集；importance 取最高和过滤；稳定排序 / ID；数量裁剪；伪造引用过滤；三类失败；import 独立。
- `test_knowledge_list_api.py`：401、404、400、422、成功 POST / 历史 / 详情、非法参数不落库、failed 可重读、重复请求不同 ID。
```powershell
cd backend
conda run -n course-nexus pytest tests/modules/generation/generators/knowledge_list -q
conda run -n course-nexus pytest tests/modules/generation tests/modules/generated_content tests/modules/material_context -q
```
- 预期全部 PASS；registry 创建 KnowledgeListGenerator；无 live network。

## 5. 验收标准
### 自动化验收
- [ ] 所有资料 batches 均 map，未用 Top-K。
- [ ] items 数量、字段、importance、排序、ID 符合参数和 table-schema。
- [ ] 同义项去重并合并真实引用；范围外 / 未保留引用不落库。
- [ ] 权限、参数、空材料和三类生成失败全部覆盖。
### 人工验收
- [ ] 两份不同章节资料生成 balanced 清单，结果覆盖两份资料。
- [ ] 每项有定义、重要度、关联章节和可追溯引用。
- [ ] pitfalls + minimum_importance=medium 重生成，结果只含 high / medium。
- [ ] item_count=201 返回 422，历史不变；响应无 mastery / exam_hint。

## 6. 交付物
- Knowledge List 参数、map / reduce / final schema、prompt、generator、factory。
- schema / generator / API 测试和中文验收记录。
- 建议提交：`feat(knowledge-list): 实现全材料知识点清单生成`、`test(knowledge-list): 覆盖去重引用和失败路径`。

## 7. 文档同步
- 更新 `docs/api-data/contracts.md` 的参数和 items 示例。
- 核对 table-schema，严格使用既有字段；字段不变不修改。
- 更新 `runtime-flows.md`、`current-state.md`，只标 Knowledge List 完成。
- 掌握度 / exam hint 若进入产品，另行更新 PRD、数据和 API 契约。

## 8. 冲突与注意事项
- **冲突点**：G01 文件只读；Knowledge List 不等于 Outline 或计划知识点；table-schema 变更交唯一负责人。
- **严格遵循**：全材料 batch + coverage、ModelProvider、逐项真实引用、统一内容表。
- **一定不能做**：新增 knowledge 表 / migration；写掌握度 / checkin / 计划；调用其他 generator；直接访问 chunk / Chroma / OpenAI；空 items、伪考试频率或无引用标 success。

## 9. 完成检查表
- [ ] 实现、测试、人工验收、docs 全部完成。
- [ ] G01、generated-content、material-context 回归通过。
- [ ] `git diff --check` 通过，测试无网络，修改未越权。
- [ ] 未新增表、migration、依赖；小功能已独立提交。
